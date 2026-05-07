"""Ingestion script for processing and embedding corpus entries into the database."""

import logging
from pathlib import Path

import hydra
from dotenv import load_dotenv
from omegaconf import DictConfig
from sqlalchemy.orm import sessionmaker
from tqdm import tqdm

from linguaalayam.corpus import datuk, dravidian, enml
from linguaalayam.database import (
    batch_insert,
    build_engine,
    build_session_factory,
    get_ingested_headwords,
    get_session,
)
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.models import Embeddable
from linguaalayam.scripts import VectorCheckpoint

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

log = logging.getLogger(__name__)

_PARSERS = {
    "enml": enml.parse,
    "datuk": datuk.parse,
    "dravidian": dravidian.parse,
}


def _batched(items: list, size: int):
    """Yield successive batches of a specified size from a list of items."""
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _embed_with_checkpoint(
    source: str,
    entries: list[Embeddable],
    service: EmbeddingService,
    checkpoint: VectorCheckpoint,
) -> dict[str, list[float]]:
    """Embed entries, skipping those already in the checkpoint.

    Appends each batch to the checkpoint file immediately after embedding
    so progress is never lost on failure.

    Returns a dict of {headword: vector} covering both newly embedded
    and previously checkpointed entries.
    """
    cached = checkpoint.load()
    to_embed = [e for e in entries if e.headword not in cached]

    if cached:
        log.info(
            "%s: %d vectors restored from checkpoint, %d remaining to embed",
            source,
            len(cached),
            len(to_embed),
        )

    with tqdm(total=len(to_embed), desc=f"Embedding {source}", unit="entry") as pbar:
        for batch in _batched(to_embed, service._cfg.batch_size):
            vectors = service.encode(batch)
            checkpoint.append_batch([e.headword for e in batch], vectors)
            pbar.update(len(batch))

    return checkpoint.load()


def _insert_with_checkpoint(
    source: str,
    entries: list[Embeddable],
    vectors_by_headword: dict[str, list[float]],
    session_factory: sessionmaker,
    checkpoint: VectorCheckpoint,
    db_batch_size: int,
) -> None:
    """Insert entries into the DB in batches.

    After each successful batch insert, removes those headwords from the
    checkpoint so disk space is reclaimed progressively. Deletes the
    checkpoint file entirely when all entries are inserted.
    """
    with tqdm(total=len(entries), desc=f"Inserting {source}", unit="entry") as pbar:
        for i in range(0, len(entries), db_batch_size):
            batch_entries = entries[i : i + db_batch_size]
            batch_vectors = [vectors_by_headword[e.headword] for e in batch_entries]

            with get_session(session_factory) as session:
                batch_insert(session, batch_entries, batch_vectors)

            checkpoint.remove_inserted({e.headword for e in batch_entries})
            pbar.update(len(batch_entries))

    log.info("%s: done", source)


def _ingest_corpus(
    source: str,
    entries: list[Embeddable],
    service: EmbeddingService,
    session_factory: sessionmaker,
    checkpoint: VectorCheckpoint,
    db_batch_size: int,
) -> None:
    """Embed and insert a list of entries with checkpoint-based fault tolerance."""
    log.info("%s: %d entries to process", source, len(entries))
    vectors_by_headword = _embed_with_checkpoint(source, entries, service, checkpoint)
    _insert_with_checkpoint(
        source, entries, vectors_by_headword, session_factory, checkpoint, db_batch_size
    )


def _get_pending(
    source: str,
    all_entries: list[Embeddable],
    ingested_headwords: set[str],
    limit: int | None,
) -> list[Embeddable]:
    """Filter out already-ingested entries and apply optional debug limit."""
    pending = [
        e
        for e in tqdm(all_entries, desc=f"Filtering {source}", unit="entry")
        if e.headword not in ingested_headwords
    ]
    skipped = len(all_entries) - len(pending)
    if skipped:
        log.info("%s: skipping %d already-ingested entries", source, skipped)

    if limit is not None:
        pending = pending[:limit]
        log.info("%s: debug limit applied, processing %d entries", source, len(pending))

    return pending


def _process_source(
    source: str,
    source_cfg: DictConfig,
    service: EmbeddingService,
    session_factory: sessionmaker,
    data_dir: Path,
    checkpoint_dir: Path,
    db_batch_size: int,
    limit: int | None,
) -> None:
    """Handle the full pipeline for a single corpus source.

    Parameters
    ----------
    source : str
        The name of the corpus source (e.g. "enml").
    source_cfg : DictConfig
        Configuration for the corpus source, including file path and DB source name.
    service : EmbeddingService
        The embedding service instance to use for generating vectors.
    session_factory : sessionmaker
        Factory function for creating new database sessions.
    data_dir : Path
        Directory containing the source data files.
    checkpoint_dir : Path
        Directory to store checkpoint files for fault tolerance.
    db_batch_size : int
        The number of entries to insert into the database in each batch.
    limit : int | None
        Optional limit on the number of entries to process (for debugging).
    """
    filepath = data_dir / source_cfg.path
    if not filepath.exists():
        log.error(
            "%s: file not found at %s — skipping. "
            "Download from https://olam.in/p/open and place at the expected path.",
            source,
            filepath,
        )
        return

    log.info("%s: parsing %s", source, filepath)
    all_entries: list[Embeddable] = _PARSERS[source](filepath)

    if not all_entries:
        log.warning("%s: no entries parsed, skipping", source)
        return

    with get_session(session_factory) as session:
        ingested_headwords = get_ingested_headwords(session, source_cfg.source_name)

    checkpoint = VectorCheckpoint(checkpoint_dir / f"{source}.jsonl")
    checkpointed_headwords = set(checkpoint.load().keys())

    pending = _get_pending(source, all_entries, ingested_headwords, limit)

    if not pending and not checkpointed_headwords:
        log.info("%s: all entries already ingested", source)
        return

    if checkpointed_headwords:
        log.info(
            "%s: %d entries already vectorized in checkpoint, will insert those first",
            source,
            len(checkpointed_headwords),
        )

    _ingest_corpus(source, pending, service, session_factory, checkpoint, db_batch_size)


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:  # pragma: no cover
    """Main entrypoint for the ingestion script.

    Parameters
    ----------
    cfg : DictConfig
        Configuration object containing all settings.
    """
    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)

    log.info("Loading embedding model: %s", cfg.embedding.model)
    service = EmbeddingService(cfg.embedding)
    log.info("Vector size: %d", service.vector_size)

    data_dir = Path(cfg.data_dir)
    db_batch_size: int = cfg.corpus.db_batch_size
    checkpoint_dir = Path(cfg.get("checkpoint_dir", ".checkpoints"))
    checkpoint_dir.mkdir(exist_ok=True)

    # Limit filter for debugging
    limit: int | None = cfg.corpus.get("limit")

    for source, source_cfg in cfg.corpus.sources.items():
        if not source_cfg.enabled:
            log.info("%s: disabled in config, skipping", source)
            continue

        _process_source(
            source,
            source_cfg,
            service,
            session_factory,
            data_dir,
            checkpoint_dir,
            db_batch_size,
            limit,
        )

    log.info("Ingest complete")


if __name__ == "__main__":  # pragma: no cover
    main()

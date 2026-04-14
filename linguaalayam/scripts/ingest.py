"""
Ingest pipeline: parse corpora -> embed -> batch insert to Supabase.

Schema is managed by Alembic — run migrations before ingesting:
    alembic upgrade head

Hydra manages all configuration. Override anything from the CLI:

    # Use defaults (conf/config.yaml)
    poetry run ingest

    # Quick debug run — 50 entries, one corpus, small batches
    poetry run ingest corpus=debug

    # Switch embedding model
    poetry run ingest embedding=multilingual_e5_large

    # Ingest only enml corpus
    poetry run ingest corpus=enml_only
"""

import logging
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import hydra
from omegaconf import DictConfig
from tqdm import tqdm

from linguaalayam.corpus import datuk, dravidian, enml
from linguaalayam.database import (
    batch_insert,
    build_engine,
    build_session_factory,
    get_ingested_headwords,
    get_session,
)
from linguaalayam.embeddings import EmbeddingService, embed_in_batches
from linguaalayam.models.entries import Embeddable

log = logging.getLogger(__name__)

_PARSERS = {
    "enml": enml.parse,
    "datuk": datuk.parse,
    "dravidian": dravidian.parse,
}


def _ingest_corpus(
    source: str,
    entries: list[Embeddable],
    service: EmbeddingService,
    session_factory,
    db_batch_size: int,
) -> None:
    log.info("%s: %d new entries to embed and insert", source, len(entries))

    vectors = embed_in_batches(service, entries)

    with tqdm(total=len(entries), desc=f"Inserting {source}", unit="entry") as pbar:
        with get_session(session_factory) as session:
            for i in range(0, len(entries), db_batch_size):
                batch_entries = entries[i : i + db_batch_size]
                batch_vectors = vectors[i : i + db_batch_size]
                batch_insert(session, batch_entries, batch_vectors)
                pbar.update(len(batch_entries))

    log.info("%s: done", source)


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)

    log.info("Loading embedding model: %s", cfg.embedding.model)
    service = EmbeddingService(cfg.embedding)
    log.info("Vector size: %d", service.vector_size)

    data_dir = Path(cfg.data_dir)
    db_batch_size: int = cfg.corpus.db_batch_size
    limit: int | None = cfg.corpus.get("limit")

    for source, source_cfg in cfg.corpus.sources.items():
        if not source_cfg.enabled:
            log.info("%s: disabled in config, skipping", source)
            continue

        filepath = data_dir / source_cfg.path
        if not filepath.exists():
            log.error(
                "%s: file not found at %s — skipping. "
                "Download from https://olam.in/p/open and place at the expected path.",
                source,
                filepath,
            )
            continue

        log.info("%s: parsing %s", source, filepath)
        all_entries: list[Embeddable] = _PARSERS[source](filepath)

        if not all_entries:
            log.warning("%s: no entries parsed, skipping", source)
            continue

        # Resume: filter out already-ingested headwords
        with get_session(session_factory) as session:
            done = get_ingested_headwords(session, source_cfg.source_name)

        pending = [
            e for e in tqdm(all_entries, desc=f"Filtering {source}", unit="entry")
            if e.headword not in done
        ]
        skipped = len(all_entries) - len(pending)
        if skipped:
            log.info("%s: skipping %d already-ingested entries", source, skipped)

        if not pending:
            log.info("%s: all entries already ingested", source)
            continue

        if limit is not None:
            pending = pending[:limit]
            log.info("%s: debug limit applied, processing %d entries", source, len(pending))

        _ingest_corpus(source, pending, service, session_factory, db_batch_size)

    log.info("Ingest complete")


if __name__ == "__main__":
    main()
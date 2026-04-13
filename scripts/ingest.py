"""
Ingest pipeline: parse corpora -> embed -> batch insert to Supabase.

Hydra manages all configuration. Override anything from the CLI:

    # Use defaults (conf/config.yaml)
    poetry run ingest

    # Switch embedding model
    poetry run ingest embedding=multilingual_e5_large

    # Ingest only enml corpus
    poetry run ingest corpus=enml_only

    # Recreate tables on a fresh run
    poetry run ingest +recreate=true

    # Mix overrides freely
    poetry run ingest corpus=enml_only embedding=multilingual_e5_large data_dir=data/custom
"""

import logging

import hydra
from omegaconf import DictConfig
from tqdm import tqdm

from linguaalayam.corpus import datuk, dravidian, enml
from linguaalayam.database import (
    batch_insert,
    build_engine,
    build_session_factory,
    create_tables,
    drop_tables,
    get_session,
)
from linguaalayam.embeddings import EmbeddingService, embed_in_batches
from linguaalayam.models.entries import Embeddable

log = logging.getLogger(__name__)

# Maps source name to its parser function
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
    log.info("%s: %d entries to embed and insert", source, len(entries))

    vectors = embed_in_batches(service, entries)

    log.info("%s: inserting in batches of %d", source, db_batch_size)
    with get_session(session_factory) as session:
        for i in tqdm(
            range(0, len(entries), db_batch_size),
            desc=f"Inserting {source}",
        ):
            batch_insert(
                session,
                entries[i : i + db_batch_size],
                vectors[i : i + db_batch_size],
            )

    log.info("%s: done", source)


@hydra.main(config_path="../conf", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    from pathlib import Path

    # -- Database setup ------------------------------------------------------
    engine = build_engine(cfg.db)
    session_factory = build_session_factory(engine)

    if cfg.get("recreate", False):
        log.warning("Dropping all tables and recreating schema")
        drop_tables(engine)
    create_tables(engine)

    # -- Embedding model -----------------------------------------------------
    log.info("Loading embedding model: %s", cfg.embedding.model)
    service = EmbeddingService(cfg.embedding)
    log.info("Vector size: %d", service.vector_size)

    # -- Corpus ingestion ----------------------------------------------------
    data_dir = Path(cfg.data_dir)
    db_batch_size: int = cfg.corpus.db_batch_size

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

        parse_fn = _PARSERS[source]
        log.info("%s: parsing %s", source, filepath)
        entries: list[Embeddable] = parse_fn(filepath)

        if not entries:
            log.warning("%s: no entries parsed, skipping", source)
            continue

        _ingest_corpus(source, entries, service, session_factory, db_batch_size)

    log.info("Ingest complete")


if __name__ == "__main__":
    main()
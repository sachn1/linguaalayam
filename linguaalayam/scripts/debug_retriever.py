"""Debugging script for the retriever component of LinguAalayam."""

import argparse
from pathlib import Path

from dotenv import load_dotenv
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra
from omegaconf import DictConfig

from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.rag import Retriever

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

def _load_config(overrides: list[str]) -> DictConfig:
    """Load Configuration with Hydra.

    Parameters
    ----------
    overrides : list[str]
        List of configuration overrides to apply.

    Returns
    -------
    DictConfig
        Composed Hydra configuration object.
    """
    GlobalHydra.instance().clear()
    config_dir = str(Path(__file__).resolve().parent.parent.parent / "config")
    with initialize_config_dir(config_dir=config_dir, version_base=None):
        return compose(config_name="config", overrides=overrides)


def main() -> None:
    """
    Debug script for testing the retriever interactively.

    Usage:
        poetry run debug-retriever
        poetry run debug-retriever --query "ഓടുക" --top-k 3
        poetry run debug-retriever --source datuk
    """
    parser = argparse.ArgumentParser(description="Debug the LinguAalayam retriever")
    parser.add_argument("--query", default="run", help="Query string (default: 'run')")
    parser.add_argument("--top-k", type=int, default=1, help="Number of results (default: 5)")
    parser.add_argument("--source", default=None, help="Filter by source (e.g. olam_enml, datuk)")
    parser.add_argument("--entry-type", default=None, help="Filter by entry type (e.g. EnMlEntry)")
    parser.add_argument("--corpus", default="all", help="Corpus config to use (default: all)")
    parser.add_argument("--embedding", default="model", help="Embedding config to use")
    args = parser.parse_args()

    overrides = [
        f"corpus={args.corpus}",
        f"embedding={args.embedding}",
    ]
    cfg = _load_config(overrides)

    print(f"Loading embedding model: {cfg.embedding.model}")
    service = EmbeddingService(cfg.embedding)
    print(f"Vector size: {service.vector_size}")

    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)
    retriever = Retriever(service, session_factory)

    print(f"\nQuery : {args.query!r}")
    print(f"Top-k : {args.top_k}")
    print(f"Source: {args.source or 'all'}")
    print("-" * 60)

    results = retriever.retrieve(
        args.query,
        top_k=args.top_k,
        source=args.source,
        entry_type=args.entry_type,
    )

    if not results:
        print("No results found.")
        return

    for i, result in enumerate(results, 1):
        print(f"\n[{i}] {result['headword']}  ({result['source']} / {result['entry_type']})")
        print(result["embed_text"])


if __name__ == "__main__":
    main()

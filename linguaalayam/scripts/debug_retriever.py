"""Interactive debug script for testing all three dictionary retrieval tools."""

from pathlib import Path

import hydra
from dotenv import load_dotenv
from omegaconf import DictConfig

from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.rag.tools import DictionaryTools

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    """Debug all three retrieval tools against the live database.

    Usage:
        poetry run debug-retriever
        poetry run debug-retriever 'debug.query=ephemeral'
        DEBUG_QUERY='what does run mean' poetry run debug-retriever
        poetry run debug-retriever 'debug.query=run' debug.top_k=10 debug.fuzzy_threshold=0.2
        poetry run debug-retriever 'debug.query=run' debug.source=olam_enml
    """
    query: str = cfg.debug.query
    if not query:
        raise RuntimeError(
            "No query provided. Use the env var for complex text, or a Hydra override:\n"
            "  DEBUG_QUERY='your query' poetry run debug-retriever\n"
            "  poetry run debug-retriever 'debug.query=run'"
        )

    top_k: int = cfg.debug.top_k
    source: str | None = cfg.debug.source
    threshold: float = cfg.debug.fuzzy_threshold

    print(f"Loading embedding model: {cfg.embedding.model}")
    service = EmbeddingService(cfg.embedding)

    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)
    tools = DictionaryTools(session_factory, service)

    print(f"\nQuery : {query!r}")
    print(f"Source: {source or 'all'}")
    print("=" * 60)

    sections = [
        ("exact", tools.exact_lookup(query, source=source)),
        ("fuzzy", tools.fuzzy_lookup(query, source=source, threshold=threshold, top_k=top_k)),
        ("semantic", tools.semantic_lookup(query, top_k=top_k, source=source)),
    ]

    for label, results in sections:
        print(f"\n── {label} ──")
        if not results:
            print("  (no results)")
            continue
        for i, r in enumerate(results[:top_k], 1):
            print(f"  [{i}] {r['headword']}  [{r['match_type']} {r['score']:.3f}]")
            print(f"       {r['embed_text'][:120].replace(chr(10), ' ')}")


if __name__ == "__main__":
    main()

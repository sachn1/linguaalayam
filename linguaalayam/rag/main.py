"""RAG query entrypoint for the LinguAalayam dictionary assistant."""

import logging
from pathlib import Path

import hydra
from dotenv import load_dotenv
from hydra.utils import instantiate
from omegaconf import DictConfig

from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.llm import LLMAdapter
from linguaalayam.rag.pipeline import build_pipeline
from linguaalayam.rag.reranker import CrossEncoderReranker
from linguaalayam.rag.tools import DictionaryTools

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

log = logging.getLogger(__name__)


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:  # pragma: no cover
    """Query the LinguAalayam RAG pipeline.

    Usage:
        # Simple terms — Hydra override (avoid special chars: commas, quotes, dashes)
        poetry run rag 'rag.query=run'
        poetry run rag 'rag.query=ഓടുക' rag.source=olam_enml

        # Complex / prose queries — env var sidesteps Hydra's lexer entirely
        RAG_QUERY='what does the word "pastoral" mean?' poetry run rag
        RAG_QUERY='In Keats ode, what is the Malayalam meaning of...' poetry run rag rag.rerank=true

        # Switch LLM provider or embedding model
        RAG_QUERY='define ephemeral' poetry run rag llm=openai
        RAG_QUERY='define ephemeral' poetry run rag llm=nollm
        poetry run rag 'rag.query=run' rag.top_k=10 embedding=multilingual_e5_large
    """
    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)

    log.info("Loading embedding model: %s", cfg.embedding.model)
    service = EmbeddingService(cfg.embedding)

    tools = DictionaryTools(session_factory, service)
    llm: LLMAdapter = instantiate(cfg.llm)
    reranker = CrossEncoderReranker() if cfg.rag.rerank else None

    query: str = cfg.rag.query
    if not query:
        raise RuntimeError(
            "No query provided. Use the env var for complex text, or a Hydra override for simple terms:\n"
            "  RAG_QUERY='your query' poetry run rag\n"
            "  poetry run rag 'rag.query=run'"
        )

    pipeline = build_pipeline(tools, llm, cfg.rag, reranker=reranker)

    log.info("Query : %s", query)
    log.info("LLM   : %s", type(llm).__name__)
    log.info("Rerank: %s", cfg.rag.rerank)

    result = pipeline.invoke(
        {
            "query": query,
            "headword": None,
            "intent": None,
            "candidates": [],
            "answer": "",
        }
    )

    print(f"\nHeadword : {result['headword']!r}  (intent: {result['intent']})")
    print(f"Candidates: {len(result['candidates'])} found")
    for i, c in enumerate(result["candidates"], 1):
        preview = c["embed_text"][:80].replace("\n", " ")
        score_str = f"{c['score']:.3f}" if c.get("score") is not None else "n/a"
        print(f"  [{i}] {c['headword']}  [{c['match_type']}  {score_str}]  {preview}...")
    print(f"\nAnswer:\n{result['answer']}")


if __name__ == "__main__":  # pragma: no cover
    main()

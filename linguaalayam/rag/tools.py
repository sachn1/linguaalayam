"""Standalone dictionary retrieval tools — exact, fuzzy, and semantic lookup.

Each method is self-contained with no LangGraph imports so it can be
used directly from LangGraph nodes today and exposed as MCP tools in v0.3.
"""

from sqlalchemy.orm import sessionmaker

from linguaalayam.database.queries import exact_search, fuzzy_search, similarity_search
from linguaalayam.database.session import get_session
from linguaalayam.embeddings.service import EmbeddingService
from linguaalayam.models.orm import DictionaryEntry


def merge_candidates(lists: list[list[dict]]) -> list[dict]:
    """Merge results from multiple tools, deduplicating on (source, headword).

    Priority: exact > fuzzy > semantic — the first tool to surface an entry wins.
    Used by both the RAG pipeline and the eval runner.
    """
    seen: set[tuple[str, str]] = set()
    merged = []
    for results in lists:
        for item in results:
            key = (item["source"], item["headword"])
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return merged


def _to_result(entry: DictionaryEntry, match_type: str, score: float) -> dict:
    return {
        "headword": entry.headword,
        "source": entry.source,
        "entry_type": entry.entry_type,
        "embed_text": entry.embed_text,
        "data": entry.data,
        "match_type": match_type,
        "score": score,
    }


class DictionaryTools:
    """Retrieval tools over the dictionary database.

    Holds references to the session factory and embedding service so
    each tool method takes only domain-level arguments — the shape
    MCP tool handlers expect.
    """

    def __init__(
        self,
        session_factory: sessionmaker,
        embedding_service: EmbeddingService,
    ) -> None:
        self._session_factory = session_factory
        self._embedder = embedding_service

    def exact_lookup(
        self,
        query: str,
        source: str | None = None,
    ) -> list[dict]:
        """Return entries whose headword is a case-insensitive exact match for query."""
        with get_session(self._session_factory) as session:
            results = exact_search(session, query, source=source)
        return [_to_result(r, "exact", 1.0) for r in results]

    def fuzzy_lookup(
        self,
        query: str,
        source: str | None = None,
        threshold: float = 0.3,
        top_k: int = 10,
    ) -> list[dict]:
        """Return entries whose headword is trigram-similar to query (pg_trgm).

        Falls back to an ILIKE-based search when running against SQLite (tests).
        """
        with get_session(self._session_factory) as session:
            results = fuzzy_search(
                session, query, source=source, threshold=threshold, limit=top_k
            )
        return [_to_result(r, "fuzzy", score) for r, score in results]

    def semantic_lookup(
        self,
        query: str,
        top_k: int = 5,
        source: str | None = None,
    ) -> list[dict]:
        """Return entries ranked by cosine similarity of their embed_text to query."""
        query_vector = self._embedder.encode_query(query)
        with get_session(self._session_factory) as session:
            results = similarity_search(
                session, query_vector, top_k=top_k, source=source
            )
        return [_to_result(r, "semantic", score) for r, score in results]

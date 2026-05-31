"""MCP server exposing LinguAalayam's three dictionary retrieval tools."""

import os
import subprocess
import time
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from omegaconf import OmegaConf


from linguaalayam.mcp.shared import format_results as _format
from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.rag.tools import DictionaryTools

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

_tools: DictionaryTools | None = None


def _ensure_docker_db() -> None:
    """Start the Postgres container if it exists but is not running."""
    container = os.getenv("DB_CONTAINER", "linguaalayam-pg")
    try:
        result = subprocess.run(
            ["docker", "start", container],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            time.sleep(2)  # give Postgres a moment to accept connections
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass  # Docker not available — let the DB connection surface the error


def _init_tools() -> DictionaryTools:
    """Build DictionaryTools from environment variables."""
    db_cfg = OmegaConf.create(
        {
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "name": os.getenv("DB_NAME", "linguaalayam"),
            "pool_size": 5,
            "max_overflow": 10,
        }
    )
    embed_cfg = OmegaConf.create(
        {
            "model": os.getenv("EMBED_MODEL", _EMBED_MODEL),
            "batch_size": 256,
            "normalize": True,
            "quantise": False,
        }
    )
    engine = build_engine(db_cfg)
    session_factory = build_session_factory(engine)
    service = EmbeddingService(embed_cfg)
    return DictionaryTools(session_factory, service)


@asynccontextmanager
async def _lifespan(_: FastMCP):
    """Start Docker DB and initialise DictionaryTools before serving."""
    global _tools
    _ensure_docker_db()
    _tools = _init_tools()
    yield


mcp = FastMCP(
    "linguaalayam",
    instructions=(
        "Malayalam lexical knowledge base built on the Olam English–Malayalam corpus. "
        "Use exact_lookup first for a known word spelling. "
        "Use fuzzy_lookup for approximate matches, typos, or near-spellings. "
        "Use semantic_lookup for meaning-based queries, paraphrases, or when the exact word is unknown."
    ),
    lifespan=_lifespan,
)


def _require_tools() -> "DictionaryTools":
    """Return the initialised DictionaryTools or raise if lifespan has not run."""
    if _tools is None:
        raise RuntimeError("DictionaryTools not initialised — server lifespan may not have run")
    return _tools


@mcp.resource("dictionary://{headword}")
def get_entry(headword: str) -> str:
    """Browse a dictionary entry by URI.

    Returns all exact-match entries for the headword as plain text.
    URI format: dictionary://{headword}  e.g. dictionary://run
    """
    results = _require_tools().exact_lookup(headword)
    return _format(results, headword, "exact")


@mcp.tool()
def exact_lookup(word: str, source: str | None = None) -> str:
    """Look up a word by exact headword match (case-insensitive).

    Use this when you know the precise spelling of the English word.
    Returns all dictionary entries whose headword exactly matches the query.

    Args:
        word: The English word to look up.
        source: Optional corpus filter (e.g. "olam_enml"). Searches all corpora if omitted.
    """
    results = _require_tools().exact_lookup(word, source=source)
    return _format(results, word, "exact")


@mcp.tool()
def fuzzy_lookup(
    query: str,
    threshold: float = 0.3,
    top_k: int = 10,
    source: str | None = None,
) -> str:
    """Search for words by approximate headword similarity (trigram / pg_trgm).

    Use this for misspellings, typos, or near-matches where the exact spelling is uncertain.
    Returns headwords whose trigram similarity to the query exceeds the threshold.

    Args:
        query: The word or partial word to search for.
        threshold: Minimum trigram similarity score (0–1). Default 0.3.
        top_k: Maximum number of results to return. Default 10.
        source: Optional corpus filter (e.g. "olam_enml"). Searches all corpora if omitted.
    """
    results = _require_tools().fuzzy_lookup(query, source=source, threshold=threshold, top_k=top_k)
    return _format(results, query, "fuzzy")


@mcp.tool()
def semantic_lookup(
    query: str,
    top_k: int = 5,
    source: str | None = None,
) -> str:
    """Search for words by meaning similarity using sentence embeddings (HNSW cosine search).

    Use this for conceptual queries, paraphrases, or when you do not know the exact headword.
    Encodes the query with a multilingual sentence-transformer and retrieves the nearest entries.

    Args:
        query: A word, phrase, or description of the meaning to search for.
        top_k: Number of top results to return. Default 5.
        source: Optional corpus filter (e.g. "olam_enml"). Searches all corpora if omitted.
    """
    results = _require_tools().semantic_lookup(query, top_k=top_k, source=source)
    return _format(results, query, "semantic")


def main() -> None:  # pragma: no cover
    mcp.run()


if __name__ == "__main__":  # pragma: no cover
    main()

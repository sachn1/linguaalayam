"""FastAPI REST layer over LinguAalayam's DictionaryTools."""

import os
import subprocess
import time
from contextlib import asynccontextmanager
from importlib.metadata import version as _pkg_version
from pathlib import Path
from typing import Any, Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Query, Response
from fastapi.staticfiles import StaticFiles
from omegaconf import OmegaConf
from pydantic import BaseModel
from starlette.middleware.gzip import GZipMiddleware

from linguaalayam.api.dependencies import get_tools, set_tools
from linguaalayam.api.web import router as _web_router
from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.mcp.remote import get_mcp_app
from linguaalayam.rag.tools import DictionaryTools

load_dotenv(Path(__file__).resolve().parents[2] / ".env")

_EMBED_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
_CACHE_1D = "public, max-age=86400"

try:
    _VERSION = _pkg_version("linguaalayam")
except Exception:
    _VERSION = "dev"

CorpusSource = Literal["olam_enml", "datuk", "ekkurup"]


def _ensure_docker_db() -> None:
    container = os.getenv("DB_CONTAINER", "linguaalayam-pg")
    try:
        result = subprocess.run(
            ["docker", "start", container],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            time.sleep(2)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass


def _init_tools() -> DictionaryTools:
    db_cfg = OmegaConf.create(
        {
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", ""),
            "host": os.getenv("DB_HOST", "localhost"),
            "port": int(os.getenv("DB_PORT", "5432")),
            "name": os.getenv("DB_NAME", "linguaalayam"),
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "max_overflow": int(os.getenv("DB_MAX_OVERFLOW", "10")),
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
async def _lifespan(_: FastAPI):
    _ensure_docker_db()
    set_tools(_init_tools())
    yield


class LookupResult(BaseModel):
    headword: str
    source: str
    entry_type: str
    embed_text: str
    data: dict[str, Any]
    match_type: str
    score: float


app = FastAPI(
    title="LinguAalayam",
    description="Your companion for Malayalam and English words — ask a question, get an answer.",
    version=_VERSION,
    lifespan=_lifespan,
)

app.add_middleware(GZipMiddleware, minimum_size=500)

_STATIC = Path(__file__).resolve().parents[1] / "static"
app.mount("/static", StaticFiles(directory=str(_STATIC)), name="static")
app.mount("/mcp", get_mcp_app())
app.include_router(_web_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/lookup/exact", response_model=list[LookupResult])
def exact_lookup(
    query: str = Query(..., max_length=500),
    source: CorpusSource | None = Query(default=None, description="Corpus to search"),
    response: Response = None,
) -> list[dict]:
    """Exact headword match (case-insensitive)."""
    response.headers["Cache-Control"] = _CACHE_1D
    return get_tools().exact_lookup(query, source=source)


@app.get("/lookup/fuzzy", response_model=list[LookupResult])
def fuzzy_lookup(
    query: str = Query(..., max_length=500),
    source: CorpusSource | None = Query(default=None, description="Corpus to search"),
    threshold: float = Query(default=0.3, ge=0.0, le=1.0, description="Minimum trigram similarity"),
    top_k: int = Query(default=10, ge=1, le=100),
    response: Response = None,
) -> list[dict]:
    """Trigram fuzzy headword search (pg_trgm)."""
    response.headers["Cache-Control"] = _CACHE_1D
    return get_tools().fuzzy_lookup(query, source=source, threshold=threshold, top_k=top_k)


@app.get("/lookup/semantic", response_model=list[LookupResult])
def semantic_lookup(
    query: str = Query(..., max_length=500),
    top_k: int = Query(default=5, ge=1, le=50),
    source: CorpusSource | None = Query(default=None, description="Corpus to search"),
    response: Response = None,
) -> list[dict]:
    """HNSW cosine semantic search via sentence embeddings."""
    response.headers["Cache-Control"] = _CACHE_1D
    return get_tools().semantic_lookup(query, top_k=top_k, source=source)


def main() -> None:  # pragma: no cover
    import uvicorn

    uvicorn.run(
        "linguaalayam.api.app:app",
        host="0.0.0.0",
        port=int(os.getenv("API_PORT", "8000")),
        reload=False,
    )

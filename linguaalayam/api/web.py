"""HTMX web UI routes — search page served as Jinja2 templates."""

import logging
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from omegaconf import OmegaConf

from linguaalayam.api.dependencies import get_tools
from linguaalayam.llm.adapters.nollm import NoLLMAdapter
from linguaalayam.rag.pipeline import _SYNTHESIS_SYSTEM, _SYNTHESIS_TEMPLATE, _format_entries
from linguaalayam.rag.query_understanding import understand_query
from linguaalayam.transliteration import (
    is_latin_script,
    malayalam_to_roman,
    roman_to_malayalam_candidates,
)

log = logging.getLogger(__name__)

_NO_LLM = NoLLMAdapter()
_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))
_TEMPLATES.env.filters["romanise_ml"] = malayalam_to_roman

router = APIRouter(include_in_schema=False)


def _make_llm(provider: str, key: str):
    """Instantiate an LLM adapter from a user-supplied key."""
    if provider == "openai":
        from linguaalayam.llm.adapters.openai import OpenAIAdapter

        return OpenAIAdapter(
            OmegaConf.create({"api_key": key, "model": "gpt-4o-mini", "max_tokens": 512})
        )
    from linguaalayam.llm.adapters.anthropic import AnthropicAdapter

    return AnthropicAdapter(
        OmegaConf.create({"api_key": key, "model": "claude-haiku-4-5-20251001", "max_tokens": 512})
    )


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _TEMPLATES.TemplateResponse(request, "index.html")


@router.get("/settings", response_class=HTMLResponse)
def settings(request: Request):
    return _TEMPLATES.TemplateResponse(request, "settings.html")


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    query: Annotated[str, Query()] = "",
    mode: Annotated[str, Query()] = "fuzzy",
    source: Annotated[str, Query()] = "",
    top_k: Annotated[int, Query()] = 10,
):
    results = []
    answer: str | None = None
    q = query.strip()
    src = source.strip() or None
    romanise = request.headers.get("X-Romanise", "").strip() == "1"

    headword = q
    if q:
        headword = understand_query(q, llm=_NO_LLM).headword or q
        tools = get_tools()
        if mode == "exact":
            results = tools.exact_lookup(headword, source=src)
        elif mode == "semantic" or (mode == "fuzzy" and " " in headword):
            # Multi-word fuzzy queries (understand_query couldn't reduce to single headword)
            # are phrases/definitions — semantic retrieval handles them better than trigram.
            results = tools.semantic_lookup(q, top_k=top_k, source=src)
        else:
            results = tools.fuzzy_lookup(headword, source=src, top_k=top_k)

        # Manglish fallback: Latin query with no results → try transliterated candidates.
        if not results and is_latin_script(headword):
            for ml_candidate in roman_to_malayalam_candidates(headword):
                if mode == "exact":
                    results = tools.exact_lookup(ml_candidate, source=src)
                else:
                    results = tools.fuzzy_lookup(ml_candidate, source=src, top_k=top_k)
                if results:
                    break

        # Semantic fallback for single-word fuzzy queries that got no results.
        # Multi-word queries already went through semantic above; skip to avoid double call.
        if not results and mode == "fuzzy" and " " not in headword:
            results = tools.semantic_lookup(q, top_k=top_k, source=src)

        llm_key = request.headers.get("X-LLM-Key", "").strip()
        if llm_key and results:
            try:
                provider = request.headers.get("X-LLM-Provider", "anthropic").lower()
                llm = _make_llm(provider, llm_key)
                entries_text = _format_entries(results[:top_k])
                content = _SYNTHESIS_TEMPLATE.format(query=q, entries=entries_text)
                answer = llm.complete(_SYNTHESIS_SYSTEM, content)
            except Exception:
                log.warning("LLM synthesis failed for %r", q, exc_info=True)

    return _TEMPLATES.TemplateResponse(
        request,
        "partials/results.html",
        {
            "results": results,
            "query": q,
            "headword": headword,
            "answer": answer,
            "source_filter": src,
            "romanise": romanise,
        },
    )

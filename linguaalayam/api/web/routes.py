"""HTMX web UI routes — search page served as Jinja2 templates."""

import logging
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from linguaalayam.api.dependencies import get_tools, get_translator
from linguaalayam.api.web import llm as llm_module
from linguaalayam.api.web.confidence import has_confident_result
from linguaalayam.api.web.decomposition import decompose_and_lookup
from linguaalayam.api.web.manglish import resolve_manglish
from linguaalayam.api.web.presentation import (
    AI_HINT_MIN_WORDS,
    ANSWER_LANGUAGE_NAMES,
    compute_ai_hint,
    compute_query_morphology,
    feature_tip,
)
from linguaalayam.api.web.synthesis import DecompositionSynthesis, WholePhraseSynthesis
from linguaalayam.api.web.templates import TEMPLATES
from linguaalayam.llm.adapters.base import LLMAdapter
from linguaalayam.rag.query_understanding import understand_query

log = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False)

# Logical source values expand to actual corpus names; no value searches all.
_SOURCE_EXPANSIONS: dict[str, list[str]] = {"ml_ml": ["datuk", "sayahna"]}


@router.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    """Serve the main search page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The rendered main search page. ``translation_enabled`` in its context
        drives whether the input-language picker offers non-EN/ML options.
    """
    return TEMPLATES.TemplateResponse(
        request,
        "index.html",
        {"translation_enabled": get_translator().supports_translation},
    )


@router.get("/settings")
def settings() -> RedirectResponse:
    """Redirect to the home page with the settings sidebar auto-opened.

    The standalone settings page was replaced by the sidebar in ``base.html``;
    this keeps old bookmarks/links (e.g. ``docs/user-guide.md``) working.

    Returns
    -------
    RedirectResponse
        Redirect to ``/?settings=1``.
    """
    return RedirectResponse(url="/?settings=1")


@router.get("/privacy", response_class=HTMLResponse)
def privacy(request: Request) -> HTMLResponse:
    """Serve the privacy page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The rendered privacy page.
    """
    return TEMPLATES.TemplateResponse(request, "privacy.html")


@router.get("/mcp/setup", response_class=HTMLResponse)
def mcp_setup(request: Request) -> HTMLResponse:
    """Serve the MCP setup page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request.

    Returns
    -------
    HTMLResponse
        The rendered MCP setup page.
    """
    return TEMPLATES.TemplateResponse(request, "mcp_setup.html")


@router.get("/mcp/setup/ping", response_class=HTMLResponse)
def mcp_ping() -> HTMLResponse:
    """Check the server's reachability.

    Returns
    -------
    HTMLResponse
        The server's reachability status.
    """
    try:
        get_tools()
        return HTMLResponse('<span class="ping-ok">✓ Server is reachable</span>')
    except Exception:
        return HTMLResponse(
            '<span class="ping-err">✗ Server error — try again</span>', status_code=503
        )


def _resolve_llm(request: Request, query: str) -> LLMAdapter | None:
    """Construct the LLM adapter for this request (BYOK or server-side), or None."""
    llm_key = request.headers.get("X-LLM-Key", "").strip()
    llm_enabled = request.headers.get("X-LLM-Enabled", "").strip() == "1"
    if not query or not (llm_key or llm_enabled):
        return None
    try:
        if llm_key:
            provider = request.headers.get("X-LLM-Provider", "togetherai").lower()
            return llm_module.make_llm(provider, llm_key)
        return llm_module.get_server_llm()
    except Exception:
        log.warning("Failed to construct LLM adapter", exc_info=True)
        return None


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    query: Annotated[str, Query()] = "",
    source: Annotated[str, Query()] = "",
    top_k: Annotated[int, Query()] = 10,
    lang: Annotated[str, Query()] = "en-US",
    debug: Annotated[bool, Query()] = False,
):
    """Handle a dictionary search request and return an HTMX partial or full results page.

    Parameters
    ----------
    request : Request
        The incoming HTTP request; headers ``X-Romanise``, ``X-LLM-Key``,
        ``X-LLM-Enabled``, and ``X-LLM-Provider`` are read for optional features.
    query : str, optional
        Search term (English, Malayalam, or Manglish).
    source : str, optional
        Corpus filter; ``"ml_ml"`` expands to both ``datuk`` and ``sayahna``.
    top_k : int, optional
        Maximum number of results to return; default ``10``.
    lang : str, optional
        BCP-47 language code for the query (used for translation pre-processing);
        default ``"en-US"``.
    debug : bool, optional
        When true and phrase decomposition actually ran, render a trace panel
        (per-word Varnam candidates, what the dictionary returned, and the
        exact prompt sent to the LLM) — a developer/debugging aid, not shown
        by default. No effect when decomposition didn't run.

    Returns
    -------
    HTMLResponse
        HTMX partial ``results.html`` fragment or the full results page.
    """
    results: list[dict] = []
    answer: str | None = None
    ai_hint: str | None = None
    varnam_used = False
    varnam_alternatives: list[str] = []
    manglish_suggestions: list[str] = []
    decomposition_trace: list[dict] = []
    decomposition_citations: list[dict] = []
    debug_prompt: dict[str, str] | None = None

    q = query.strip()
    src_filter = source.strip() or None
    src: str | list[str] | None = (
        _SOURCE_EXPANSIONS.get(src_filter, src_filter) if src_filter else None
    )
    romanise = request.headers.get("X-Romanise", "").strip() == "1"

    translation = get_translator().translate(q, source_lang=lang) if q else None
    q_en = translation.text if translation else q  # English (or original if EN/ML)

    tools = get_tools()
    llm = _resolve_llm(request, q)

    headword = q_en
    if q:
        headword = understand_query(q_en, llm=llm or llm_module.NO_LLM).headword or q_en
        results = tools.fuzzy_lookup(headword, source=src, top_k=top_k)

        resolution = resolve_manglish(
            headword, results, translation=translation, request=request, tools=tools, src=src
        )
        headword, results = resolution.headword, resolution.results
        varnam_used = resolution.varnam_used
        varnam_alternatives = resolution.varnam_alternatives
        manglish_suggestions = resolution.manglish_suggestions

        worth_synthesizing = len(q.split()) >= AI_HINT_MIN_WORDS or not has_confident_result(
            results
        )

        # Prefer `headword` when it's multi-word; fall back to the original
        # multi-word query when understand_query collapsed it to one word.
        decompose_target = headword if " " in headword else (q_en if " " in q_en else None)
        word_entries: list[tuple[str, list[dict]]] = []
        if llm and decompose_target and worth_synthesizing:
            word_entries, decomposition_trace = decompose_and_lookup(decompose_target, tools, src)

        if (results or word_entries) and llm and worth_synthesizing:
            strategy = (
                DecompositionSynthesis(word_entries)
                if word_entries
                else WholePhraseSynthesis(results, top_k)
            )
            try:
                answer_lang = ANSWER_LANGUAGE_NAMES.get(translation.source_lang, "English")
                synthesis = strategy.synthesize(llm, q, answer_lang, debug)
                answer = synthesis.answer
                decomposition_citations = synthesis.citations
                debug_prompt = synthesis.debug_prompt
            except Exception:
                log.warning("LLM synthesis failed for %r", q, exc_info=True)

        llm_key = request.headers.get("X-LLM-Key", "").strip()
        llm_enabled = request.headers.get("X-LLM-Enabled", "").strip() == "1"
        ai_hint = compute_ai_hint(
            answer=answer, llm_key=llm_key, llm_enabled=llm_enabled, query=q, results=results
        )

    query_morphology = compute_query_morphology(q, translation)
    tip = feature_tip(headword, skip_mlmorph=bool(query_morphology)) if answer else None

    return TEMPLATES.TemplateResponse(
        request,
        "partials/results.html",
        {
            "results": results,
            "query": q,
            "headword": headword,
            "answer": answer,
            "tip": tip,
            "ai_hint": ai_hint,
            "source_filter": src,
            "romanise": romanise,
            "query_morphology": query_morphology,
            "translation": translation,
            "headword_set": tools.ml_headword_set(),
            "varnam_used": varnam_used,
            "varnam_alternatives": varnam_alternatives,
            "manglish_suggestions": manglish_suggestions,
            "debug": debug,
            "decomposition_trace": decomposition_trace,
            "decomposition_citations": decomposition_citations,
            "debug_prompt": debug_prompt,
        },
    )

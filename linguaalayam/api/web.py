"""HTMX web UI routes — search page served as Jinja2 templates."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from linguaalayam.api.dependencies import get_tools

_TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parents[1] / "templates"))

router = APIRouter(include_in_schema=False)


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    return _TEMPLATES.TemplateResponse("index.html", {"request": request})


@router.get("/search", response_class=HTMLResponse)
def search(
    request: Request,
    query: Annotated[str, Query()] = "",
    mode: Annotated[str, Query()] = "fuzzy",
    source: Annotated[str, Query()] = "",
    top_k: Annotated[int, Query()] = 10,
):
    results = []
    q = query.strip()
    src = source.strip() or None

    if q:
        tools = get_tools()
        if mode == "exact":
            results = tools.exact_lookup(q, source=src)
        elif mode == "semantic":
            results = tools.semantic_lookup(q, top_k=top_k, source=src)
        else:
            results = tools.fuzzy_lookup(q, source=src, top_k=top_k)

    return _TEMPLATES.TemplateResponse(
        "partials/results.html",
        {"request": request, "results": results, "query": q},
    )

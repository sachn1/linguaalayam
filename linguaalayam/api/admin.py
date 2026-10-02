"""Admin-only traffic/usage analytics dashboard, gated behind HTTP Basic Auth."""

import datetime
import os
import secrets
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from linguaalayam.api.dependencies import get_session_factory
from linguaalayam.api.web import _TEMPLATES
from linguaalayam.database import get_session
from linguaalayam.observability import (
    searches_by_country,
    top_clients_simple,
    top_feature_usage,
    top_locations,
    top_outbound_clicks,
    top_queries_with_sources,
)

router = APIRouter(include_in_schema=False)
_basic_auth = HTTPBasic()


def _require_admin(credentials: Annotated[HTTPBasicCredentials, Depends(_basic_auth)]) -> None:
    """Validate HTTP Basic credentials against ADMIN_USER / ADMIN_PASSWORD env vars.

    Uses ``secrets.compare_digest`` for both fields to avoid timing side-channels.

    Raises
    ------
    HTTPException
        401 if credentials are missing, misconfigured, or don't match.
    """
    expected_user = os.getenv("ADMIN_USER")
    expected_password = os.getenv("ADMIN_PASSWORD")
    if not expected_user or not expected_password:
        raise HTTPException(status_code=503, detail="Admin auth not configured")

    user_ok = secrets.compare_digest(credentials.username, expected_user)
    password_ok = secrets.compare_digest(credentials.password, expected_password)
    if not (user_ok and password_ok):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


def _window_start(window_minutes: int) -> datetime.datetime:
    """Return the UTC timestamp marking the start of the requested lookback window."""
    return datetime.datetime.now(datetime.UTC) - datetime.timedelta(minutes=window_minutes)


def _fmt(timestamp: datetime.datetime) -> str:
    """Format a timestamp for display, e.g. ``2026-09-10 20:29 UTC``."""
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


@router.get("/admin/analytics", response_class=HTMLResponse, dependencies=[Depends(_require_admin)])
def analytics_page(request: Request) -> HTMLResponse:
    """Serve the traffic/usage analytics dashboard shell."""
    return _TEMPLATES.TemplateResponse(request, "admin_analytics.html")


@router.get(
    "/admin/analytics/partial",
    response_class=HTMLResponse,
    dependencies=[Depends(_require_admin)],
)
def analytics_partial(
    request: Request,
    window_minutes: Annotated[int, Query(ge=1, le=525600)] = 60,
) -> HTMLResponse:
    """Return the HTMX-polled analytics fragment for the given lookback window."""
    since = _window_start(window_minutes)
    session_factory = get_session_factory()
    with get_session(session_factory) as session:
        queries = top_queries_with_sources(session, since, limit=20)
        by_country = searches_by_country(session, since, limit=20)
        by_location = top_locations(session, since, limit=20)
        clicks = top_outbound_clicks(session, since, limit=10)
        feature_usage = top_feature_usage(session, since, limit=10)
        clients = top_clients_simple(session, since, limit=10)

    total_searches = sum(count for _, count, _, _, _, _ in queries)
    unique_queries = len(queries)
    queries_with_sources = [
        (
            query,
            count,
            ", ".join(f"{country}({n})" for country, n in countries) or "—",
            ", ".join(client_ips) or "—",
            _fmt(first_seen),
            _fmt(last_seen),
        )
        for query, count, countries, client_ips, first_seen, last_seen in queries
    ]
    by_country_fmt = [
        (country, count, unique, _fmt(first_seen), _fmt(last_seen))
        for country, count, unique, first_seen, last_seen in by_country
    ]
    by_location_fmt = [
        (
            city or "Unknown",
            region or "—",
            country or "—",
            count,
            unique,
            _fmt(first_seen),
            _fmt(last_seen),
        )
        for city, region, country, count, unique, first_seen, last_seen in by_location
    ]
    clients_fmt = [
        (ip, count, _fmt(first_seen), _fmt(last_seen))
        for ip, count, first_seen, last_seen in clients
    ]

    return _TEMPLATES.TemplateResponse(
        request,
        "partials/admin_analytics_partial.html",
        {
            "window_minutes": window_minutes,
            "total_searches": total_searches,
            "unique_queries": unique_queries,
            "queries_with_sources": queries_with_sources,
            "by_country": by_country_fmt,
            "by_location": by_location_fmt,
            "clicks": clicks,
            "feature_usage": feature_usage,
            "top_clients_list": clients_fmt,
        },
    )

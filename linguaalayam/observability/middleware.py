"""ASGI middleware that records one request_log row per real search bar query."""

import logging
import re
import time

from anyio import to_thread
from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send

from linguaalayam.api.dependencies import get_session_factory
from linguaalayam.database.session import get_session
from linguaalayam.observability.geoip import locate_ip
from linguaalayam.observability.http import client_ip
from linguaalayam.observability.queries import log_request

log = logging.getLogger(__name__)

# Coarse route classification for analytics — path prefix -> route_type label.
# More specific prefixes (e.g. "/mcp/setup") must precede broader ones (e.g. "/mcp")
# since the first match wins — otherwise a human viewing the setup page would be
# counted the same as an AI assistant's actual MCP protocol traffic.
_ROUTE_TYPES: list[tuple[str, str]] = [
    ("/search", "web_search"),
    ("/lookup/exact", "lookup_exact"),
    ("/lookup/fuzzy", "lookup_fuzzy"),
    ("/lookup/semantic", "lookup_semantic"),
    ("/mcp/setup", "mcp_setup_page"),
    ("/mcp", "mcp"),
    ("/health", "health"),
    ("/docs", "api_docs"),
    ("/openapi.json", "api_docs"),
    ("/static", "static"),
]

# Paths never worth processing — skip immediately.
_EXCLUDED_PREFIXES = ("/admin", "/health", "/track/click")

# Known crawler/bot user-agent substrings (case-insensitive). Not authoritative —
# Cloudflare's real bot score is an Enterprise-only feature — but enough to separate
# obvious automated traffic (search engine crawlers, uptime pingers, HTTP libraries)
# from browser-driven use when eyeballing the request_log table.
_BOT_UA_PATTERN = re.compile(
    r"bot|crawl|spider|slurp|curl|wget|python-requests|httpx|axios|go-http-client|"
    r"scrapy|headless|monitor|pingdom|uptimerobot|facebookexternalhit",
    re.IGNORECASE,
)


def classify_route(path: str) -> str:
    """Map a request path to a coarse route_type label for analytics."""
    for prefix, route_type in _ROUTE_TYPES:
        if path.startswith(prefix):
            return route_type
    return "other"


def looks_like_bot(user_agent: str | None) -> bool:
    """Heuristic guess that a request is automated, based on its User-Agent string."""
    return bool(user_agent) and bool(_BOT_UA_PATTERN.search(user_agent))


class RequestLoggingMiddleware:
    """Raw ASGI middleware that records one ``request_log`` row per real search bar query.

    Only logs ``/search`` requests with a non-empty ``query`` parameter from
    non-bot clients. Everything else (static assets, API docs, health probes,
    MCP traffic, empty typing, bots/scrapers) is intentionally ignored —
    Cloudflare already covers that. The owner cares about where actual
    dictionary searches come from, not every HTTP hit.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope["path"].startswith(_EXCLUDED_PREFIXES):
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        status_holder: dict[str, int] = {}

        async def send_wrapper(message: dict) -> None:
            if message["type"] == "http.response.start":
                status_holder["status"] = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            duration_ms = (time.monotonic() - start) * 1000
            status_code = status_holder.get("status", 0)
            await to_thread.run_sync(self._record, scope, status_code, duration_ms)

    @staticmethod
    def _record(scope: Scope, status_code: int, duration_ms: float) -> None:
        """Best-effort insert of one analytics row — never let logging break a request."""
        try:
            request = Request(scope)
            path = request.url.path
            query = request.query_params.get("query", "").strip()

            route_type = classify_route(path)
            is_bot = looks_like_bot(request.headers.get("user-agent"))

            # Only log real search bar queries with actual content from real humans.
            if route_type != "web_search" or not query or is_bot:
                return

            ip = client_ip(request)
            # CF-IPCountry is free and already-resolved when Cloudflare is
            # proxying; the GeoIP lookup is the fallback (and the only source
            # of city/region) for traffic that reaches Cloud Run directly.
            city, region, geoip_country = locate_ip(ip)
            country = request.headers.get("cf-ipcountry") or geoip_country

            session_factory = get_session_factory()
            with get_session(session_factory) as session:
                log_request(
                    session,
                    method=request.method,
                    path=path,
                    route_type=route_type,
                    query=query,
                    status_code=status_code,
                    duration_ms=duration_ms,
                    ip=ip,
                    city=city,
                    region=region,
                    country=country,
                    user_agent=request.headers.get("user-agent"),
                    is_bot=False,
                )
        except Exception:  # pragma: no cover — logging must never break a request
            log.warning("Failed to record request_log entry", exc_info=True)

"""Request-level traffic and usage analytics — model, queries, and ASGI middleware."""

from .events import log_feature_event
from .middleware import RequestLoggingMiddleware, classify_route, looks_like_bot
from .models import RequestLog
from .queries import (
    log_request,
    searches_by_country,
    top_clients_simple,
    top_outbound_clicks,
    top_queries_with_sources,
)
from .router import router as click_tracking_router

__all__ = [
    "RequestLog",
    "RequestLoggingMiddleware",
    "classify_route",
    "click_tracking_router",
    "log_feature_event",
    "log_request",
    "looks_like_bot",
    "searches_by_country",
    "top_clients_simple",
    "top_outbound_clicks",
    "top_queries_with_sources",
]

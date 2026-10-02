"""Request-metadata helpers shared by the ASGI middleware and one-off feature events."""

from starlette.requests import Request


def client_ip(request: Request) -> str | None:
    """Best-guess client IP.

    Prefers Cloudflare's own header (set only when Cloudflare is proxying,
    which it no longer does for the production hostnames — see
    ``X-Forwarded-For`` below), then Cloud Run's/any reverse proxy's
    ``X-Forwarded-For`` (leftmost entry is the original client), then falls
    back to the raw ASGI transport address.
    """
    if cf_ip := request.headers.get("cf-connecting-ip"):
        return cf_ip
    if forwarded := request.headers.get("x-forwarded-for"):
        return forwarded.split(",")[0].strip() or None
    return request.client.host if request.client else None

"""Request-metadata helpers shared by the ASGI middleware and one-off feature events."""

from starlette.requests import Request

from linguaalayam.observability.geoip import locate_ip


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


def client_location(request: Request) -> tuple[str | None, str | None, str | None, str | None]:
    """Resolve ``(ip, city, region, country)`` for the request's client.

    Country prefers Cloudflare's ``CF-IPCountry`` header when present (free,
    already-resolved); city/region always come from the local GeoIP lookup,
    since Cloud Run/Cloudflare have no equivalent header for those.
    """
    ip = client_ip(request)
    city, region, geoip_country = locate_ip(ip)
    country = request.headers.get("cf-ipcountry") or geoip_country
    return ip, city, region, country

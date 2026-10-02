"""Tests for client_ip's header fallback chain in observability/http.py."""

from starlette.requests import Request

from linguaalayam.observability.http import client_ip


def _request(headers: dict[str, str], client_host: str | None = "203.0.113.9") -> Request:
    scope = {
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": (client_host, 12345) if client_host else None,
    }
    return Request(scope)


class TestClientIp:
    """Header precedence: CF-Connecting-IP > X-Forwarded-For > transport address."""

    def test_prefers_cf_connecting_ip(self):
        """CF-Connecting-IP wins even when X-Forwarded-For is also present."""
        req = _request({"cf-connecting-ip": "198.51.100.1", "x-forwarded-for": "198.51.100.2"})
        assert client_ip(req) == "198.51.100.1"

    def test_falls_back_to_x_forwarded_for(self):
        """Without Cloudflare's header, the leftmost X-Forwarded-For entry is used."""
        req = _request({"x-forwarded-for": "198.51.100.3, 10.0.0.1, 10.0.0.2"})
        assert client_ip(req) == "198.51.100.3"

    def test_falls_back_to_transport_address(self):
        """With no relevant headers at all, use the raw ASGI transport address."""
        req = _request({})
        assert client_ip(req) == "203.0.113.9"

    def test_none_when_nothing_available(self):
        """No headers and no transport client resolves to None, not an error."""
        req = _request({}, client_host=None)
        assert client_ip(req) is None

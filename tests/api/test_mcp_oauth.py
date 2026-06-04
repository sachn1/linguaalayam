"""OAuth discovery + dynamic-registration tests for the MCP connector.

Regression guard for the Claude connector "couldn't register with sign-in
service" failure: clients probe several RFC 9728 / RFC 8414 well-known URLs and
abort if any in their strategy 404s or omits the public-client ("none") auth
method.  These tests assert every discovery variant is served consistently and
that the full auth-code + PKCE flow completes end to end.
"""

import base64
import hashlib
import secrets
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from linguaalayam.api.app import app
from linguaalayam.mcp.remote import _ISSUER_URL

_RESOURCE = _ISSUER_URL.rstrip("/")
_CLAUDE_REDIRECT = "https://claude.ai/api/mcp/auth_callback"


@pytest.fixture()
def client():
    return TestClient(app, raise_server_exceptions=True)


# ── discovery: every variant Claude may probe must return 200 ───────────────────

_AS_PATHS = [
    "/.well-known/oauth-authorization-server",
    "/.well-known/oauth-authorization-server/mcp",
    "/.well-known/oauth-authorization-server/mcp/",
]
_PR_PATHS = [
    "/.well-known/oauth-protected-resource",
    "/.well-known/oauth-protected-resource/mcp",
]


@pytest.mark.parametrize("path", _AS_PATHS)
def test_authorization_server_metadata_served(client, path):
    r = client.get(path)
    assert r.status_code == 200, path
    meta = r.json()
    # endpoints all share the issuer base
    assert meta["issuer"] == _RESOURCE
    for ep in ("authorization_endpoint", "token_endpoint", "registration_endpoint"):
        assert meta[ep].startswith(_RESOURCE), (ep, meta[ep])
    # public PKCE clients (token_endpoint_auth_method=none) must be advertised
    assert "none" in meta["token_endpoint_auth_methods_supported"]
    assert "S256" in meta["code_challenge_methods_supported"]


_OIDC_PATHS = [
    "/.well-known/openid-configuration",
    "/.well-known/openid-configuration/mcp",
]


@pytest.mark.parametrize("path", _OIDC_PATHS)
def test_openid_configuration_alias_served(client, path):
    # the MCP TS SDK probes OIDC discovery; serve the same AS metadata there
    r = client.get(path)
    assert r.status_code == 200, path
    assert "token_endpoint" in r.json()


@pytest.mark.parametrize("path", _PR_PATHS)
def test_protected_resource_metadata_served(client, path):
    r = client.get(path)
    assert r.status_code == 200, path
    meta = r.json()
    assert meta["resource"] == _RESOURCE
    assert meta["authorization_servers"] == [_RESOURCE]


def test_as_metadata_consistent_across_paths(client):
    bodies = [client.get(p).json() for p in _AS_PATHS]
    assert all(b == bodies[0] for b in bodies)


# ── dynamic client registration (RFC 7591) ──────────────────────────────────────


def test_dynamic_client_registration(client):
    body = {
        "client_name": "Claude",
        "redirect_uris": [_CLAUDE_REDIRECT],
        "grant_types": ["authorization_code", "refresh_token"],
        "response_types": ["code"],
        "token_endpoint_auth_method": "none",
        "scope": "dictionary",
    }
    r = client.post("/mcp/register", json=body)
    assert r.status_code == 201, r.text
    reg = r.json()
    assert reg["client_id"]
    assert reg["redirect_uris"] == [_CLAUDE_REDIRECT]
    assert reg["token_endpoint_auth_method"] == "none"


# ── full auth-code + PKCE flow, as Claude runs it ───────────────────────────────


def _pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    challenge = (
        base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    )
    return verifier, challenge


def test_end_to_end_authorization_code_flow(client):
    # 1. register
    reg = client.post(
        "/mcp/register",
        json={
            "client_name": "Claude",
            "redirect_uris": [_CLAUDE_REDIRECT],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": "dictionary",
        },
    ).json()
    client_id = reg["client_id"]

    # 2. authorize (auto-approved) → redirect back with ?code=…
    verifier, challenge = _pkce()
    state = secrets.token_urlsafe(8)
    r = client.get(
        "/mcp/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": _CLAUDE_REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": state,
            "scope": "dictionary",
        },
        follow_redirects=False,
    )
    assert r.status_code in (302, 307), r.text
    location = r.headers["location"]
    assert location.startswith(_CLAUDE_REDIRECT)
    assert f"state={state}" in location
    code = location.split("code=")[1].split("&")[0]

    # 3. exchange code for a token (public client, PKCE verifier, no secret)
    r = client.post(
        "/mcp/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _CLAUDE_REDIRECT,
            "client_id": client_id,
            "code_verifier": verifier,
        },
    )
    assert r.status_code == 200, r.text
    tok = r.json()
    assert tok["access_token"]
    assert tok["token_type"].lower() == "bearer"
    assert tok["refresh_token"]


def _obtain_token(client: TestClient, prefix: str = "/mcp") -> str:
    """Run register → authorize → token. prefix="/mcp" exercises the FastMCP
    endpoints; prefix="" exercises the root-proxied endpoints that the MCP TS
    SDK (Inspector / Claude) actually hits."""
    reg = client.post(
        f"{prefix}/register",
        json={
            "client_name": "Claude",
            "redirect_uris": [_CLAUDE_REDIRECT],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": "dictionary",
        },
    ).json()
    verifier, challenge = _pkce()
    loc = client.get(
        f"{prefix}/authorize",
        params={
            "response_type": "code",
            "client_id": reg["client_id"],
            "redirect_uri": _CLAUDE_REDIRECT,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "state": "s",
            "scope": "dictionary",
        },
        follow_redirects=False,
    ).headers["location"]
    code = loc.split("code=")[1].split("&")[0]
    return client.post(
        f"{prefix}/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": _CLAUDE_REDIRECT,
            "client_id": reg["client_id"],
            "code_verifier": verifier,
        },
    ).json()["access_token"]


def _initialize(client: TestClient, token: str) -> tuple:
    r = client.post(
        "/mcp/",
        headers={
            "Authorization": f"Bearer {token}",
            "content-type": "application/json",
            "accept": "application/json, text/event-stream",
        },
        json={
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-06-18",
                "capabilities": {},
                "clientInfo": {"name": "test", "version": "1"},
            },
        },
    )
    return r, r.headers.get("mcp-session-id")


def test_authenticated_mcp_initialize_and_list_tools():
    """Two regressions in one lifespan (session_manager.run() is once-per-process):

    1. The mounted MCP sub-app needs its session manager started in the app
       lifespan, else every authenticated MCP request 500s.
    2. The MCP TS SDK (Inspector / Claude) runs OAuth against the ROOT
       (/register, /authorize, /token), not /mcp/* — the root proxy must work.

    Drives the full root-based flow → initialize → tools/list, and confirms a
    token minted via the /mcp-prefixed endpoints initializes too.
    """
    with (
        patch("linguaalayam.api.app._ensure_docker_db"),
        patch("linguaalayam.api.app._init_tools", return_value=MagicMock()),
    ):
        with TestClient(app) as client:  # `with` runs lifespan → starts session mgr
            # origin-based flow (what the real client does): endpoints at root
            root_token = _obtain_token(client, prefix="")
            init, sid = _initialize(client, root_token)
            assert init.status_code == 200, init.text
            assert "serverInfo" in init.text
            assert sid

            h = {
                "Authorization": f"Bearer {root_token}",
                "content-type": "application/json",
                "accept": "application/json, text/event-stream",
                "mcp-session-id": sid,
            }
            client.post(
                "/mcp/", headers=h, json={"jsonrpc": "2.0", "method": "notifications/initialized"}
            )
            tl = client.post(
                "/mcp/", headers=h, json={"jsonrpc": "2.0", "id": 2, "method": "tools/list"}
            )
            assert tl.status_code == 200, tl.text
            for name in ("exact_lookup", "fuzzy_lookup", "semantic_lookup"):
                assert name in tl.text

            # a token minted via the /mcp-prefixed endpoints is equally valid
            prefixed_init, _ = _initialize(client, _obtain_token(client, prefix="/mcp"))
            assert prefixed_init.status_code == 200, prefixed_init.text

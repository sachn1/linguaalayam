"""Unit tests for PassthroughOAuthProvider, independent of the HTTP/MCP layer."""

import asyncio
import time
from unittest.mock import patch

from mcp.server.auth.provider import AuthorizationCode, AuthorizationParams
from mcp.shared.auth import OAuthClientInformationFull

from linguaalayam.api.oauth import PassthroughOAuthProvider


def _client(client_id: str = "client-1") -> OAuthClientInformationFull:
    """Build a minimal registered-client object for tests."""
    return OAuthClientInformationFull(
        client_id=client_id,
        redirect_uris=["https://claude.ai/api/mcp/auth_callback"],
    )


def _params(**overrides) -> AuthorizationParams:
    """Build minimal authorization params for tests."""
    defaults = {
        "state": "xyz",
        "scopes": ["mcp"],
        "code_challenge": "challenge",
        "redirect_uri": "https://claude.ai/api/mcp/auth_callback",
        "redirect_uri_provided_explicitly": True,
        "resource": None,
    }
    defaults.update(overrides)
    return AuthorizationParams(**defaults)


async def _authorize_and_extract_code(provider: PassthroughOAuthProvider, client) -> str:
    """Run the authorize step and pull the generated code out of the redirect URI."""
    redirect = await provider.authorize(client, _params())
    return redirect.split("code=")[1].split("&")[0]


class TestClientRegistration:
    def test_register_then_get_round_trips(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            await provider.register_client(client)
            return await provider.get_client("client-1")

        assert asyncio.run(_run()).client_id == "client-1"

    def test_get_unregistered_client_returns_none(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            return await provider.get_client("never-registered")

        assert asyncio.run(_run()) is None


class TestAuthorizationCodeFlow:
    def test_authorize_generates_a_redirect_with_code_and_state(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            return await provider.authorize(_client(), _params(state="xyz"))

        redirect = asyncio.run(_run())
        assert "code=" in redirect
        assert "state=xyz" in redirect

    def test_load_authorization_code_returns_what_was_issued(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            return await provider.load_authorization_code(client, code)

        loaded = asyncio.run(_run())
        assert isinstance(loaded, AuthorizationCode)
        assert loaded.client_id == "client-1"

    def test_load_authorization_code_returns_none_for_unknown_code(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            return await provider.load_authorization_code(_client(), "never-issued")

        assert asyncio.run(_run()) is None

    def test_load_authorization_code_returns_none_once_expired(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            with patch("linguaalayam.api.oauth.time.time", return_value=time.time() + 601):
                return await provider.load_authorization_code(client, code)

        assert asyncio.run(_run()) is None

    def test_exchange_authorization_code_returns_tokens_and_consumes_the_code(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            auth_code = await provider.load_authorization_code(client, code)
            token = await provider.exchange_authorization_code(client, auth_code)
            still_there = await provider.load_authorization_code(client, code)
            return token, still_there

        token, still_there = asyncio.run(_run())
        assert token.token_type.lower() == "bearer"
        assert token.access_token and token.refresh_token
        assert still_there is None  # one-time use


class TestAccessTokenVerification:
    def test_load_access_token_returns_the_issued_token(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            auth_code = await provider.load_authorization_code(client, code)
            issued = await provider.exchange_authorization_code(client, auth_code)
            return issued, await provider.load_access_token(issued.access_token)

        issued, loaded = asyncio.run(_run())
        assert loaded.token == issued.access_token

    def test_load_access_token_returns_none_for_unknown_token(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            return await provider.load_access_token("never-issued")

        assert asyncio.run(_run()) is None

    def test_load_access_token_returns_none_once_expired(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            auth_code = await provider.load_authorization_code(client, code)
            issued = await provider.exchange_authorization_code(client, auth_code)
            with patch(
                "linguaalayam.api.oauth.time.time",
                return_value=time.time() + 86_400 * 31,
            ):
                return await provider.load_access_token(issued.access_token)

        assert asyncio.run(_run()) is None


class TestRefreshTokenFlow:
    def test_exchange_refresh_token_issues_a_new_access_and_refresh_token(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            auth_code = await provider.load_authorization_code(client, code)
            issued = await provider.exchange_authorization_code(client, auth_code)
            refresh_token = await provider.load_refresh_token(client, issued.refresh_token)
            new_tokens = await provider.exchange_refresh_token(client, refresh_token, [])
            old_still_valid = await provider.load_refresh_token(client, issued.refresh_token)
            return new_tokens, old_still_valid

        new_tokens, old_still_valid = asyncio.run(_run())
        assert new_tokens.access_token and new_tokens.refresh_token
        assert old_still_valid is None  # old refresh token consumed

    def test_load_refresh_token_returns_none_for_unknown_token(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            return await provider.load_refresh_token(_client(), "never-issued")

        assert asyncio.run(_run()) is None


class TestRevocation:
    def test_revoke_access_token_removes_it(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            auth_code = await provider.load_authorization_code(client, code)
            issued = await provider.exchange_authorization_code(client, auth_code)
            access = await provider.load_access_token(issued.access_token)
            await provider.revoke_token(access)
            return await provider.load_access_token(issued.access_token)

        assert asyncio.run(_run()) is None

    def test_revoke_refresh_token_removes_it(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            auth_code = await provider.load_authorization_code(client, code)
            issued = await provider.exchange_authorization_code(client, auth_code)
            refresh = await provider.load_refresh_token(client, issued.refresh_token)
            await provider.revoke_token(refresh)
            return await provider.load_refresh_token(client, issued.refresh_token)

        assert asyncio.run(_run()) is None


class TestPurgeExpired:
    def test_purge_removes_only_expired_entries(self):
        async def _run():
            provider = PassthroughOAuthProvider()
            client = _client()
            code = await _authorize_and_extract_code(provider, client)
            with patch("linguaalayam.api.oauth.time.time", return_value=time.time() + 601):
                provider._purge_expired()
            return provider._codes, code

        codes, code = asyncio.run(_run())
        assert code not in codes

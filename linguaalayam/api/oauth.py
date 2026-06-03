"""Passthrough OAuth 2.0 provider for the MCP server.

LinguAalayam is a public dictionary — no user accounts, no secrets to protect.
OAuth is required only so Claude.ai's browser MCP connector can connect.

This provider auto-approves every authorization request: any client that registers
via RFC 7591 dynamic registration receives an authorization code immediately (no
login screen), and that code is exchanged for a long-lived access token.

Tokens are stored in-memory. A server restart invalidates all tokens; clients
will re-authorize automatically on next use.
"""

import secrets
import time

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    OAuthAuthorizationServerProvider,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

_TOKEN_TTL = 86_400 * 30  # 30 days


class PassthroughOAuthProvider(
    OAuthAuthorizationServerProvider[AuthorizationCode, RefreshToken, AccessToken]
):
    """In-memory OAuth AS that auto-approves every request."""

    def __init__(self) -> None:
        self._clients: dict[str, OAuthClientInformationFull] = {}
        self._codes: dict[str, AuthorizationCode] = {}
        self._access: dict[str, AccessToken] = {}
        self._refresh: dict[str, RefreshToken] = {}

    # ---- RFC 7591 dynamic client registration ----

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        return self._clients.get(client_id)

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        self._clients[client_info.client_id] = client_info

    # ---- Authorization code flow ----

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        """Auto-approve: generate a code and redirect immediately."""
        code = secrets.token_urlsafe(32)
        self._codes[code] = AuthorizationCode(
            code=code,
            scopes=params.scopes or [],
            expires_at=time.time() + 600,
            client_id=client.client_id,
            code_challenge=params.code_challenge,
            redirect_uri=params.redirect_uri,
            redirect_uri_provided_explicitly=params.redirect_uri_provided_explicitly,
            resource=params.resource,
        )
        return construct_redirect_uri(str(params.redirect_uri), code=code, state=params.state)

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        code = self._codes.get(authorization_code)
        if code and code.expires_at < time.time():
            del self._codes[authorization_code]
            return None
        return code

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        self._codes.pop(authorization_code.code, None)
        access = secrets.token_urlsafe(32)
        refresh = secrets.token_urlsafe(32)
        expires_at = int(time.time()) + _TOKEN_TTL
        self._access[access] = AccessToken(
            token=access,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=expires_at,
            resource=authorization_code.resource,
        )
        self._refresh[refresh] = RefreshToken(
            token=refresh,
            client_id=client.client_id,
            scopes=authorization_code.scopes,
            expires_at=expires_at,
        )
        return OAuthToken(
            access_token=access,
            token_type="bearer",
            expires_in=_TOKEN_TTL,
            refresh_token=refresh,
            scope=" ".join(authorization_code.scopes),
        )

    # ---- Refresh token flow ----

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        token = self._refresh.get(refresh_token)
        if token and token.expires_at and token.expires_at < time.time():
            del self._refresh[refresh_token]
            return None
        return token

    async def exchange_refresh_token(
        self,
        client: OAuthClientInformationFull,
        refresh_token: RefreshToken,
        scopes: list[str],
    ) -> OAuthToken:
        self._refresh.pop(refresh_token.token, None)
        access = secrets.token_urlsafe(32)
        new_refresh = secrets.token_urlsafe(32)
        effective_scopes = scopes or refresh_token.scopes
        expires_at = int(time.time()) + _TOKEN_TTL
        self._access[access] = AccessToken(
            token=access,
            client_id=client.client_id,
            scopes=effective_scopes,
            expires_at=expires_at,
        )
        self._refresh[new_refresh] = RefreshToken(
            token=new_refresh,
            client_id=client.client_id,
            scopes=effective_scopes,
            expires_at=expires_at,
        )
        return OAuthToken(
            access_token=access,
            token_type="bearer",
            expires_in=_TOKEN_TTL,
            refresh_token=new_refresh,
            scope=" ".join(effective_scopes),
        )

    # ---- Token verification ----

    async def load_access_token(self, token: str) -> AccessToken | None:
        access = self._access.get(token)
        if access and access.expires_at and access.expires_at < time.time():
            del self._access[token]
            return None
        return access

    # ---- Revocation ----

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        if isinstance(token, AccessToken):
            self._access.pop(token.token, None)
        else:
            self._refresh.pop(token.token, None)

    # ---- Utility ----

    def _purge_expired(self) -> None:
        """Remove expired tokens to prevent unbounded memory growth."""
        now = time.time()
        self._codes = {k: v for k, v in self._codes.items() if v.expires_at >= now}
        self._access = {
            k: v for k, v in self._access.items() if not v.expires_at or v.expires_at >= now
        }
        self._refresh = {
            k: v for k, v in self._refresh.items() if not v.expires_at or v.expires_at >= now
        }

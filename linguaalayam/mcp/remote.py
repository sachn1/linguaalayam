"""Remote MCP server — mounted into the FastAPI app at /mcp.

Shares DictionaryTools with the REST API (no second DB connection or model load).
Clients connect via URL: https://linguaalayam.org/mcp — no local install required.

OAuth 2.0 (RFC 7591 dynamic registration + PKCE) is enabled so Claude.ai's browser
MCP connector can authenticate. The provider is a passthrough — it auto-approves
every authorization request because LinguAalayam is a public dictionary service with
no user accounts. Tokens are in-memory; a server restart invalidates them and clients
re-authorize automatically.
"""

import os

from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions, RevocationOptions
from mcp.server.fastmcp import FastMCP
from pydantic import AnyHttpUrl
from starlette.applications import Starlette

from linguaalayam.api.dependencies import get_tools
from linguaalayam.api.oauth import PassthroughOAuthProvider
from linguaalayam.mcp.shared import format_results as _format

_ISSUER_URL = os.environ.get("MCP_ISSUER_URL", "http://localhost:8000/mcp")

_oauth_provider = PassthroughOAuthProvider()

mcp = FastMCP(
    "linguaalayam",
    instructions=(
        "Malayalam lexical knowledge base built on the Olam, Datuk, and Ekkurup corpora. "
        "Use exact_lookup first for a known word spelling. "
        "Use fuzzy_lookup for approximate matches or typos. "
        "Use semantic_lookup for meaning-based queries or when the exact headword is unknown."
    ),
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(_ISSUER_URL),
        service_documentation_url=AnyHttpUrl("https://linguaalayam.org/mcp/setup"),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=["dictionary"],
            default_scopes=["dictionary"],
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=["dictionary"],
        resource_server_url=None,
    ),
    auth_server_provider=_oauth_provider,
)


@mcp.resource("dictionary://{headword}")
def get_entry(headword: str) -> str:
    """Browse a dictionary entry by URI (e.g. dictionary://run)."""
    results = get_tools().exact_lookup(headword)
    return _format(results, headword, "exact")


@mcp.tool()
def exact_lookup(word: str, source: str | None = None) -> str:
    """Look up a word by exact headword match (case-insensitive).

    Args:
        word: The word to look up (English or Malayalam).
        source: Optional corpus filter (e.g. "olam_enml"). Searches all corpora if omitted.
    """
    results = get_tools().exact_lookup(word, source=source)
    return _format(results, word, "exact")


@mcp.tool()
def fuzzy_lookup(
    query: str,
    threshold: float = 0.3,
    top_k: int = 10,
    source: str | None = None,
) -> str:
    """Search for words by approximate headword similarity (trigram).

    Args:
        query: The word or partial word to search for.
        threshold: Minimum trigram similarity score (0–1). Default 0.3.
        top_k: Maximum number of results to return. Default 10.
        source: Optional corpus filter. Searches all corpora if omitted.
    """
    results = get_tools().fuzzy_lookup(query, source=source, threshold=threshold, top_k=top_k)
    return _format(results, query, "fuzzy")


@mcp.tool()
def semantic_lookup(
    query: str,
    top_k: int = 5,
    source: str | None = None,
) -> str:
    """Search for words by meaning similarity using sentence embeddings.

    Args:
        query: A word, phrase, or description of the meaning to search for.
        top_k: Number of top results to return. Default 5.
        source: Optional corpus filter. Searches all corpora if omitted.
    """
    results = get_tools().semantic_lookup(query, top_k=top_k, source=source)
    return _format(results, query, "semantic")


def get_mcp_app() -> Starlette:
    return mcp.streamable_http_app()

"""Database package — engine, session, and query helpers."""

from .queries import (
    batch_insert,
    exact_search,
    fuzzy_search,
    get_ingested_headwords,
    similarity_search,
)
from .session import build_engine, build_session_factory, create_tables, drop_tables, get_session

__all__ = [
    "build_engine",
    "build_session_factory",
    "create_tables",
    "drop_tables",
    "get_session",
    "get_ingested_headwords",
    "batch_insert",
    "exact_search",
    "fuzzy_search",
    "similarity_search",
]

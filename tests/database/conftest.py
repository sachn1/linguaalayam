import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine

from linguaalayam.database.session import build_session_factory, create_tables
from linguaalayam.models.orm import DictionaryEntry


@pytest.fixture()
def session_factory():
    """SQLite in-memory session factory.

    Swaps Postgres-only column types (Vector, JSONB) for SQLite-compatible
    equivalents so query logic can be tested without a real database.
    """
    DictionaryEntry.__table__.c.embedding.type = sa.JSON()
    DictionaryEntry.__table__.c.data.type = sa.JSON()

    engine = create_engine("sqlite:///:memory:")
    create_tables(engine)
    factory = build_session_factory(engine)
    yield factory
    engine.dispose()

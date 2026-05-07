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
    Restores original types after the test so global ORM state is clean.
    """
    orig_embedding_type = DictionaryEntry.__table__.c.embedding.type
    orig_data_type = DictionaryEntry.__table__.c.data.type

    DictionaryEntry.__table__.c.embedding.type = sa.JSON()
    DictionaryEntry.__table__.c.data.type = sa.JSON()

    engine = create_engine("sqlite:///:memory:")
    create_tables(engine)
    factory = build_session_factory(engine)
    yield factory
    engine.dispose()

    DictionaryEntry.__table__.c.embedding.type = orig_embedding_type
    DictionaryEntry.__table__.c.data.type = orig_data_type
    # Clear memoized comparators so they rebuild from the restored type on next access.
    # Column uses a regular __dict__; ColumnProperty hides its __dict__ behind __getattr__
    # so we bypass that with object.__getattribute__.
    DictionaryEntry.__table__.c.embedding.__dict__.pop("comparator", None)
    DictionaryEntry.__table__.c.data.__dict__.pop("comparator", None)
    for attr_name in ("embedding", "data"):
        try:
            prop_dict = object.__getattribute__(
                DictionaryEntry.__mapper__.attrs[attr_name], "__dict__"
            )
            prop_dict.pop("comparator", None)
        except AttributeError:
            pass

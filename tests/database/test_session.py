"""Tests for the get_session context manager in database/session.py."""

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from linguaalayam.database.session import get_session


def test_build_session_factory_returns_sessionmaker(session_factory):
    """The session_factory fixture should be a SQLAlchemy sessionmaker."""
    assert isinstance(session_factory, sessionmaker)


def test_get_session_yields_session(session_factory):
    """get_session should yield a non-None session object."""
    with get_session(session_factory) as session:
        assert session is not None


def test_get_session_commits_on_success(session_factory):
    """A successful block should commit without raising."""
    with get_session(session_factory) as session:
        session.execute(text("SELECT 1"))


def test_get_session_rolls_back_on_exception(session_factory):
    """An exception inside the block should trigger rollback and re-raise."""
    with pytest.raises(RuntimeError):
        with get_session(session_factory) as session:
            session.execute(text("SELECT 1"))
            raise RuntimeError("simulated failure")


def test_get_session_closes_after_exception(session_factory):
    """Session should be usable again after a previous block raised."""
    try:
        with get_session(session_factory) as session:
            raise ValueError("boom")
    except ValueError:
        pass
    with get_session(session_factory) as session:
        session.execute(text("SELECT 1"))

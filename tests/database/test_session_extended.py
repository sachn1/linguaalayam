"""Tests for build_engine and drop_tables in database/session.py."""

from unittest.mock import MagicMock, patch

import sqlalchemy as sa
from omegaconf import OmegaConf
from sqlalchemy import create_engine

from linguaalayam.database.session import (
    build_engine,
    create_tables,
    drop_tables,
)
from linguaalayam.models.orm import DictionaryEntry


def _pg_cfg(**overrides):
    """Build an OmegaConf Postgres config with optional field overrides."""
    base = {
        "user": "postgres",
        "password": "secret",
        "host": "localhost",
        "port": 5432,
        "name": "testdb",
        "pool_size": 1,
        "max_overflow": 0,
    }
    base.update(overrides)
    return OmegaConf.create(base)


class TestBuildEngine:
    """build_engine URL construction and SSL handling."""

    def test_returns_engine(self):
        """build_engine should return the engine produced by create_engine."""
        cfg = _pg_cfg()
        with (
            patch("linguaalayam.database.session.create_engine") as mock_ce,
            patch("linguaalayam.database.session.event"),
        ):
            mock_engine = MagicMock()
            mock_ce.return_value = mock_engine
            engine = build_engine(cfg)
        assert engine is mock_engine

    def test_url_includes_host_and_db(self):
        """Generated URL should include the host and database name."""
        cfg = _pg_cfg()
        captured_url = []

        with (
            patch("linguaalayam.database.session.create_engine") as mock_ce,
            patch("linguaalayam.database.session.event"),
        ):
            mock_ce.side_effect = lambda url, **kw: captured_url.append(url) or MagicMock()
            build_engine(cfg)

        assert "localhost" in captured_url[0]
        assert "testdb" in captured_url[0]

    def test_sslmode_appended_when_set(self):
        """sslmode config value should appear in the generated URL."""
        cfg = _pg_cfg(sslmode="require")
        captured_url = []

        with (
            patch("linguaalayam.database.session.create_engine") as mock_ce,
            patch("linguaalayam.database.session.event"),
        ):
            mock_ce.side_effect = lambda url, **kw: captured_url.append(url) or MagicMock()
            build_engine(cfg)

        assert "sslmode=require" in captured_url[0]

    def test_no_sslmode_param_when_absent(self):
        """URL should not include sslmode when the config key is absent."""
        cfg = _pg_cfg()
        captured_url = []

        with (
            patch("linguaalayam.database.session.create_engine") as mock_ce,
            patch("linguaalayam.database.session.event"),
        ):
            mock_ce.side_effect = lambda url, **kw: captured_url.append(url) or MagicMock()
            build_engine(cfg)

        assert "sslmode" not in captured_url[0]

    def test_password_url_encoded(self):
        """Special characters in the password should be percent-encoded in the URL."""
        cfg = _pg_cfg(password="p@ss w0rd")
        captured_url = []

        with (
            patch("linguaalayam.database.session.create_engine") as mock_ce,
            patch("linguaalayam.database.session.event"),
        ):
            mock_ce.side_effect = lambda url, **kw: captured_url.append(url) or MagicMock()
            build_engine(cfg)

        assert "p@ss w0rd" not in captured_url[0]
        assert "p%40ss" in captured_url[0]


class TestDropTables:
    """drop_tables destructive DDL behaviour."""

    def test_drop_tables_removes_all(self):
        """drop_tables should remove the dictionary_entries table."""
        engine = create_engine("sqlite:///:memory:")
        orig_embedding = DictionaryEntry.__table__.c.embedding.type
        orig_data = DictionaryEntry.__table__.c.data.type
        DictionaryEntry.__table__.c.embedding.type = sa.JSON()
        DictionaryEntry.__table__.c.data.type = sa.JSON()

        create_tables(engine)
        drop_tables(engine)

        with engine.connect():
            tables = sa.inspect(engine).get_table_names()
        assert "dictionary_entries" not in tables

        DictionaryEntry.__table__.c.embedding.type = orig_embedding
        DictionaryEntry.__table__.c.data.type = orig_data
        engine.dispose()

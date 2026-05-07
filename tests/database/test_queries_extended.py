"""Extended query tests: exact_search, fuzzy_search (sqlite path), similarity_search, pg batch_insert."""

from unittest.mock import MagicMock, patch

import pytest
from pgvector.sqlalchemy import Vector

from linguaalayam.database.queries import (
    batch_insert,
    exact_search,
    fuzzy_search,
    similarity_search,
)
from linguaalayam.database.session import get_session
from linguaalayam.models.entries import EnMlEntry
from linguaalayam.models.orm import DictionaryEntry


def _entry(headword: str = "run") -> EnMlEntry:
    return EnMlEntry(headword=headword, definitions=[("v", "ഓടുക")])


def _vec() -> list[float]:
    return [0.1, 0.2, 0.3, 0.4]


# ---------------------------------------------------------------------------
# batch_insert — PostgreSQL path
# ---------------------------------------------------------------------------


class TestBatchInsertPostgres:
    def test_uses_pg_upsert(self):
        mock_session = MagicMock()
        mock_session.bind.dialect.name = "postgresql"

        with patch("linguaalayam.database.queries.pg_insert") as mock_pg:
            mock_stmt = MagicMock()
            mock_pg.return_value = mock_stmt
            mock_stmt.on_conflict_do_nothing.return_value = mock_stmt
            batch_insert(mock_session, [_entry()], [_vec()])

        mock_pg.assert_called_once()
        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# exact_search
# ---------------------------------------------------------------------------


class TestExactSearch:
    def test_returns_matching_entry(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "run")
        assert len(results) == 1
        assert results[0].headword == "run"

    def test_case_insensitive(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "RUN")
        assert len(results) == 1

    def test_no_match_returns_empty(self, session_factory):
        with get_session(session_factory) as session:
            results = exact_search(session, "xyzzy")
        assert results == []

    def test_source_filter_matches(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "run", source="olam_enml")
        assert len(results) == 1

    def test_source_filter_excludes(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "run", source="other_corpus")
        assert results == []


# ---------------------------------------------------------------------------
# fuzzy_search — SQLite ILIKE fallback
# ---------------------------------------------------------------------------


class TestFuzzySearchSQLite:
    def test_ilike_matches_substring(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run"), _entry("runner")], [_vec(), _vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run")
        headwords = [r.headword for r, _ in results]
        assert "run" in headwords

    def test_ilike_source_filter(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run", source="olam_enml")
        assert len(results) == 1

    def test_ilike_source_filter_excludes(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run", source="other")
        assert results == []

    def test_ilike_no_match(self, session_factory):
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "xyzzy")
        assert results == []

    def test_score_is_1_for_sqlite(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run")
        assert all(score == 1.0 for _, score in results)


# ---------------------------------------------------------------------------
# fuzzy_search — PostgreSQL pg_trgm path (mock session)
# ---------------------------------------------------------------------------


class TestFuzzySearchPostgres:
    def test_pg_trgm_returns_results(self):
        mock_session = MagicMock()
        mock_session.bind.dialect.name = "postgresql"
        mock_entry = MagicMock(spec=DictionaryEntry)
        mock_session.execute.return_value = [(mock_entry, 0.75)]

        results = fuzzy_search(mock_session, "run")
        assert len(results) == 1
        assert results[0][1] == pytest.approx(0.75)

    def test_pg_trgm_with_source(self):
        mock_session = MagicMock()
        mock_session.bind.dialect.name = "postgresql"
        mock_session.execute.return_value = []

        fuzzy_search(mock_session, "run", source="olam_enml")
        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# similarity_search (mock session — pgvector not available in SQLite)
# ---------------------------------------------------------------------------


class TestSimilaritySearch:
    def setup_method(self):
        # similarity_search uses the table column directly, so restoring the column
        # type and clearing its comparator cache is sufficient.
        col = DictionaryEntry.__table__.c.embedding
        col.type = Vector(768)
        col.__dict__.pop("comparator", None)

    def test_returns_scored_results(self):
        mock_entry = MagicMock(spec=DictionaryEntry)
        mock_session = MagicMock()
        mock_session.execute.return_value = [(mock_entry, 0.1)]

        results = similarity_search(mock_session, [0.1, 0.2, 0.3, 0.4])
        assert len(results) == 1
        assert results[0][1] == pytest.approx(0.9)

    def test_source_filter_applied(self):
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        similarity_search(mock_session, [0.1, 0.2, 0.3, 0.4], source="olam_enml")
        mock_session.execute.assert_called_once()

    def test_entry_type_filter_applied(self):
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        similarity_search(mock_session, [0.1, 0.2, 0.3, 0.4], entry_type="EnMlEntry")
        mock_session.execute.assert_called_once()

    def test_empty_results(self):
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        results = similarity_search(mock_session, [0.0, 0.0, 0.0, 0.0])
        assert results == []

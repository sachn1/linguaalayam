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
from linguaalayam.models.entries import OlamEntry
from linguaalayam.models.orm import DictionaryEntry


def _entry(headword: str = "run") -> OlamEntry:
    """Return a minimal OlamEntry for the given headword."""
    return OlamEntry(headword=headword, definitions=[("v", "ഓടുക")])


def _vec() -> list[float]:
    """Return a fixed 4-dimensional test vector."""
    return [0.1, 0.2, 0.3, 0.4]


# ---------------------------------------------------------------------------
# batch_insert — PostgreSQL path
# ---------------------------------------------------------------------------


class TestBatchInsertPostgres:
    """batch_insert Postgres ON CONFLICT path (mock session)."""

    def test_uses_pg_upsert(self):
        """Should call pg_insert and execute the conflict-do-nothing statement."""
        mock_session = MagicMock()
        mock_session.get_bind.return_value.dialect.name = "postgresql"

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
    """exact_search correctness and source filtering."""

    def test_returns_matching_entry(self, session_factory):
        """Should return the entry whose headword exactly matches."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "run")
        assert len(results) == 1
        assert results[0].headword == "run"

    def test_case_insensitive(self, session_factory):
        """Lookup should succeed regardless of case."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "RUN")
        assert len(results) == 1

    def test_no_match_returns_empty(self, session_factory):
        """Should return an empty list when no headword matches."""
        with get_session(session_factory) as session:
            results = exact_search(session, "xyzzy")
        assert results == []

    def test_source_filter_matches(self, session_factory):
        """Matching source filter should include the entry."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "run", source="olam_enml")
        assert len(results) == 1

    def test_source_filter_excludes(self, session_factory):
        """Non-matching source filter should return an empty list."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = exact_search(session, "run", source="other_corpus")
        assert results == []


# ---------------------------------------------------------------------------
# fuzzy_search — SQLite ILIKE fallback
# ---------------------------------------------------------------------------


class TestFuzzySearchSQLite:
    """fuzzy_search SQLite ILIKE fallback behaviour."""

    def test_ilike_matches_substring(self, session_factory):
        """ILIKE search should match entries containing the query substring."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run"), _entry("runner")], [_vec(), _vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run")
        headwords = [r.headword for r, _ in results]
        assert "run" in headwords

    def test_ilike_source_filter(self, session_factory):
        """Source filter should narrow SQLite ILIKE results."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run", source="olam_enml")
        assert len(results) == 1

    def test_ilike_source_filter_excludes(self, session_factory):
        """Non-matching source filter should exclude all results."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run", source="other")
        assert results == []

    def test_ilike_no_match(self, session_factory):
        """Should return empty list when no entry matches the query."""
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "xyzzy")
        assert results == []

    def test_score_is_1_for_sqlite(self, session_factory):
        """SQLite ILIKE fallback should assign score=1.0 to all results."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vec()])
        with get_session(session_factory) as session:
            results = fuzzy_search(session, "run")
        assert all(score == 1.0 for _, score in results)


# ---------------------------------------------------------------------------
# fuzzy_search — PostgreSQL pg_trgm path (mock session)
# ---------------------------------------------------------------------------


class TestFuzzySearchPostgres:
    """fuzzy_search Postgres pg_trgm path (mock session)."""

    def test_pg_trgm_returns_results(self):
        """Should return (entry, score) tuples from the pg_trgm query."""
        mock_session = MagicMock()
        mock_session.get_bind.return_value.dialect.name = "postgresql"
        mock_entry = MagicMock(spec=DictionaryEntry)
        mock_session.execute.return_value = [(mock_entry, 0.75)]

        results = fuzzy_search(mock_session, "run")
        assert len(results) == 1
        assert results[0][1] == pytest.approx(0.75)

    def test_pg_trgm_with_source(self):
        """Source filter should be included in the Postgres query."""
        mock_session = MagicMock()
        mock_session.get_bind.return_value.dialect.name = "postgresql"
        mock_session.execute.return_value = []

        fuzzy_search(mock_session, "run", source="olam_enml")
        mock_session.execute.assert_called_once()


# ---------------------------------------------------------------------------
# similarity_search (mock session — pgvector not available in SQLite)
# ---------------------------------------------------------------------------


class TestSimilaritySearch:
    """similarity_search cosine scoring and filter forwarding."""

    def setup_method(self):
        """Restore Vector column type so cosine_distance is available."""
        # similarity_search uses the table column directly, so restoring the column
        # type and clearing its comparator cache is sufficient.
        col = DictionaryEntry.__table__.c.embedding
        col.type = Vector(768)
        col.__dict__.pop("comparator", None)

    def test_returns_scored_results(self):
        """Should convert cosine distance to similarity score (1 - dist)."""
        mock_entry = MagicMock(spec=DictionaryEntry)
        mock_session = MagicMock()
        mock_session.execute.return_value = [(mock_entry, 0.1)]

        results = similarity_search(mock_session, [0.1, 0.2, 0.3, 0.4])
        assert len(results) == 1
        assert results[0][1] == pytest.approx(0.9)

    def test_source_filter_applied(self):
        """Source filter should be passed to the query."""
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        similarity_search(mock_session, [0.1, 0.2, 0.3, 0.4], source="olam_enml")
        mock_session.execute.assert_called_once()

    def test_entry_type_filter_applied(self):
        """entry_type filter should be included in the query."""
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        similarity_search(mock_session, [0.1, 0.2, 0.3, 0.4], entry_type="OlamEntry")
        mock_session.execute.assert_called_once()

    def test_empty_results(self):
        """Should return an empty list when no entries match."""
        mock_session = MagicMock()
        mock_session.execute.return_value = []
        results = similarity_search(mock_session, [0.0, 0.0, 0.0, 0.0])
        assert results == []

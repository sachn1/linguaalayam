"""Tests for batch_insert and get_ingested_headwords in database/queries.py."""

from linguaalayam.database.queries import batch_insert, get_ingested_headwords
from linguaalayam.database.session import get_session
from linguaalayam.models.entries import OlamEntry
from linguaalayam.models.orm import DictionaryEntry


def _entry(headword: str = "run") -> OlamEntry:
    """Return a minimal OlamEntry for the given headword."""
    return OlamEntry(headword=headword, definitions=[("v", "ഓടുക")])


def _vector() -> list[float]:
    """Return a fixed 4-dimensional test vector."""
    return [0.1, 0.2, 0.3, 0.4]


class TestBatchInsert:
    """batch_insert correctness and idempotency."""

    def test_inserts_entries(self, session_factory):
        """Two distinct entries should both appear in the table."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run"), _entry("walk")], [_vector(), _vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).count() == 2

    def test_stores_correct_headword(self, session_factory):
        """Inserted row should carry the expected headword."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("serendipity")], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).first().headword == "serendipity"

    def test_stores_correct_source(self, session_factory):
        """Inserted row should carry source='olam_enml'."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry()], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).first().source == "olam_enml"

    def test_stores_correct_entry_type(self, session_factory):
        """Inserted row should store the class name as entry_type."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry()], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).first().entry_type == "OlamEntry"

    def test_idempotent_on_duplicate(self, session_factory):
        """Inserting the same entry twice should leave exactly one row."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vector()])
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).count() == 1

    def test_empty_batch_does_not_raise(self, session_factory):
        """Calling batch_insert with empty lists should be a no-op."""
        with get_session(session_factory) as session:
            batch_insert(session, [], [])


class TestGetIngestedHeadwords:
    """get_ingested_headwords correctness and source filtering."""

    def test_returns_empty_when_no_entries(self, session_factory):
        """Should return an empty set when the table is empty."""
        with get_session(session_factory) as session:
            assert get_ingested_headwords(session, "olam_enml") == set()

    def test_returns_headwords_for_source(self, session_factory):
        """Should return all headwords for the requested source."""
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run"), _entry("walk")], [_vector(), _vector()])

        with get_session(session_factory) as session:
            assert get_ingested_headwords(session, "olam_enml") == {"run", "walk"}

    def test_filters_by_source(self, session_factory):
        """Should exclude headwords from other sources."""
        enml_entry = _entry("run")
        datuk_entry = OlamEntry(headword="ഓടുക", definitions=[("v", "test")], source="datuk")

        with get_session(session_factory) as session:
            batch_insert(session, [enml_entry, datuk_entry], [_vector(), _vector()])

        with get_session(session_factory) as session:
            result = get_ingested_headwords(session, "olam_enml")
        assert "run" in result
        assert "ഓടുക" not in result

    def test_returns_set(self, session_factory):
        """Return type should always be a set."""
        with get_session(session_factory) as session:
            assert isinstance(get_ingested_headwords(session, "olam_enml"), set)

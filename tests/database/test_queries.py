from linguaalayam.database.queries import batch_insert, get_ingested_headwords
from linguaalayam.database.session import get_session
from linguaalayam.models.entries import EnMlEntry
from linguaalayam.models.orm import DictionaryEntry


def _entry(headword: str = "run") -> EnMlEntry:
    return EnMlEntry(headword=headword, definitions=[("v", "ഓടുക")])


def _vector() -> list[float]:
    return [0.1, 0.2, 0.3, 0.4]


class TestBatchInsert:
    def test_inserts_entries(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run"), _entry("walk")], [_vector(), _vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).count() == 2

    def test_stores_correct_headword(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("serendipity")], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).first().headword == "serendipity"

    def test_stores_correct_source(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry()], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).first().source == "olam_enml"

    def test_stores_correct_entry_type(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry()], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).first().entry_type == "EnMlEntry"

    def test_idempotent_on_duplicate(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vector()])
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run")], [_vector()])

        with get_session(session_factory) as session:
            assert session.query(DictionaryEntry).count() == 1

    def test_empty_batch_does_not_raise(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [], [])


class TestGetIngestedHeadwords:
    def test_returns_empty_when_no_entries(self, session_factory):
        with get_session(session_factory) as session:
            assert get_ingested_headwords(session, "olam_enml") == set()

    def test_returns_headwords_for_source(self, session_factory):
        with get_session(session_factory) as session:
            batch_insert(session, [_entry("run"), _entry("walk")], [_vector(), _vector()])

        with get_session(session_factory) as session:
            assert get_ingested_headwords(session, "olam_enml") == {"run", "walk"}

    def test_filters_by_source(self, session_factory):
        enml_entry = _entry("run")
        datuk_entry = EnMlEntry(headword="ഓടുക", definitions=[("v", "test")], source="datuk")

        with get_session(session_factory) as session:
            batch_insert(session, [enml_entry, datuk_entry], [_vector(), _vector()])

        with get_session(session_factory) as session:
            result = get_ingested_headwords(session, "olam_enml")
        assert "run" in result
        assert "ഓടുക" not in result

    def test_returns_set(self, session_factory):
        with get_session(session_factory) as session:
            assert isinstance(get_ingested_headwords(session, "olam_enml"), set)

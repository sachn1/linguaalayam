"""Tests for the DictionaryEntry ORM model."""

from linguaalayam.models import DictionaryEntry


def test_repr_contains_headword():
    """repr should include the entry's headword."""
    entry = DictionaryEntry(headword="run", source="olam_enml")
    assert "run" in repr(entry)


def test_repr_contains_source():
    """repr should include the entry's source name."""
    entry = DictionaryEntry(headword="run", source="olam_enml")
    assert "olam_enml" in repr(entry)


def test_tablename():
    """ORM should map to the 'dictionary_entries' table."""
    assert DictionaryEntry.__tablename__ == "dictionary_entries"

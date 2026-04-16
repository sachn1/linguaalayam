from linguaalayam.models import DictionaryEntry


def test_repr_contains_headword():
    entry = DictionaryEntry(headword="run", source="olam_enml")
    assert "run" in repr(entry)


def test_repr_contains_source():
    entry = DictionaryEntry(headword="run", source="olam_enml")
    assert "olam_enml" in repr(entry)


def test_tablename():
    assert DictionaryEntry.__tablename__ == "dictionary_entries"

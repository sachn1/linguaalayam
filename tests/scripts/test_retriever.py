from unittest.mock import MagicMock, patch

import pytest

from linguaalayam.models.orm import DictionaryEntry
from linguaalayam.rag.retriever import Retriever


@pytest.fixture()
def db_entry():
    return DictionaryEntry(
        headword="run",
        source="olam_enml",
        entry_type="EnMlEntry",
        embed_text="word: run\n  [v] ഓടുക",
        data={"headword": "run", "definitions": [["v", "ഓടുക"]], "source": "olam_enml"},
    )


@pytest.fixture()
def mock_embedder():
    embedder = MagicMock()
    embedder.encode_query.return_value = [0.1, 0.2, 0.3, 0.4]
    return embedder


@pytest.fixture()
def retriever(mock_embedder, db_entry):
    """Retriever with similarity_search fully mocked — no DB or pgvector needed."""
    factory = MagicMock()
    with patch("linguaalayam.rag.retriever.similarity_search", return_value=[(db_entry, 0.9)]):
        yield Retriever(mock_embedder, factory)


def test_retrieve_calls_encode_query(retriever, mock_embedder):
    with patch("linguaalayam.rag.retriever.similarity_search", return_value=[]):
        retriever.retrieve("what does run mean")
    mock_embedder.encode_query.assert_called_once_with("what does run mean")


def test_retrieve_result_has_expected_keys(retriever):
    entry = DictionaryEntry(
        headword="run", source="olam_enml", entry_type="EnMlEntry",
        embed_text="word: run", data={},
    )
    with patch("linguaalayam.rag.retriever.similarity_search", return_value=[(entry, 0.9)]):
        results = retriever.retrieve("run")
    assert {"headword", "source", "entry_type", "embed_text", "data", "score"} <= results[0].keys()


def test_retrieve_result_headword(retriever, db_entry):
    with patch("linguaalayam.rag.retriever.similarity_search", return_value=[(db_entry, 0.9)]):
        results = retriever.retrieve("run")
    assert results[0]["headword"] == "run"


def test_retrieve_returns_empty_when_no_results(mock_embedder):
    factory = MagicMock()
    r = Retriever(mock_embedder, factory)
    with patch("linguaalayam.rag.retriever.similarity_search", return_value=[]):
        results = r.retrieve("xyzzy")
    assert results == []


def test_to_context_maps_all_fields():
    entry = DictionaryEntry(
        headword="run", source="olam_enml", entry_type="EnMlEntry",
        embed_text="word: run", data={"headword": "run"},
    )
    result = Retriever._to_context(entry, score=0.85)
    assert result == {
        "headword": "run",
        "source": "olam_enml",
        "entry_type": "EnMlEntry",
        "embed_text": "word: run",
        "data": {"headword": "run"},
        "score": 0.85,
    }

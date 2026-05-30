"""Tests for rag/reranker.py — CrossEncoderReranker."""

from unittest.mock import MagicMock, patch

from linguaalayam.rag.reranker import CrossEncoderReranker


def _candidate(headword: str, score: float = 1.0) -> dict:
    """Build a minimal candidate dict for the given headword."""
    return {
        "headword": headword,
        "source": "olam_enml",
        "embed_text": f"word: {headword}",
        "match_type": "exact",
        "score": score,
    }


def _make_reranker(scores: list[float]) -> CrossEncoderReranker:
    """Build a CrossEncoderReranker with a mocked CrossEncoder returning scores."""
    with patch("linguaalayam.rag.reranker.CrossEncoder") as mock_ce:
        mock_model = MagicMock()
        mock_ce.return_value = mock_model
        mock_model.predict.return_value = scores
        reranker = CrossEncoderReranker()
        reranker._model = mock_model
    return reranker


class TestCrossEncoderReranker:
    """CrossEncoderReranker sorting and truncation."""

    def test_rerank_sorts_by_score(self):
        """Candidates should be ordered from highest to lowest cross-encoder score."""
        reranker = _make_reranker([0.1, 0.9])
        candidates = [_candidate("walk"), _candidate("run")]
        reranker._model.predict.return_value = [0.1, 0.9]
        result = reranker.rerank("run", candidates)
        assert result[0]["headword"] == "run"
        assert result[1]["headword"] == "walk"

    def test_rerank_empty_returns_empty(self):
        """Empty candidate list should return immediately without scoring."""
        reranker = _make_reranker([])
        result = reranker.rerank("run", [])
        assert result == []

    def test_top_n_limits_results(self):
        """top_n should truncate the sorted result list."""
        reranker = _make_reranker([0.9, 0.8, 0.7])
        candidates = [_candidate("a"), _candidate("b"), _candidate("c")]
        reranker._model.predict.return_value = [0.9, 0.8, 0.7]
        result = reranker.rerank("query", candidates, top_n=2)
        assert len(result) == 2

    def test_top_n_none_returns_all(self):
        """top_n=None should return all candidates sorted."""
        reranker = _make_reranker([0.9, 0.8])
        candidates = [_candidate("a"), _candidate("b")]
        reranker._model.predict.return_value = [0.9, 0.8]
        result = reranker.rerank("query", candidates, top_n=None)
        assert len(result) == 2

    def test_pairs_constructed_correctly(self):
        """predict should be called with (query, embed_text) pairs."""
        reranker = _make_reranker([0.5])
        candidates = [_candidate("run")]
        reranker._model.predict.return_value = [0.5]
        reranker.rerank("run", candidates)
        call_args = reranker._model.predict.call_args[0][0]
        assert call_args == [("run", "word: run")]

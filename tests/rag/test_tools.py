"""Tests for rag/tools.py — DictionaryTools and merge_candidates."""

from unittest.mock import MagicMock, patch

from linguaalayam.rag.tools import DictionaryTools, merge_candidates


def _candidate(headword: str, source: str = "olam_enml", match_type: str = "exact") -> dict:
    """Build a minimal candidate dict for the given headword."""
    return {
        "headword": headword,
        "source": source,
        "entry_type": "EnMlEntry",
        "embed_text": f"word: {headword}",
        "data": {},
        "match_type": match_type,
        "score": 1.0,
    }


class TestMergeCandidates:
    """merge_candidates deduplication and priority ordering."""

    def test_deduplicates_by_source_and_headword(self):
        """The same (source, headword) from two lists should produce one entry."""
        a = [_candidate("run", match_type="exact")]
        b = [_candidate("run", match_type="fuzzy")]
        merged = merge_candidates([a, b])
        assert len(merged) == 1
        assert merged[0]["match_type"] == "exact"  # first list wins

    def test_preserves_distinct_entries(self):
        """Different headwords should all appear in the merged list."""
        a = [_candidate("run")]
        b = [_candidate("walk")]
        merged = merge_candidates([a, b])
        assert len(merged) == 2

    def test_empty_lists(self):
        """Two empty lists should produce an empty merged list."""
        assert merge_candidates([[], []]) == []

    def test_single_list(self):
        """A single-element input should pass through unchanged."""
        a = [_candidate("run"), _candidate("walk")]
        merged = merge_candidates([a])
        assert len(merged) == 2

    def test_priority_order(self):
        """Earlier list entries should appear before later-list entries in output."""
        a = [_candidate("run", match_type="exact")]
        b = [_candidate("run", match_type="semantic")]
        c = [_candidate("fly", match_type="semantic")]
        merged = merge_candidates([a, b, c])
        headwords = [r["headword"] for r in merged]
        assert headwords.index("run") < headwords.index("fly")


class TestDictionaryTools:
    """DictionaryTools exact, fuzzy, and semantic lookup wrappers."""

    def _make_tools(self):
        """Build a DictionaryTools with mock session factory and embedder."""
        session_factory = MagicMock()
        embedding_service = MagicMock()
        embedding_service.encode_query.return_value = [0.1, 0.2, 0.3, 0.4]
        return (
            DictionaryTools(session_factory, embedding_service),
            session_factory,
            embedding_service,
        )

    def _mock_session_ctx(self):
        """Build a mock async-compatible session context manager."""
        ctx = MagicMock()
        ctx.__enter__ = MagicMock(return_value=MagicMock())
        ctx.__exit__ = MagicMock(return_value=False)
        return ctx

    def test_exact_lookup_returns_results(self):
        """exact_lookup should serialise ORM rows into result dicts."""
        tools, sf, _ = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "run"
        mock_entry.source = "olam_enml"
        mock_entry.entry_type = "EnMlEntry"
        mock_entry.embed_text = "word: run"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.exact_search", return_value=[mock_entry]),
        ):
            results = tools.exact_lookup("run")

        assert len(results) == 1
        assert results[0]["headword"] == "run"
        assert results[0]["match_type"] == "exact"
        assert results[0]["score"] == 1.0

    def test_exact_lookup_empty(self):
        """exact_lookup should return an empty list on miss."""
        tools, _, _ = self._make_tools()
        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.exact_search", return_value=[]),
        ):
            results = tools.exact_lookup("xyzzy")
        assert results == []

    def test_fuzzy_lookup_returns_results(self):
        """fuzzy_lookup should return results with match_type='fuzzy'."""
        tools, _, _ = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "run"
        mock_entry.source = "olam_enml"
        mock_entry.entry_type = "EnMlEntry"
        mock_entry.embed_text = "word: run"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.fuzzy_search", return_value=[(mock_entry, 0.8)]),
        ):
            results = tools.fuzzy_lookup("runing")

        assert len(results) == 1
        assert results[0]["match_type"] == "fuzzy"
        assert results[0]["score"] == 0.8

    def test_semantic_lookup_encodes_query(self):
        """semantic_lookup should embed the query before calling similarity_search."""
        tools, _, embed_svc = self._make_tools()
        mock_entry = MagicMock()
        mock_entry.headword = "run"
        mock_entry.source = "olam_enml"
        mock_entry.entry_type = "EnMlEntry"
        mock_entry.embed_text = "word: run"
        mock_entry.data = {}

        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.similarity_search", return_value=[(mock_entry, 0.9)]),
        ):
            results = tools.semantic_lookup("to move quickly on foot")

        embed_svc.encode_query.assert_called_once_with("to move quickly on foot")
        assert len(results) == 1
        assert results[0]["match_type"] == "semantic"

    def test_exact_lookup_passes_source(self):
        """Source filter should be forwarded to exact_search."""
        tools, _, _ = self._make_tools()
        with (
            patch("linguaalayam.rag.tools.get_session", return_value=self._mock_session_ctx()),
            patch("linguaalayam.rag.tools.exact_search", return_value=[]) as mock_es,
        ):
            tools.exact_lookup("run", source="olam_enml")
        mock_es.assert_called_once()
        _, kwargs = mock_es.call_args
        assert kwargs.get("source") == "olam_enml" or mock_es.call_args[0][2] == "olam_enml"

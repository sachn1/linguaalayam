"""Tests for rag/pipeline.py — pipeline nodes and _format_entries."""

from unittest.mock import MagicMock

from langchain_core.messages import AIMessage
from omegaconf import OmegaConf

from linguaalayam.rag.pipeline import RAGState, _format_entries, build_pipeline


def _candidate(headword: str, match_type: str = "exact", score: float = 1.0) -> dict:
    return {
        "headword": headword,
        "source": "olam_enml",
        "entry_type": "EnMlEntry",
        "embed_text": f"word: {headword}\n  [v] ഓടുക",
        "data": {},
        "match_type": match_type,
        "score": score,
    }


class TestFormatEntries:
    def test_includes_headword(self):
        text = _format_entries([_candidate("run")])
        assert "run" in text

    def test_includes_embed_text(self):
        text = _format_entries([_candidate("run")])
        assert "ഓടുക" in text

    def test_numbers_entries(self):
        text = _format_entries([_candidate("run"), _candidate("walk")])
        assert "[1]" in text
        assert "[2]" in text

    def test_empty_list(self):
        assert _format_entries([]) == ""

    def test_no_score_handled(self):
        c = _candidate("run")
        c["score"] = None
        text = _format_entries([c])
        assert "run" in text


class TestBuildPipeline:
    def _make_tools(self, headword: str = "run"):
        tools = MagicMock()
        tools.exact_lookup.return_value = [_candidate(headword)]
        tools.fuzzy_lookup.return_value = []
        tools.semantic_lookup.return_value = []
        return tools

    def _make_llm(self, answer: str = "Test answer"):
        llm = MagicMock()
        # understand_query structured output
        from linguaalayam.rag.query_understanding import QueryUnderstanding

        structured = MagicMock()
        structured.invoke.return_value = QueryUnderstanding(headword="run", intent="define")
        llm.with_structured_output.return_value = structured
        # synthesis response
        llm.invoke.return_value = AIMessage(content=answer)
        return llm

    def _initial_state(self, query: str = "run") -> RAGState:
        return {"query": query, "headword": None, "intent": None, "candidates": [], "answer": ""}

    def test_pipeline_returns_answer(self):
        tools = self._make_tools()
        llm = self._make_llm("Malayalam: ഓടുക")
        cfg = OmegaConf.create({"top_k": 5, "rerank": False})
        pipeline = build_pipeline(tools, llm, cfg)
        result = pipeline.invoke(self._initial_state("run"))
        assert "answer" in result
        assert result["answer"]

    def test_pipeline_sets_candidates(self):
        tools = self._make_tools("run")
        llm = self._make_llm()
        cfg = OmegaConf.create({"top_k": 5, "rerank": False})
        pipeline = build_pipeline(tools, llm, cfg)
        result = pipeline.invoke(self._initial_state("run"))
        assert result["candidates"]

    def test_synthesize_returns_no_results_message(self):
        tools = MagicMock()
        tools.exact_lookup.return_value = []
        tools.fuzzy_lookup.return_value = []
        tools.semantic_lookup.return_value = []

        llm = self._make_llm()
        cfg = OmegaConf.create({"top_k": 5, "rerank": False})
        pipeline = build_pipeline(tools, llm, cfg)
        result = pipeline.invoke(self._initial_state("xyzzy"))
        assert "No dictionary entries" in result["answer"]

    def test_rerank_node_skips_without_reranker(self):
        tools = self._make_tools()
        llm = self._make_llm()
        cfg = OmegaConf.create({"top_k": 5, "rerank": True})
        # reranker=None → rerank node is a no-op
        pipeline = build_pipeline(tools, llm, cfg, reranker=None)
        result = pipeline.invoke(self._initial_state("run"))
        assert "answer" in result

    def test_rerank_node_uses_reranker(self):
        tools = self._make_tools()
        llm = self._make_llm()
        mock_reranker = MagicMock()
        mock_reranker.rerank.return_value = [_candidate("run")]
        cfg = OmegaConf.create({"top_k": 5, "rerank": True})
        pipeline = build_pipeline(tools, llm, cfg, reranker=mock_reranker)
        pipeline.invoke(self._initial_state("run"))
        mock_reranker.rerank.assert_called_once()

    def test_source_passed_to_tools(self):
        tools = self._make_tools()
        llm = self._make_llm()
        cfg = OmegaConf.create({"top_k": 5, "rerank": False, "source": "olam_enml"})
        pipeline = build_pipeline(tools, llm, cfg)
        pipeline.invoke(self._initial_state("run"))
        _, kwargs = tools.exact_lookup.call_args
        assert (
            kwargs.get("source") == "olam_enml" or tools.exact_lookup.call_args[0][1] == "olam_enml"
        )

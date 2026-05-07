"""Tests for eval/runner.py."""

import json
from unittest.mock import MagicMock

import pytest
from omegaconf import OmegaConf

from linguaalayam.eval import run_eval
from linguaalayam.eval.dataset import EvalQuery
from linguaalayam.eval.metrics import QueryResult
from linguaalayam.eval.runner import _eval_query, _find_rank


class TestFindRank:
    def test_first_position(self):
        candidates = [{"headword": "run"}, {"headword": "walk"}]
        assert _find_rank("run", candidates) == 1

    def test_second_position(self):
        candidates = [{"headword": "walk"}, {"headword": "run"}]
        assert _find_rank("run", candidates) == 2

    def test_miss_returns_none(self):
        candidates = [{"headword": "walk"}]
        assert _find_rank("run", candidates) is None

    def test_case_insensitive(self):
        candidates = [{"headword": "Run"}]
        assert _find_rank("run", candidates) == 1

    def test_empty_candidates(self):
        assert _find_rank("run", []) is None


class TestEvalQuery:
    def _make_tools(self, exact=None, fuzzy=None, semantic=None):
        tools = MagicMock()
        tools.exact_lookup.return_value = exact or []
        tools.fuzzy_lookup.return_value = fuzzy or []
        tools.semantic_lookup.return_value = semantic or []
        return tools

    def test_hit_at_1_when_exact_match(self):
        tools = self._make_tools(
            exact=[{"headword": "run", "match_type": "exact", "source": "olam_enml"}]
        )
        q = EvalQuery(query="run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.hit_at_1
        assert result.hit_at_k
        assert result.tool_attribution == "exact"

    def test_miss_when_no_results(self):
        tools = self._make_tools()
        q = EvalQuery(query="xyzzy", expected_headword="xyzzy", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert not result.hit_at_1
        assert not result.hit_at_k
        assert result.tool_attribution is None
        assert result.reciprocal_rank == 0.0

    def test_latency_measured(self):
        tools = self._make_tools()
        q = EvalQuery(query="run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.latency_ms >= 0

    def test_extracted_headword_from_pattern(self):
        tools = self._make_tools()
        q = EvalQuery(query="define run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.extracted_headword == "run"

    def test_second_rank_hit(self):
        tools = self._make_tools(
            exact=[{"headword": "walk", "match_type": "exact", "source": "olam_enml"}],
            semantic=[{"headword": "run", "match_type": "semantic", "source": "olam_enml"}],
        )
        q = EvalQuery(query="run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.hit_at_k
        assert result.reciprocal_rank == pytest.approx(0.5)


class TestRunEval:
    def test_returns_results_list(self, tmp_path):
        q = {"query": "run", "expected_headword": "run"}
        p = tmp_path / "q.jsonl"
        p.write_text(json.dumps(q), encoding="utf-8")

        tools = MagicMock()
        tools.exact_lookup.return_value = []
        tools.fuzzy_lookup.return_value = []
        tools.semantic_lookup.return_value = []

        cfg = OmegaConf.create(
            {"dataset": str(p), "top_k": 5, "fuzzy_threshold": 0.3, "fuzzy_limit": 10}
        )
        results = run_eval(tools, cfg)
        assert isinstance(results, list)
        assert len(results) == 1
        assert isinstance(results[0], QueryResult)

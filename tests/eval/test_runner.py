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
    """_find_rank rank detection and case handling."""

    def test_first_position(self):
        """Should return 1 when expected headword is first in the list."""
        candidates = [{"headword": "run"}, {"headword": "walk"}]
        assert _find_rank("run", candidates) == 1

    def test_second_position(self):
        """Should return 2 when expected headword is second."""
        candidates = [{"headword": "walk"}, {"headword": "run"}]
        assert _find_rank("run", candidates) == 2

    def test_miss_returns_none(self):
        """Should return None when expected headword is not present."""
        candidates = [{"headword": "walk"}]
        assert _find_rank("run", candidates) is None

    def test_case_insensitive(self):
        """Rank detection should be case-insensitive."""
        candidates = [{"headword": "Run"}]
        assert _find_rank("run", candidates) == 1

    def test_empty_candidates(self):
        """Should return None for an empty candidate list."""
        assert _find_rank("run", []) is None


class TestEvalQuery:
    """_eval_query single-query evaluation correctness."""

    def _make_tools(self, exact=None, fuzzy=None, semantic=None):
        """Build a mock DictionaryTools with preconfigured return values."""
        tools = MagicMock()
        tools.exact_lookup.return_value = exact or []
        tools.fuzzy_lookup.return_value = fuzzy or []
        tools.semantic_lookup.return_value = semantic or []
        return tools

    def test_hit_at_1_when_exact_match(self):
        """Exact match as first result should yield hit_at_1=True."""
        tools = self._make_tools(
            exact=[{"headword": "run", "match_type": "exact", "source": "olam_enml"}]
        )
        q = EvalQuery(query="run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.hit_at_1
        assert result.hit_at_k
        assert result.tool_attribution == "exact"

    def test_miss_when_no_results(self):
        """Empty candidate list should yield hit_at_1=False, tool_attribution=None."""
        tools = self._make_tools()
        q = EvalQuery(query="xyzzy", expected_headword="xyzzy", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert not result.hit_at_1
        assert not result.hit_at_k
        assert result.tool_attribution is None
        assert result.reciprocal_rank == 0.0

    def test_latency_measured(self):
        """latency_ms should be non-negative."""
        tools = self._make_tools()
        q = EvalQuery(query="run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.latency_ms >= 0

    def test_extracted_headword_from_pattern(self):
        """Regex query understanding should extract 'run' from 'define run'."""
        tools = self._make_tools()
        q = EvalQuery(query="define run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.extracted_headword == "run"

    def test_second_rank_hit(self):
        """Expected headword at rank 2 should give reciprocal_rank=0.5."""
        tools = self._make_tools(
            exact=[{"headword": "walk", "match_type": "exact", "source": "olam_enml"}],
            semantic=[{"headword": "run", "match_type": "semantic", "source": "olam_enml"}],
        )
        q = EvalQuery(query="run", expected_headword="run", intent="define")
        result = _eval_query(q, tools, top_k=5, fuzzy_threshold=0.3, fuzzy_limit=10)
        assert result.hit_at_k
        assert result.reciprocal_rank == pytest.approx(0.5)


class TestRunEval:
    """run_eval end-to-end over a dataset file."""

    def test_returns_results_list(self, tmp_path):
        """run_eval should return one QueryResult per dataset query."""
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

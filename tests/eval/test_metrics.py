"""Tests for eval/metrics.py — pure metric functions."""

from linguaalayam.eval import intent_breakdown, mrr, hit_rate, hit_rate_at_1, tool_breakdown
from linguaalayam.eval.metrics import QueryResult


def _result(
    hit1: bool = True,
    hitk: bool = True,
    rr: float = 1.0,
    tool: str | None = "exact",
    intent: str = "define",
) -> QueryResult:
    """Build a QueryResult with the given metric fields and sensible defaults."""
    return QueryResult(
        query="q",
        expected_headword="run",
        intent=intent,
        source=None,
        extracted_headword="run",
        retrieved_headwords=["run"],
        hit_at_1=hit1,
        hit_at_k=hitk,
        reciprocal_rank=rr,
        tool_attribution=tool,
        latency_ms=5.0,
    )


class TestHitRateAt1:
    """hit_rate_at_1 edge cases and normal operation."""

    def test_all_hit(self):
        """Should return 1.0 when every result is a hit at rank 1."""
        results = [_result(hit1=True), _result(hit1=True)]
        assert hit_rate_at_1(results) == 1.0

    def test_none_hit(self):
        """Should return 0.0 when no result is a hit at rank 1."""
        results = [_result(hit1=False), _result(hit1=False)]
        assert hit_rate_at_1(results) == 0.0

    def test_half_hit(self):
        """Should return 0.5 when half the results are hits."""
        results = [_result(hit1=True), _result(hit1=False)]
        assert hit_rate_at_1(results) == 0.5

    def test_empty_returns_zero(self):
        """Should return 0.0 for an empty results list."""
        assert hit_rate_at_1([]) == 0.0


class TestHitRate:
    """hit_rate (hit@k) edge cases."""

    def test_all_hit(self):
        """Should return 1.0 when all results hit within top-k."""
        results = [_result(hitk=True), _result(hitk=True)]
        assert hit_rate(results) == 1.0

    def test_none_hit(self):
        """Should return 0.0 when no results hit within top-k."""
        results = [_result(hitk=False), _result(hitk=False)]
        assert hit_rate(results) == 0.0

    def test_empty_returns_zero(self):
        """Should return 0.0 for an empty results list."""
        assert hit_rate([]) == 0.0


class TestMrr:
    """mrr (Mean Reciprocal Rank) correctness."""

    def test_all_first_rank(self):
        """Should return 1.0 when all queries are found at rank 1."""
        results = [_result(rr=1.0), _result(rr=1.0)]
        assert mrr(results) == 1.0

    def test_mixed_ranks(self):
        """Should average reciprocal ranks correctly."""
        results = [_result(rr=1.0), _result(rr=0.5)]
        assert mrr(results) == 0.75

    def test_all_miss(self):
        """Should return 0.0 when no query is found."""
        results = [_result(rr=0.0), _result(rr=0.0)]
        assert mrr(results) == 0.0

    def test_empty_returns_zero(self):
        """Should return 0.0 for an empty results list."""
        assert mrr([]) == 0.0


class TestToolBreakdown:
    """tool_breakdown hit counting by tool."""

    def test_counts_by_tool(self):
        """Should count one hit per tool and one miss."""
        results = [
            _result(tool="exact"),
            _result(tool="fuzzy"),
            _result(tool="semantic"),
            _result(tool=None),
        ]
        counts = tool_breakdown(results)
        assert counts["exact"] == 1
        assert counts["fuzzy"] == 1
        assert counts["semantic"] == 1
        assert counts["miss"] == 1

    def test_all_misses(self):
        """All None attributions should be counted under 'miss'."""
        results = [_result(tool=None), _result(tool=None)]
        counts = tool_breakdown(results)
        assert counts["miss"] == 2
        assert counts["exact"] == 0


class TestIntentBreakdown:
    """intent_breakdown grouping and metric computation."""

    def test_groups_by_intent(self):
        """Results should be grouped and counted by intent label."""
        results = [
            _result(intent="define"),
            _result(intent="define"),
            _result(intent="translate", hit1=False, hitk=False, rr=0.0, tool=None),
        ]
        breakdown = intent_breakdown(results)
        assert "define" in breakdown
        assert "translate" in breakdown
        assert breakdown["define"]["count"] == 2
        assert breakdown["translate"]["count"] == 1

    def test_hit_rates_computed(self):
        """Per-intent breakdown should include hit@1, hit@k, and mrr."""
        results = [_result(hit1=True, hitk=True, rr=1.0, intent="define")]
        breakdown = intent_breakdown(results)
        assert breakdown["define"]["hit@1"] == 1.0
        assert breakdown["define"]["hit@k"] == 1.0
        assert breakdown["define"]["mrr"] == 1.0

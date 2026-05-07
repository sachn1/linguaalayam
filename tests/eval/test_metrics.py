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
    def test_all_hit(self):
        results = [_result(hit1=True), _result(hit1=True)]
        assert hit_rate_at_1(results) == 1.0

    def test_none_hit(self):
        results = [_result(hit1=False), _result(hit1=False)]
        assert hit_rate_at_1(results) == 0.0

    def test_half_hit(self):
        results = [_result(hit1=True), _result(hit1=False)]
        assert hit_rate_at_1(results) == 0.5

    def test_empty_returns_zero(self):
        assert hit_rate_at_1([]) == 0.0


class TestHitRate:
    def test_all_hit(self):
        results = [_result(hitk=True), _result(hitk=True)]
        assert hit_rate(results) == 1.0

    def test_none_hit(self):
        results = [_result(hitk=False), _result(hitk=False)]
        assert hit_rate(results) == 0.0

    def test_empty_returns_zero(self):
        assert hit_rate([]) == 0.0


class TestMrr:
    def test_all_first_rank(self):
        results = [_result(rr=1.0), _result(rr=1.0)]
        assert mrr(results) == 1.0

    def test_mixed_ranks(self):
        results = [_result(rr=1.0), _result(rr=0.5)]
        assert mrr(results) == 0.75

    def test_all_miss(self):
        results = [_result(rr=0.0), _result(rr=0.0)]
        assert mrr(results) == 0.0

    def test_empty_returns_zero(self):
        assert mrr([]) == 0.0


class TestToolBreakdown:
    def test_counts_by_tool(self):
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
        results = [_result(tool=None), _result(tool=None)]
        counts = tool_breakdown(results)
        assert counts["miss"] == 2
        assert counts["exact"] == 0


class TestIntentBreakdown:
    def test_groups_by_intent(self):
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
        results = [_result(hit1=True, hitk=True, rr=1.0, intent="define")]
        breakdown = intent_breakdown(results)
        assert breakdown["define"]["hit@1"] == 1.0
        assert breakdown["define"]["hit@k"] == 1.0
        assert breakdown["define"]["mrr"] == 1.0

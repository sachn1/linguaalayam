"""Tests for _print_summary and _write_results in eval/main.py."""

import json

from omegaconf import OmegaConf

from linguaalayam.eval.main import _print_summary, _write_results
from linguaalayam.eval.metrics import QueryResult


def _make_result(
    query: str = "run",
    expected: str = "run",
    hit1: bool = True,
    hitk: bool = True,
    rr: float = 1.0,
    tool: str | None = "exact",
    intent: str = "define",
    latency: float = 5.0,
) -> QueryResult:
    """Build a QueryResult with configurable metric fields."""
    return QueryResult(
        query=query,
        expected_headword=expected,
        intent=intent,
        source=None,
        extracted_headword=expected,
        retrieved_headwords=[expected] if hitk else [],
        hit_at_1=hit1,
        hit_at_k=hitk,
        reciprocal_rank=rr,
        tool_attribution=tool,
        latency_ms=latency,
    )


_CFG = OmegaConf.create(
    {"eval": {"dataset": "data/eval/q.jsonl", "top_k": 5}, "embedding": {"model": "mpnet"}}
)


class TestPrintSummary:
    """_print_summary output content checks."""

    def test_empty_results(self, capsys):
        """Should print 'No results' message for an empty list."""
        _print_summary([], _CFG)
        out = capsys.readouterr().out
        assert "No results" in out

    def test_shows_hit_rates(self, capsys):
        """Summary output should include Hit@1 and MRR sections."""
        results = [_make_result()]
        _print_summary(results, _CFG)
        out = capsys.readouterr().out
        assert "Hit@1" in out
        assert "MRR" in out

    def test_shows_misses_section(self, capsys):
        """Results with no hits should produce a Misses section."""
        results = [_make_result(hit1=False, hitk=False, rr=0.0, tool=None)]
        _print_summary(results, _CFG)
        out = capsys.readouterr().out
        assert "Misses" in out

    def test_truncates_long_miss_list(self, capsys):
        """More than 10 misses should be truncated with an ellipsis."""
        results = [_make_result(hit1=False, hitk=False, rr=0.0, tool=None) for _ in range(15)]
        _print_summary(results, _CFG)
        out = capsys.readouterr().out
        assert "more" in out


class TestWriteResults:
    """_write_results file creation and JSONL output correctness."""

    def test_creates_file(self, tmp_path):
        """Output file should exist after writing."""
        results = [_make_result()]
        out_path = tmp_path / "subdir" / "out.jsonl"
        _write_results(results, out_path)
        assert out_path.exists()

    def test_creates_parent_directory(self, tmp_path):
        """Missing parent directories should be created automatically."""
        results = [_make_result()]
        out_path = tmp_path / "nested" / "deep" / "out.jsonl"
        _write_results(results, out_path)
        assert out_path.exists()

    def test_valid_jsonl(self, tmp_path):
        """Each line of the output file should be valid JSON with query/headword."""
        results = [_make_result(), _make_result(query="walk", expected="walk")]
        out_path = tmp_path / "out.jsonl"
        _write_results(results, out_path)
        lines = [json.loads(line) for line in out_path.read_text().splitlines() if line]
        assert len(lines) == 2
        assert lines[0]["query"] == "run"
        assert lines[1]["query"] == "walk"

    def test_all_fields_written(self, tmp_path):
        """Output JSON should include all required QueryResult fields."""
        results = [_make_result()]
        out_path = tmp_path / "out.jsonl"
        _write_results(results, out_path)
        data = json.loads(out_path.read_text().splitlines()[0])
        required = {
            "query",
            "expected_headword",
            "intent",
            "extracted_headword",
            "retrieved_headwords",
            "hit_at_1",
            "hit_at_k",
            "reciprocal_rank",
            "tool_attribution",
            "latency_ms",
        }
        assert required <= data.keys()

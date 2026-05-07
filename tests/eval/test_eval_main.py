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
    def test_empty_results(self, capsys):
        _print_summary([], _CFG)
        out = capsys.readouterr().out
        assert "No results" in out

    def test_shows_hit_rates(self, capsys):
        results = [_make_result()]
        _print_summary(results, _CFG)
        out = capsys.readouterr().out
        assert "Hit@1" in out
        assert "MRR" in out

    def test_shows_misses_section(self, capsys):
        results = [_make_result(hit1=False, hitk=False, rr=0.0, tool=None)]
        _print_summary(results, _CFG)
        out = capsys.readouterr().out
        assert "Misses" in out

    def test_truncates_long_miss_list(self, capsys):
        results = [_make_result(hit1=False, hitk=False, rr=0.0, tool=None) for _ in range(15)]
        _print_summary(results, _CFG)
        out = capsys.readouterr().out
        assert "more" in out


class TestWriteResults:
    def test_creates_file(self, tmp_path):
        results = [_make_result()]
        out_path = tmp_path / "subdir" / "out.jsonl"
        _write_results(results, out_path)
        assert out_path.exists()

    def test_creates_parent_directory(self, tmp_path):
        results = [_make_result()]
        out_path = tmp_path / "nested" / "deep" / "out.jsonl"
        _write_results(results, out_path)
        assert out_path.exists()

    def test_valid_jsonl(self, tmp_path):
        results = [_make_result(), _make_result(query="walk", expected="walk")]
        out_path = tmp_path / "out.jsonl"
        _write_results(results, out_path)
        lines = [json.loads(line) for line in out_path.read_text().splitlines() if line]
        assert len(lines) == 2
        assert lines[0]["query"] == "run"
        assert lines[1]["query"] == "walk"

    def test_all_fields_written(self, tmp_path):
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

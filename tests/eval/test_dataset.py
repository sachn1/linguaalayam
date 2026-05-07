"""Tests for eval/dataset.py."""

import json
from pathlib import Path

import pytest

from linguaalayam.eval import EvalQuery, load_dataset


def _write_jsonl(path: Path, lines: list[dict]) -> Path:
    path.write_text("\n".join(json.dumps(d) for d in lines), encoding="utf-8")
    return path


def test_load_valid_dataset(tmp_path):
    p = _write_jsonl(
        tmp_path / "q.jsonl",
        [{"query": "define run", "expected_headword": "run", "intent": "define"}],
    )
    queries = load_dataset(p)
    assert len(queries) == 1
    assert queries[0].query == "define run"
    assert queries[0].expected_headword == "run"
    assert queries[0].intent == "define"


def test_optional_fields_default(tmp_path):
    p = _write_jsonl(
        tmp_path / "q.jsonl",
        [{"query": "run", "expected_headword": "run"}],
    )
    queries = load_dataset(p)
    assert queries[0].intent == "define"
    assert queries[0].source is None


def test_optional_source_field(tmp_path):
    p = _write_jsonl(
        tmp_path / "q.jsonl",
        [{"query": "run", "expected_headword": "run", "source": "olam_enml"}],
    )
    queries = load_dataset(p)
    assert queries[0].source == "olam_enml"


def test_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError, match="not found"):
        load_dataset(tmp_path / "missing.jsonl")


def test_raises_on_invalid_json(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text("not json\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Invalid JSON"):
        load_dataset(p)


def test_skips_blank_lines(tmp_path):
    p = tmp_path / "q.jsonl"
    p.write_text(
        '\n{"query": "run", "expected_headword": "run"}\n\n',
        encoding="utf-8",
    )
    queries = load_dataset(p)
    assert len(queries) == 1


def test_multiple_queries(tmp_path):
    rows = [
        {"query": "run", "expected_headword": "run"},
        {"query": "walk", "expected_headword": "walk"},
    ]
    p = _write_jsonl(tmp_path / "q.jsonl", rows)
    queries = load_dataset(p)
    assert len(queries) == 2


def test_returns_eval_query_instances(tmp_path):
    p = _write_jsonl(tmp_path / "q.jsonl", [{"query": "run", "expected_headword": "run"}])
    queries = load_dataset(p)
    assert all(isinstance(q, EvalQuery) for q in queries)

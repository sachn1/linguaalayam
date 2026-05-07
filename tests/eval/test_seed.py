"""Tests for eval/seed.py — _build_entries function."""

from unittest.mock import patch

from linguaalayam.eval.dataset import EvalQuery
from linguaalayam.eval.seed import _build_entries


def _queries(*headwords: str) -> list[EvalQuery]:
    return [
        EvalQuery(query=f"define {hw}", expected_headword=hw, intent="define") for hw in headwords
    ]


def test_build_entries_known_headword():
    with patch("linguaalayam.eval.seed.load_dataset", return_value=_queries("run")):
        entries = _build_entries()
    assert len(entries) == 1
    assert entries[0].headword == "run"


def test_build_entries_multiple_headwords():
    with patch(
        "linguaalayam.eval.seed.load_dataset", return_value=_queries("run", "walk", "peace")
    ):
        entries = _build_entries()
    headwords = {e.headword for e in entries}
    assert {"run", "walk", "peace"} == headwords


def test_build_entries_stub_for_unknown():
    with patch("linguaalayam.eval.seed.load_dataset", return_value=_queries("xyzzy_unknown")):
        entries = _build_entries()
    assert len(entries) == 1
    assert entries[0].headword == "xyzzy_unknown"
    # stub definition contains the headword
    assert any("xyzzy_unknown" in defn for _, defn in entries[0].definitions)


def test_build_entries_deduplicates_headwords():
    # same headword queried with different queries → one entry
    queries = [
        EvalQuery(query="define run", expected_headword="run", intent="define"),
        EvalQuery(query="run meaning", expected_headword="run", intent="define"),
    ]
    with patch("linguaalayam.eval.seed.load_dataset", return_value=queries):
        entries = _build_entries()
    headwords = [e.headword for e in entries]
    assert headwords.count("run") == 1

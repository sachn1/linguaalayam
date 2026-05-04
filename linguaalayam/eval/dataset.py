"""Eval dataset loader — reads JSONL files of (query, expected_headword) pairs."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalQuery:
    query: str
    expected_headword: str
    intent: str
    source: str | None = None


def load_dataset(path: str | Path) -> list[EvalQuery]:
    """Load an eval dataset from a JSONL file.

    Each line must have: query, expected_headword.
    Optional fields: intent (default "define"), source (default null).
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(
            f"Eval dataset not found: {p}\n"
            "Generate one or use the seed set at data/eval/queries.jsonl"
        )

    queries = []
    for i, line in enumerate(p.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON at line {i} of {p}: {e}") from e

        queries.append(EvalQuery(
            query=data["query"],
            expected_headword=data["expected_headword"],
            intent=data.get("intent", "define"),
            source=data.get("source"),
        ))

    return queries

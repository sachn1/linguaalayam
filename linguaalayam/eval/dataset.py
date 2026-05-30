"""Eval dataset loader — reads JSONL files of (query, expected_headword) pairs."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class EvalQuery:
    """A single labelled evaluation query.

    Attributes
    ----------
    query : str
        The natural-language query string as the user would type it.
    expected_headword : str
        The dictionary headword that a correct retrieval should surface.
    intent : str
        Query intent label (e.g. ``"define"``, ``"translate"``).
    source : str or None
        Optional corpus filter to restrict retrieval to a single source.
    """

    query: str
    expected_headword: str
    intent: str
    source: str | None = None


def load_dataset(path: str | Path) -> list[EvalQuery]:
    """Load an evaluation dataset from a JSONL file.

    Each line must contain a JSON object with at minimum ``query`` and
    ``expected_headword`` keys. ``intent`` defaults to ``"define"`` and
    ``source`` defaults to ``None`` when absent.

    Parameters
    ----------
    path : str or Path
        Path to the JSONL file.

    Returns
    -------
    list[EvalQuery]
        Parsed evaluation queries in file order.

    Raises
    ------
    FileNotFoundError
        If the file does not exist at ``path``.
    ValueError
        If any line contains malformed JSON.
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

        queries.append(
            EvalQuery(
                query=data["query"],
                expected_headword=data["expected_headword"],
                intent=data.get("intent", "define"),
                source=data.get("source"),
            )
        )

    return queries

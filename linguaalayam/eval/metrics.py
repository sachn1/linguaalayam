"""Retrieval evaluation metrics — hit rate, MRR, and breakdown slices."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryResult:
    """Evaluation result for a single query.

    Attributes
    ----------
    query : str
        The original natural-language query.
    expected_headword : str
        The correct dictionary headword for this query.
    intent : str
        Query intent label (e.g. ``"define"``, ``"translate"``).
    source : str or None
        Corpus filter that was applied, or ``None`` for all corpora.
    extracted_headword : str
        Headword extracted by query understanding before retrieval.
    retrieved_headwords : list[str]
        Ordered list of headwords in the top-k result set.
    hit_at_1 : bool
        ``True`` if the expected headword is the top-ranked result.
    hit_at_k : bool
        ``True`` if the expected headword appears anywhere in the top-k results.
    reciprocal_rank : float
        ``1 / rank`` if found, ``0.0`` otherwise; used to compute MRR.
    tool_attribution : str or None
        Which retrieval tool first surfaced the correct result
        (``"exact"``, ``"fuzzy"``, or ``"semantic"``), or ``None`` on a miss.
    latency_ms : float
        End-to-end retrieval latency in milliseconds.
    """

    query: str
    expected_headword: str
    intent: str
    source: str | None
    extracted_headword: str
    retrieved_headwords: list[str]
    hit_at_1: bool
    hit_at_k: bool
    reciprocal_rank: float
    tool_attribution: str | None  # "exact" | "fuzzy" | "semantic" | None (miss)
    latency_ms: float


def hit_rate_at_1(results: list[QueryResult]) -> float:
    """Compute the fraction of queries where the top result is correct.

    Parameters
    ----------
    results : list[QueryResult]
        Evaluation results to aggregate.

    Returns
    -------
    float
        Hit@1 rate in ``[0, 1]``; ``0.0`` for an empty list.
    """
    if not results:
        return 0.0
    return sum(1 for r in results if r.hit_at_1) / len(results)


def hit_rate(results: list[QueryResult]) -> float:
    """Compute the fraction of queries where the correct result appears in top-k.

    Parameters
    ----------
    results : list[QueryResult]
        Evaluation results to aggregate.

    Returns
    -------
    float
        Hit@k rate in ``[0, 1]``; ``0.0`` for an empty list.
    """
    if not results:
        return 0.0
    return sum(1 for r in results if r.hit_at_k) / len(results)


def mrr(results: list[QueryResult]) -> float:
    """Compute Mean Reciprocal Rank across all queries.

    Parameters
    ----------
    results : list[QueryResult]
        Evaluation results to aggregate.

    Returns
    -------
    float
        MRR in ``[0, 1]``; ``0.0`` for an empty list.
    """
    if not results:
        return 0.0
    return sum(r.reciprocal_rank for r in results) / len(results)


def tool_breakdown(results: list[QueryResult]) -> dict[str, int]:
    """Count how many hits each retrieval tool is responsible for, plus misses.

    Parameters
    ----------
    results : list[QueryResult]
        Evaluation results to aggregate.

    Returns
    -------
    dict[str, int]
        Counts keyed by ``"exact"``, ``"fuzzy"``, ``"semantic"``, and ``"miss"``.
    """
    counts: dict[str, int] = {"exact": 0, "fuzzy": 0, "semantic": 0, "miss": 0}
    for r in results:
        key = r.tool_attribution if r.tool_attribution else "miss"
        counts[key] = counts.get(key, 0) + 1
    return counts


def intent_breakdown(results: list[QueryResult]) -> dict[str, dict]:
    """Compute per-intent hit@1, hit@k, MRR, and count.

    Parameters
    ----------
    results : list[QueryResult]
        Evaluation results to aggregate.

    Returns
    -------
    dict[str, dict]
        Mapping from intent label to a dict with keys
        ``"count"``, ``"hit@1"``, ``"hit@k"``, and ``"mrr"``.
    """
    by_intent: dict[str, list[QueryResult]] = {}
    for r in results:
        by_intent.setdefault(r.intent, []).append(r)

    return {
        intent: {
            "count": len(group),
            "hit@1": round(hit_rate_at_1(group), 3),
            "hit@k": round(hit_rate(group), 3),
            "mrr": round(mrr(group), 3),
        }
        for intent, group in sorted(by_intent.items())
    }

"""Retrieval evaluation metrics — hit rate, MRR, and breakdown slices."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class QueryResult:
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
    if not results:
        return 0.0
    return sum(1 for r in results if r.hit_at_1) / len(results)


def hit_rate(results: list[QueryResult], k: int | None = None) -> float:
    """Hit rate at k (or at whatever k was used during eval if k is None)."""
    if not results:
        return 0.0
    return sum(1 for r in results if r.hit_at_k) / len(results)


def mrr(results: list[QueryResult]) -> float:
    if not results:
        return 0.0
    return sum(r.reciprocal_rank for r in results) / len(results)


def tool_breakdown(results: list[QueryResult]) -> dict[str, int]:
    """Count how many hits each tool is responsible for, plus misses."""
    counts: dict[str, int] = {"exact": 0, "fuzzy": 0, "semantic": 0, "miss": 0}
    for r in results:
        key = r.tool_attribution if r.tool_attribution else "miss"
        counts[key] = counts.get(key, 0) + 1
    return counts


def intent_breakdown(results: list[QueryResult]) -> dict[str, dict]:
    """Per-intent hit@1, hit@k, MRR, and count."""
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

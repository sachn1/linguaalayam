"""Eval runner — runs all three retrieval tools against the eval dataset and scores results.

LLM-free by design: uses regex-only query understanding so results are deterministic
and no API key is needed. Measures retrieval quality only; answer quality is separate.
"""

import time

from omegaconf import DictConfig

from linguaalayam.eval.dataset import EvalQuery, load_dataset
from linguaalayam.eval.metrics import QueryResult
from linguaalayam.rag.query_understanding import understand_query
from linguaalayam.rag.tools import DictionaryTools, merge_candidates


def _find_rank(expected: str, candidates: list[dict]) -> int | None:
    for i, c in enumerate(candidates, 1):
        if c["headword"].lower() == expected.lower():
            return i
    return None


def _eval_query(
    q: EvalQuery,
    tools: DictionaryTools,
    top_k: int,
    fuzzy_threshold: float,
    fuzzy_limit: int,
) -> QueryResult:
    t0 = time.perf_counter()

    # Regex-only understanding — no LLM, keeps eval deterministic and free
    qu = understand_query(q.query, llm=None)
    headword = qu.headword

    exact = tools.exact_lookup(headword, source=q.source)
    fuzzy = tools.fuzzy_lookup(
        headword, source=q.source, threshold=fuzzy_threshold, top_k=fuzzy_limit
    )
    semantic = tools.semantic_lookup(q.query, top_k=top_k, source=q.source)

    merged = merge_candidates([exact, fuzzy, semantic])
    top = merged[:top_k]

    latency_ms = (time.perf_counter() - t0) * 1000
    rank = _find_rank(q.expected_headword, top)

    tool_attribution = None
    if rank is not None:
        matched = next(c for c in top if c["headword"].lower() == q.expected_headword.lower())
        tool_attribution = matched["match_type"]

    return QueryResult(
        query=q.query,
        expected_headword=q.expected_headword,
        intent=q.intent,
        source=q.source,
        extracted_headword=headword,
        retrieved_headwords=[c["headword"] for c in top],
        hit_at_1=rank == 1,
        hit_at_k=rank is not None,
        reciprocal_rank=1.0 / rank if rank is not None else 0.0,
        tool_attribution=tool_attribution,
        latency_ms=latency_ms,
    )


def run_eval(tools: DictionaryTools, cfg: DictConfig) -> list[QueryResult]:
    dataset = load_dataset(cfg.dataset)
    top_k: int = cfg.get("top_k", 5)
    fuzzy_threshold: float = cfg.get("fuzzy_threshold", 0.3)
    fuzzy_limit: int = cfg.get("fuzzy_limit", 10)

    return [
        _eval_query(q, tools, top_k=top_k, fuzzy_threshold=fuzzy_threshold, fuzzy_limit=fuzzy_limit)
        for q in dataset
    ]

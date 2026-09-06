"""Eval runner — runs all three retrieval tools against the eval dataset and scores results.

LLM-free by design: uses regex-only query understanding so results are deterministic
and no API key is needed. Measures retrieval quality only; answer quality is separate.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TYPE_CHECKING

from omegaconf import DictConfig

from linguaalayam.eval.dataset import EvalQuery, load_dataset
from linguaalayam.eval.metrics import QueryResult
from linguaalayam.rag.query_understanding import understand_query
from linguaalayam.rag.tools import DictionaryTools, merge_candidates

if TYPE_CHECKING:
    from linguaalayam.rag.reranker import CrossEncoderReranker

SemanticFn = Callable[[str, str | None, int], list[dict]]


def _find_rank(expected: str, candidates: list[dict]) -> int | None:
    """Return 1-based rank of expected headword in candidates, or None."""
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
    semantic_fn: SemanticFn | None = None,
    reranker: "CrossEncoderReranker | None" = None,
    rerank_candidate_k: int = 25,
) -> QueryResult:
    """Run all three retrieval tools against a single query and score the result.

    Parameters
    ----------
    semantic_fn : callable or None
        If provided, replaces ``tools.semantic_lookup`` for this query.
        Signature: ``(query_text, source, top_k) -> list[dict]``.
        Used to test candidate embedding models without re-ingesting the DB.
    reranker : CrossEncoderReranker or None, optional
        When provided, re-scores the merged exact+fuzzy+semantic candidates
        before truncating to ``top_k`` — mirrors the production rerank step
        in ``rag/pipeline.py`` so eval can measure its effect on Hit@k/MRR.
    rerank_candidate_k : int, optional
        Pool size to fetch (instead of ``top_k``) before reranking, so the
        cross-encoder can promote a correct-but-lower-ranked candidate
        rather than only reshuffling a pool already truncated to ``top_k``.
        Ignored unless ``reranker`` is provided.
    """
    t0 = time.perf_counter()

    # Regex-only understanding — no LLM, keeps eval deterministic and free
    qu = understand_query(q.query, llm=None)
    headword = qu.headword

    fetch_k = max(top_k, rerank_candidate_k) if reranker is not None else top_k

    exact = tools.exact_lookup(headword, source=q.source)
    fuzzy = tools.fuzzy_lookup(
        headword, source=q.source, threshold=fuzzy_threshold, top_k=max(fuzzy_limit, fetch_k)
    )

    if semantic_fn is not None:
        semantic = semantic_fn(q.query, q.source, fetch_k)
    else:
        semantic = tools.semantic_lookup(q.query, top_k=fetch_k, source=q.source)

    merged = merge_candidates([exact, fuzzy, semantic])
    if reranker is not None and merged:
        merged = reranker.rerank(q.query, merged, top_n=top_k)
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


def run_eval(
    tools: DictionaryTools,
    cfg: DictConfig,
    queries: list[EvalQuery] | None = None,
    semantic_fn: SemanticFn | None = None,
    reranker: "CrossEncoderReranker | None" = None,
) -> list[QueryResult]:
    """Run retrieval evaluation against a labeled query dataset.

    Parameters
    ----------
    tools : DictionaryTools
        Retrieval tools backed by a live database session.
    cfg : DictConfig
        Eval configuration; recognised keys: ``dataset``, ``top_k``,
        ``fuzzy_threshold``, ``fuzzy_limit``.
    queries : list[EvalQuery] or None
        Pre-loaded queries. If ``None``, loaded from ``cfg.dataset``.
    semantic_fn : callable or None
        If provided, replaces DB-backed semantic search. Use to test
        candidate embedding models without re-ingesting the corpus.
        Signature: ``(query_text, source, top_k) -> list[dict]``.
    reranker : CrossEncoderReranker or None, optional
        When provided, applied to every query's merged candidates before
        scoring — see :func:`_eval_query`.

    Returns
    -------
    list[QueryResult]
        One result per query in the dataset.
    """
    dataset = queries if queries is not None else load_dataset(cfg.dataset)
    top_k: int = cfg.get("top_k", 5)
    fuzzy_threshold: float = cfg.get("fuzzy_threshold", 0.3)
    fuzzy_limit: int = cfg.get("fuzzy_limit", 10)
    rerank_candidate_k: int = cfg.get("rerank_candidate_k", 25)

    return [
        _eval_query(
            q,
            tools,
            top_k=top_k,
            fuzzy_threshold=fuzzy_threshold,
            fuzzy_limit=fuzzy_limit,
            semantic_fn=semantic_fn,
            reranker=reranker,
            rerank_candidate_k=rerank_candidate_k,
        )
        for q in dataset
    ]

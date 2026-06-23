"""Evaluation entrypoint.

Two modes, one command:

1. **Single-model** (default): tests the ingested production model against the DB.
   Uses exact + fuzzy + semantic (pgvector) — the real production path.

2. **Multi-model compare**: when ``eval.compare`` is configured and corpus sample
   exists, iterates over all enabled embedding models. Exact + fuzzy still hit the
   real DB; semantic is replaced with in-memory cosine similarity per candidate model.
   Each (model, dataset) pair is logged as an MLflow run in the ``retrieval_pipeline``
   experiment, so you can compare models without re-ingesting.

Runs over all datasets defined in ``eval.datasets``. Prints a separate summary per
dataset.

CLI examples::

    poetry run eval-retrieval
    poetry run eval-retrieval eval.top_k=10
    poetry run eval-retrieval eval.output=results/v2.1.jsonl
    poetry run eval-retrieval eval.compare.mlflow=false
"""

from __future__ import annotations

import csv
import io
import json
import logging
import time
from pathlib import Path

import hydra
import mlflow
import numpy as np
import torch
from omegaconf import DictConfig
from sentence_transformers import SentenceTransformer

from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.env import load_env
from linguaalayam.eval.dataset import load_dataset
from linguaalayam.eval.metrics import QueryResult, intent_breakdown, mrr, tool_breakdown
from linguaalayam.eval.runner import SemanticFn, run_eval
from linguaalayam.rag.tools import DictionaryTools

load_env()

log = logging.getLogger(__name__)

_RAG_EXPERIMENT = "retrieval_pipeline"


# ---------------------------------------------------------------------------
# In-memory semantic function factory
# ---------------------------------------------------------------------------


def _load_corpus_sample(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _encode_corpus(
    model: SentenceTransformer,
    entries: list[dict],
    passage_prefix: str,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    texts = [f"{passage_prefix}{e['embed_text']}" for e in entries]
    t0 = time.perf_counter()
    matrix: np.ndarray = model.encode(
        texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    elapsed = (time.perf_counter() - t0) * 1000
    print(f"  Corpus encoded in {elapsed:.0f}ms", flush=True)
    source_masks = {
        src: np.array([e["source"] == src for e in entries])
        for src in {e["source"] for e in entries}
    }
    return matrix, source_masks


def _make_semantic_fn(
    model: SentenceTransformer,
    corpus_matrix: np.ndarray,
    source_masks: dict[str, np.ndarray],
    entries: list[dict],
    query_prefix: str,
) -> SemanticFn:
    """Return a semantic_fn compatible with runner._eval_query."""

    def semantic_fn(query_text: str, source: str | None, top_k: int) -> list[dict]:
        if source and source in source_masks:
            mask = source_masks[source]
            mat = corpus_matrix[mask]
            ents = [e for e, m in zip(entries, mask) if m]
        else:
            mat = corpus_matrix
            ents = entries

        if not ents:
            return []

        q_vec: np.ndarray = model.encode(
            f"{query_prefix}{query_text}",
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        sims = mat @ q_vec
        top_idx = np.argsort(-sims)[:top_k]
        return [
            {
                "headword": ents[i]["headword"],
                "source": ents[i]["source"],
                "entry_type": None,
                "embed_text": ents[i]["embed_text"],
                "data": None,
                "match_type": "semantic",
                "score": float(sims[i]),
            }
            for i in top_idx
        ]

    return semantic_fn


# ---------------------------------------------------------------------------
# Printing + MLflow logging
# ---------------------------------------------------------------------------


def _print_summary(
    results: list[QueryResult],
    cfg: DictConfig,
    label: str = "",
    model_label: str = "",
) -> None:
    n = len(results)
    if n == 0:
        print("No results — is the dataset empty?")
        return

    hits_1 = sum(r.hit_at_1 for r in results)
    hits_k = sum(r.hit_at_k for r in results)
    mrr_val = mrr(results)
    tools_attr = tool_breakdown(results)
    intents = intent_breakdown(results)
    avg_ms = sum(r.latency_ms for r in results) / n
    top_k = cfg.eval.get("top_k", 5)

    parts = [p for p in ("RAG Evaluation", label, model_label) if p]
    heading = " — ".join(parts)

    print()
    print("=" * 65)
    print(heading)
    print("=" * 65)
    print(f"Queries : {n}    Top-k : {top_k}")
    print()
    print(f"Hit@1   : {hits_1 / n:.3f}  ({hits_1}/{n})")
    print(f"Hit@{top_k}   : {hits_k / n:.3f}  ({hits_k}/{n})")
    print(f"MRR     : {mrr_val:.3f}")
    print(f"Latency : {avg_ms:.1f} ms avg")
    print()

    print("Tool attribution:")
    hit_count = hits_k or 1
    for tool in ("exact", "fuzzy", "semantic"):
        c = tools_attr.get(tool, 0)
        print(f"  {tool:<10}: {c:3}  ({c / hit_count * 100:.1f}% of hits)")
    print(f"  {'miss':<10}: {tools_attr.get('miss', 0):3}")
    print()

    print("By intent:")
    for intent, m in intents.items():
        print(
            f"  {intent:<22}  hit@1={m['hit@1']:.2f}  "
            f"hit@k={m['hit@k']:.2f}  mrr={m['mrr']:.2f}  n={m['count']}"
        )

    misses = [r for r in results if not r.hit_at_k]
    if misses:
        print()
        print(f"Misses ({len(misses)}):")
        for r in misses[:10]:
            got = ", ".join(r.retrieved_headwords[:3]) or "—"
            print(f"  {r.query!r:42} expected={r.expected_headword!r}  got=[{got}]")
        if len(misses) > 10:
            print(f"  ... and {len(misses) - 10} more")

    print("=" * 65)


def _log_retrieval_to_mlflow(
    results: list[QueryResult],
    model_key: str,
    model_hf_id: str,
    dataset_label: str,
    cfg: DictConfig,
) -> None:
    top_k = cfg.eval.get("top_k", 5)
    n = len(results)
    hits_k = sum(r.hit_at_k for r in results)
    mrr_val = mrr(results)
    intents = intent_breakdown(results)

    run_name = f"{model_key}_{dataset_label}"
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tags({"model": model_key, "dataset": dataset_label})
        mlflow.log_params(
            {
                "model_hf_id": model_hf_id,
                "model_key": model_key,
                "dataset_label": dataset_label,
                "top_k": top_k,
                "n_queries": n,
                "embedding_model": cfg.embedding.model,
            }
        )
        mlflow.log_metrics(
            {
                "hit_at_1": round(sum(r.hit_at_1 for r in results) / n, 4) if n else 0.0,
                f"hit_at_{top_k}": round(hits_k / n, 4) if n else 0.0,
                "mrr": round(mrr_val, 4),
                "latency_ms": round(sum(r.latency_ms for r in results) / n, 2) if n else 0.0,
                "miss_count": n - hits_k,
            }
        )
        tools_attr = tool_breakdown(results)
        for tool in ("exact", "fuzzy", "semantic"):
            mlflow.log_metric(f"hits_by_{tool}", tools_attr.get(tool, 0))
        for intent, m in intents.items():
            mlflow.log_metrics(
                {
                    f"{intent}_hit_at_1": m["hit@1"],
                    f"{intent}_hit_at_k": m["hit@k"],
                    f"{intent}_mrr": m["mrr"],
                }
            )

        # Per-query detail as a CSV artifact — view in MLflow UI > Artifacts tab
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(
            [
                "query",
                "expected_headword",
                "intent",
                "hit_at_1",
                "hit_at_k",
                "reciprocal_rank",
                "tool_attribution",
                "retrieved_top3",
                "latency_ms",
            ]
        )
        for r in results:
            writer.writerow(
                [
                    r.query,
                    r.expected_headword,
                    r.intent,
                    int(r.hit_at_1),
                    int(r.hit_at_k),
                    round(r.reciprocal_rank, 4),
                    r.tool_attribution,
                    "|".join(r.retrieved_headwords[:3]),
                    round(r.latency_ms, 2),
                ]
            )
        mlflow.log_text(buf.getvalue(), "per_query_results.csv")


def _write_results(results: list[QueryResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in results:
            f.write(
                json.dumps(
                    {
                        "query": r.query,
                        "expected_headword": r.expected_headword,
                        "intent": r.intent,
                        "extracted_headword": r.extracted_headword,
                        "retrieved_headwords": r.retrieved_headwords,
                        "hit_at_1": r.hit_at_1,
                        "hit_at_k": r.hit_at_k,
                        "reciprocal_rank": r.reciprocal_rank,
                        "tool_attribution": r.tool_attribution,
                        "latency_ms": round(r.latency_ms, 2),
                    }
                )
                + "\n"
            )
    log.info("Results written to %s", path)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:  # pragma: no cover
    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)

    log.info("Loading production embedding model: %s", cfg.embedding.model)
    service = EmbeddingService(cfg.embedding)
    tools = DictionaryTools(session_factory, service)

    compare_cfg = cfg.eval.get("compare")
    corpus_path = Path(compare_cfg.corpus_sample) if compare_cfg else None
    multi_model_mode = (
        compare_cfg is not None
        and corpus_path is not None
        and corpus_path.exists()
        and any(m.get("enabled", True) for m in compare_cfg.models)
    )

    datasets_cfg = cfg.eval.get("datasets")
    if not datasets_cfg:
        datasets_cfg = [{"path": cfg.eval.dataset, "label": "default"}]

    loaded_datasets = [
        {"label": ds.label, "queries": load_dataset(ds.path), "path": ds.path}
        for ds in datasets_cfg
    ]

    use_mlflow = compare_cfg.get("mlflow", True) if compare_cfg else False

    if multi_model_mode:
        # Multi-model mode: exact+fuzzy from DB, semantic in-memory per candidate
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            print(f"GPU: {torch.cuda.get_device_name(0)}")

        log.info("Loading corpus sample from %s", corpus_path)
        entries = _load_corpus_sample(corpus_path)
        log.info("%d corpus entries loaded", len(entries))

        active_models = [m for m in compare_cfg.models if m.get("enabled", True)]
        print(
            f"Multi-model RAG eval — {len(active_models)} models × {len(loaded_datasets)} datasets"
        )

        if use_mlflow:
            mlflow.set_experiment(_RAG_EXPERIMENT)
            print(f"MLflow experiment: '{_RAG_EXPERIMENT}'  (mlflow ui --port 5001)")

        all_results: list[QueryResult] = []
        for model_cfg in active_models:
            print(f"\n{'─' * 60}")
            print(f"Model: {model_cfg.get('label', model_cfg.hf_id)}")
            trust = model_cfg.get("trust_remote_code", False)
            model = SentenceTransformer(model_cfg.hf_id, device=device, trust_remote_code=trust)

            corpus_matrix, source_masks = _encode_corpus(
                model, entries, model_cfg.get("passage_prefix", "")
            )
            semantic_fn = _make_semantic_fn(
                model,
                corpus_matrix,
                source_masks,
                entries,
                model_cfg.get("query_prefix", ""),
            )

            for ds in loaded_datasets:
                results = run_eval(tools, cfg.eval, queries=ds["queries"], semantic_fn=semantic_fn)
                _print_summary(
                    results,
                    cfg,
                    label=ds["label"],
                    model_label=model_cfg.get("label", model_cfg.key),
                )
                all_results.extend(results)

                if use_mlflow:
                    _log_retrieval_to_mlflow(
                        results,
                        model_key=model_cfg.key,
                        model_hf_id=model_cfg.hf_id,
                        dataset_label=ds["label"],
                        cfg=cfg,
                    )
                    print(f"  → logged to MLflow: {model_cfg.key}/{ds['label']}")

            del model
            if device == "cuda":
                torch.cuda.empty_cache()

        if cfg.eval.output and all_results:
            _write_results(all_results, Path(cfg.eval.output))

    else:
        # Single-model mode: production model, full pgvector semantic
        if not multi_model_mode and corpus_path and not corpus_path.exists():
            log.warning(
                "Corpus sample not found at %s — running single-model mode. "
                "Run `poetry run eval-prepare-corpus` to enable multi-model comparison.",
                corpus_path,
            )

        all_results = []
        for ds in loaded_datasets:
            log.info("Running eval on %s (%s)", ds["path"], ds["label"])
            results = run_eval(tools, cfg.eval, queries=ds["queries"])
            _print_summary(results, cfg, label=ds["label"])
            all_results.extend(results)

        if cfg.eval.output and all_results:
            _write_results(all_results, Path(cfg.eval.output))

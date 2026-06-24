"""Offline embedding model comparison with MLflow tracking.

Candidate models are defined in config/eval/default.yaml under the
``compare.models`` list. Set ``enabled: false`` on any model to skip it.
Each model's corpus is encoded ONCE then scored against every dataset —
encoding is the expensive step.

No re-ingestion needed. Loads a pre-prepared corpus sample (run
``poetry run prepare-eval-sample`` once to generate it).

Usage:
    poetry run model-compare
    poetry run model-compare eval.compare.top_k=10
    poetry run model-compare eval.compare.mlflow=false      # stdout only
    mlflow ui --port 5001                                   # browse results
"""

from __future__ import annotations

import csv
import io
import json
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import hydra
import mlflow
import numpy as np
import torch
from omegaconf import DictConfig
from sentence_transformers import SentenceTransformer

from linguaalayam.eval.dataset import EvalQuery, load_dataset

_EXPERIMENT = "embedding_model_comparison"


@dataclass
class DatasetResult:
    """Metrics for one model evaluated against one dataset."""

    model_key: str
    model_label: str
    model_dim: int
    dataset_label: str
    hit_at_1: float
    hit_at_k: float
    mrr: float
    latency_ms: float
    n_queries: int
    per_intent: dict[str, dict] = field(default_factory=dict)
    misses: list[dict] = field(default_factory=list)
    per_query_rows: list[dict] = field(default_factory=list)


def _load_corpus(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def _encode_corpus(
    model: SentenceTransformer,
    entries: list[dict],
    passage_prefix: str,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Encode all corpus entries and build per-source index masks."""
    corpus_texts = [f"{passage_prefix}{e['embed_text']}" for e in entries]
    print(f"  Encoding {len(corpus_texts)} corpus entries...", flush=True)
    t0 = time.perf_counter()
    matrix: np.ndarray = model.encode(
        corpus_texts,
        batch_size=64,
        show_progress_bar=True,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    print(f"  Corpus encoded in {(time.perf_counter() - t0) * 1000:.0f}ms", flush=True)
    source_masks = {
        src: np.array([e["source"] == src for e in entries])
        for src in {e["source"] for e in entries}
    }
    return matrix, source_masks


def _score_queries(
    queries: list[EvalQuery],
    model: SentenceTransformer,
    corpus_matrix: np.ndarray,
    source_masks: dict[str, np.ndarray],
    entries: list[dict],
    query_prefix: str,
    top_k: int,
    semantic_intents: set[str] | None = None,
) -> tuple[dict, list[dict], float, list[dict]]:
    """Score a query list against pre-encoded corpus.

    semantic_intents: if provided, only queries with intent in this set are scored.
    Returns (per_intent_raw, misses, total_latency_ms, per_query_rows).
    """
    per_intent_raw: dict[str, dict] = defaultdict(lambda: {"n": 0, "h1": 0, "hk": 0, "rr": 0.0})
    misses: list[dict] = []
    per_query_rows: list[dict] = []
    total_latency = 0.0

    for q in queries:
        if semantic_intents is not None and q.intent not in semantic_intents:
            continue
        if q.source and q.source in source_masks:
            mask = source_masks[q.source]
            mat = corpus_matrix[mask]
            ents = [e for e, m in zip(entries, mask) if m]
        else:
            mat = corpus_matrix
            ents = entries

        bucket = per_intent_raw[q.intent]
        bucket["n"] += 1

        if not ents:
            misses.append(
                {
                    "query": q.query,
                    "expected": q.expected_headword,
                    "reason": f"no entries source={q.source}",
                }
            )
            per_query_rows.append(
                {
                    "query": q.query,
                    "expected_headword": q.expected_headword,
                    "intent": q.intent,
                    "hit_at_1": 0,
                    "hit_at_k": 0,
                    "reciprocal_rank": 0.0,
                    "retrieved_top3": "",
                    "latency_ms": 0.0,
                }
            )
            continue

        tq = time.perf_counter()
        q_vec: np.ndarray = model.encode(
            f"{query_prefix}{q.query}",
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        sims = mat @ q_vec
        top_idx = np.argsort(-sims)[:top_k]
        latency = (time.perf_counter() - tq) * 1000
        total_latency += latency

        retrieved = [ents[i]["headword"].lower() for i in top_idx]
        expected = q.expected_headword.lower()
        rank = next((r for r, hw in enumerate(retrieved, 1) if hw == expected), None)

        hit_1 = int(rank == 1)
        hit_k = int(rank is not None)
        rr = (1.0 / rank) if rank else 0.0

        if rank == 1:
            bucket["h1"] += 1
        if rank is not None:
            bucket["hk"] += 1
            bucket["rr"] += rr
        else:
            misses.append(
                {
                    "query": q.query,
                    "expected": q.expected_headword,
                    "intent": q.intent,
                    "got": [ents[i]["headword"] for i in top_idx[:3]],
                }
            )

        per_query_rows.append(
            {
                "query": q.query,
                "expected_headword": q.expected_headword,
                "intent": q.intent,
                "hit_at_1": hit_1,
                "hit_at_k": hit_k,
                "reciprocal_rank": round(rr, 4),
                "retrieved_top3": "|".join(ents[i]["headword"] for i in top_idx[:3]),
                "latency_ms": round(latency, 2),
            }
        )

    return per_intent_raw, misses, total_latency, per_query_rows


def _build_dataset_result(
    model_cfg: DictConfig,
    dataset_label: str,
    queries: list[EvalQuery],
    per_intent_raw: dict,
    misses: list[dict],
    total_latency: float,
    per_query_rows: list[dict] | None = None,
) -> DatasetResult:
    n = len(queries)
    hits_1 = sum(v["h1"] for v in per_intent_raw.values())
    hits_k = sum(v["hk"] for v in per_intent_raw.values())
    rr_sum = sum(v["rr"] for v in per_intent_raw.values())
    per_intent = {
        intent: {
            "hit_at_1": round(v["h1"] / v["n"], 3) if v["n"] else 0.0,
            "hit_at_k": round(v["hk"] / v["n"], 3) if v["n"] else 0.0,
            "mrr": round(v["rr"] / v["n"], 3) if v["n"] else 0.0,
            "n": v["n"],
        }
        for intent, v in per_intent_raw.items()
    }
    return DatasetResult(
        model_key=model_cfg.key,
        model_label=model_cfg.get("label", model_cfg.hf_id),
        model_dim=model_cfg.get("dim", 768),
        dataset_label=dataset_label,
        hit_at_1=hits_1 / n if n else 0.0,
        hit_at_k=hits_k / n if n else 0.0,
        mrr=rr_sum / n if n else 0.0,
        latency_ms=total_latency / n if n else 0.0,
        n_queries=n,
        per_intent=per_intent,
        misses=misses,
        per_query_rows=per_query_rows or [],
    )


def _log_to_mlflow(result: DatasetResult, model_cfg: DictConfig, top_k: int) -> None:
    run_name = f"{result.model_key}_{result.dataset_label}"
    with mlflow.start_run(run_name=run_name):
        mlflow.set_tags({"model": result.model_key, "dataset": result.dataset_label})
        mlflow.log_params(
            {
                "model_hf_id": model_cfg.hf_id,
                "model_dim": result.model_dim,
                "dataset_label": result.dataset_label,
                "top_k": top_k,
                "n_queries": result.n_queries,
            }
        )
        mlflow.log_metrics(
            {
                "hit_at_1": round(result.hit_at_1, 4),
                f"hit_at_{top_k}": round(result.hit_at_k, 4),
                "mrr": round(result.mrr, 4),
                "latency_ms": round(result.latency_ms, 2),
                "miss_count": len(result.misses),
            }
        )
        for intent, m in result.per_intent.items():
            mlflow.log_metrics(
                {
                    f"{intent}_hit_at_1": m["hit_at_1"],
                    f"{intent}_hit_at_k": m["hit_at_k"],
                    f"{intent}_mrr": m["mrr"],
                }
            )

        if result.per_query_rows:
            buf = io.StringIO()
            writer = csv.DictWriter(buf, fieldnames=list(result.per_query_rows[0].keys()))
            writer.writeheader()
            writer.writerows(result.per_query_rows)
            mlflow.log_text(buf.getvalue(), "per_query_results.csv")


def _print_dataset_table(
    dataset_label: str,
    results: list[DatasetResult],
    top_k: int,
) -> None:
    w = 90
    ranked = sorted(results, key=lambda x: -x.mrr)
    print()
    print("=" * w)
    print(f"Dataset: {dataset_label}")
    if not ranked:
        print("  (no models completed: all skipped)")
        print("=" * w)
        return
    print(
        f"{'Model':<35} {'Dim':>5} {'Hit@1':>7} {f'Hit@{top_k}':>7} "
        f"{'MRR':>7} {'ms/q':>8} {'Misses':>7}"
    )
    print("-" * w)
    for r in ranked:
        print(
            f"{r.model_label:<35} {r.model_dim:>5} {r.hit_at_1:>7.3f} "
            f"{r.hit_at_k:>7.3f} {r.mrr:>7.3f} {r.latency_ms:>7.1f}  {len(r.misses):>6}"
        )
    print()
    for intent in sorted({i for r in ranked for i in r.per_intent}):
        print(f"  {intent}:")
        for r in ranked:
            m = r.per_intent.get(intent, {})
            if m:
                print(
                    f"    {r.model_label:<33}  hit@1={m['hit_at_1']:.3f}  "
                    f"hit@k={m['hit_at_k']:.3f}  mrr={m['mrr']:.3f}  n={m['n']}"
                )
    print()
    best = ranked[0]
    if best.misses:
        print(f"  Misses for {best.model_label} ({len(best.misses)}):")
        for miss in best.misses[:5]:
            got = ", ".join(str(g) for g in miss.get("got", [])[:3]) or "—"
            print(
                f"    [{miss.get('intent', '?'):20}] "
                f"{miss['query']!r:35} expected={miss['expected']!r}  "
                f"got=[{got}]"
            )
        if len(best.misses) > 5:
            print(f"    ... and {len(best.misses) - 5} more")
    print("=" * w)


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    """Compare embedding models across EN and ML query datasets.

    Each enabled model's corpus is encoded once, then scored against every
    dataset defined in ``eval.compare.datasets``. Results printed per dataset.

    CLI examples::

        poetry run model-compare
        poetry run model-compare eval.compare.top_k=10
        poetry run model-compare eval.compare.mlflow=false
    """
    compare_cfg = cfg.eval.compare
    top_k: int = compare_cfg.get("top_k", 5)
    use_mlflow: bool = compare_cfg.get("mlflow", True)

    corpus_path = Path(compare_cfg.corpus_sample)
    if not corpus_path.exists():
        print(f"Corpus sample not found: {corpus_path}")
        print("Run first:  poetry run prepare-eval-sample")
        raise SystemExit(1)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cuda":
        print(f"GPU: {torch.cuda.get_device_name(0)}")
    else:
        print("Running on CPU  (install cu128 torch for faster eval)")

    print(f"Loading corpus sample from {corpus_path}...", flush=True)
    entries = _load_corpus(corpus_path)
    source_counts = {
        s: sum(1 for e in entries if e["source"] == s) for s in ("olam_enml", "datuk", "ekkurup")
    }
    print(f"  {len(entries)} entries — {source_counts}")

    semantic_intents_cfg = compare_cfg.get("semantic_intents")
    semantic_intents: set[str] | None = set(semantic_intents_cfg) if semantic_intents_cfg else None
    if semantic_intents:
        print(f"Intent filter (semantic only): {sorted(semantic_intents)}")

    datasets_cfg = compare_cfg.get("datasets")
    if not datasets_cfg:
        # backward compat: single dataset key
        datasets_cfg = [{"path": compare_cfg.dataset, "label": "default"}]

    loaded_datasets = []
    for ds in datasets_cfg:
        queries = load_dataset(ds.path)
        loaded_datasets.append({"label": ds.label, "queries": queries, "path": ds.path})
        scored_n = sum(
            1 for q in queries if semantic_intents is None or q.intent in semantic_intents
        )
        print(f"  {ds.label}: {scored_n}/{len(queries)} queries scored (semantic intents only)")

    active_models = [m for m in compare_cfg.models if m.get("enabled", True)]
    if not active_models:
        print("No models enabled in config/eval/default.yaml.")
        raise SystemExit(1)

    print(f"\nModels: {[m.key for m in active_models]}")
    if use_mlflow:
        mlflow.set_experiment(_EXPERIMENT)
        print(f"MLflow experiment: '{_EXPERIMENT}'  (run `mlflow ui --port 5001` to browse)\n")

    # results_by_dataset[label] = list of DatasetResult (one per model)
    results_by_dataset: dict[str, list[DatasetResult]] = {ds["label"]: [] for ds in loaded_datasets}

    for model_cfg in active_models:
        print(f"\n{'─' * 60}")
        print(f"Model: {model_cfg.get('label', model_cfg.hf_id)}")

        try:
            trust = model_cfg.get("trust_remote_code", False)
            model = SentenceTransformer(model_cfg.hf_id, device=device, trust_remote_code=trust)
        except Exception as exc:
            print(f"  SKIP — failed to load {model_cfg.hf_id}: {exc}")
            continue

        try:
            corpus_matrix, source_masks = _encode_corpus(
                model, entries, model_cfg.get("passage_prefix", "")
            )

            for ds in loaded_datasets:
                query_prefix = model_cfg.get("query_prefix", "")
                per_intent_raw, misses, total_latency, per_query_rows = _score_queries(
                    ds["queries"],
                    model,
                    corpus_matrix,
                    source_masks,
                    entries,
                    query_prefix,
                    top_k,
                    semantic_intents=semantic_intents,
                )
                scored_queries = [
                    q
                    for q in ds["queries"]
                    if semantic_intents is None or q.intent in semantic_intents
                ]
                result = _build_dataset_result(
                    model_cfg,
                    ds["label"],
                    scored_queries,
                    per_intent_raw,
                    misses,
                    total_latency,
                    per_query_rows,
                )
                results_by_dataset[ds["label"]].append(result)

                if use_mlflow:
                    _log_to_mlflow(result, model_cfg, top_k)
                    print(
                        f"  → {ds['label']}: logged to MLflow run '{model_cfg.key}_{ds['label']}'"
                    )
        except Exception as exc:
            print(f"  SKIP — error during eval for {model_cfg.key}: {exc}")
        finally:
            del model
            if device == "cuda":
                torch.cuda.empty_cache()

    for ds in loaded_datasets:
        _print_dataset_table(ds["label"], results_by_dataset[ds["label"]], top_k)

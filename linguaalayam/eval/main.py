"""Evaluation entrypoint — measures retrieval quality against a labeled query set."""

import json
import logging
from pathlib import Path

import hydra
from dotenv import load_dotenv
from omegaconf import DictConfig

from linguaalayam.database import build_engine, build_session_factory
from linguaalayam.embeddings import EmbeddingService
from linguaalayam.eval.metrics import QueryResult, intent_breakdown, mrr, tool_breakdown
from linguaalayam.eval.runner import run_eval
from linguaalayam.rag.tools import DictionaryTools

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

log = logging.getLogger(__name__)


def _print_summary(results: list[QueryResult], cfg: DictConfig) -> None:
    n = len(results)
    if n == 0:
        print("No results — is the dataset empty?")
        return

    hits_1 = sum(r.hit_at_1 for r in results)
    hits_k = sum(r.hit_at_k for r in results)
    mrr_val = mrr(results)
    tools = tool_breakdown(results)
    intents = intent_breakdown(results)
    avg_ms = sum(r.latency_ms for r in results) / n

    top_k = cfg.eval.get("top_k", 5)

    print()
    print("=" * 60)
    print("Evaluation Summary")
    print("=" * 60)
    print(f"Dataset : {cfg.eval.dataset} ({n} queries)")
    print(f"Model   : {cfg.embedding.model}")
    print(f"Top-k   : {top_k}")
    print()
    print(f"Hit@1   : {hits_1/n:.3f}  ({hits_1}/{n})")
    print(f"Hit@{top_k}   : {hits_k/n:.3f}  ({hits_k}/{n})")
    print(f"MRR     : {mrr_val:.3f}")
    print(f"Latency : {avg_ms:.1f} ms avg")
    print()

    print("Tool attribution:")
    hit_count = hits_k or 1
    for tool in ("exact", "fuzzy", "semantic"):
        c = tools.get(tool, 0)
        print(f"  {tool:<10}: {c:3}  ({c/hit_count*100:.1f}% of hits)")
    print(f"  {'miss':<10}: {tools.get('miss', 0):3}")
    print()

    print("By intent:")
    for intent, m in intents.items():
        print(f"  {intent:<12}  hit@1={m['hit@1']:.2f}  hit@k={m['hit@k']:.2f}  mrr={m['mrr']:.2f}  n={m['count']}")

    misses = [r for r in results if not r.hit_at_k]
    if misses:
        print()
        print(f"Misses ({len(misses)}):")
        for r in misses[:10]:
            got = ", ".join(r.retrieved_headwords[:3]) or "—"
            print(f"  {r.query!r:45} expected={r.expected_headword!r}  got=[{got}]")
        if len(misses) > 10:
            print(f"  ... and {len(misses) - 10} more")

    print("=" * 60)


def _write_results(results: list[QueryResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for r in results:
            f.write(json.dumps({
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
            }) + "\n")
    log.info("Results written to %s", path)


@hydra.main(config_path="../../config", config_name="config", version_base=None)
def main(cfg: DictConfig) -> None:
    """Evaluate retrieval quality against the labeled query set.

    Usage:
        poetry run eval
        poetry run eval eval.top_k=10
        poetry run eval eval.dataset=data/eval/my_queries.jsonl eval.output=results/run1.jsonl
        poetry run eval eval.fuzzy_threshold=0.2
    """
    engine = build_engine(cfg.database)
    session_factory = build_session_factory(engine)

    log.info("Loading embedding model: %s", cfg.embedding.model)
    service = EmbeddingService(cfg.embedding)

    tools = DictionaryTools(session_factory, service)

    log.info("Running eval on %s", cfg.eval.dataset)
    results = run_eval(tools, cfg.eval)

    _print_summary(results, cfg)

    if cfg.eval.output:
        _write_results(results, Path(cfg.eval.output))


if __name__ == "__main__":
    main()

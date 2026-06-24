"""Evaluation package — dataset loading, retrieval metrics, and eval runner."""

from .dataset import EvalQuery, load_dataset
from .metrics import hit_rate, hit_rate_at_1, intent_breakdown, mrr, tool_breakdown
from .runner import QueryResult, run_eval

__all__ = [
    "EvalQuery",
    "load_dataset",
    "QueryResult",
    "run_eval",
    "hit_rate",
    "hit_rate_at_1",
    "mrr",
    "tool_breakdown",
    "intent_breakdown",
]

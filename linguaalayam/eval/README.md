# Evaluation Harness

Measures retrieval quality against a labeled query set. LLM-free — deterministic, requires no API key, runs against the real ingested corpus.

## Usage

```bash
# Run against the default 50-query set
poetry run eval

# Tune parameters
poetry run eval eval.top_k=10 eval.fuzzy_threshold=0.2

# Write per-query JSONL results for further analysis
poetry run eval eval.output=results/v0.2.jsonl

# Use a custom dataset
poetry run eval eval.dataset=data/eval/my_queries.jsonl
```

## Metrics (currently implemented)

| Metric | Description |
|---|---|
| **Hit@1** | Fraction of queries where the expected headword is the top result |
| **Hit@k** | Fraction of queries where the expected headword appears in the top-k results |
| **MRR** | Mean Reciprocal Rank — average of 1/rank across all queries |
| **Tool attribution** | How many hits came from exact / fuzzy / semantic search |
| **Intent breakdown** | Hit@1, Hit@k, MRR sliced by query intent (define, translate, etc.) |
| **Latency** | Average retrieval time per query in milliseconds |

## Query set (`data/eval/queries.jsonl`)

50 labeled queries across six categories:

| Category | Count | Examples |
|---|---|---|
| Exact single-word | 15 | `run`, `water`, `peace` |
| Prose define | 10 | `what does run mean`, `define ephemeral` |
| Translation | 5 | `run in Malayalam`, `translate love to Malayalam` |
| Fuzzy / typo | 5 | `runing`, `watter`, `beautifull` |
| Semantic / paraphrase | 10 | `to move quickly on foot`, `complete absence of sound` |
| Edge cases | 5 | `urn`, `pastoral`, `nostalgia` |

## Planned additions

| Level | Additions |
|---|---|
| **ML / AI Engineer** | LLM-as-judge scoring (faithfulness, answer relevance, conciseness per `SKILLS.md`); prompt ablation across system prompt variants |
| **MLOps** | Baseline persistence per git tag; regression detection on PRs (e.g. "Hit@5 dropped from 0.91 → 0.84"); experiment tracking via JSONL diff or W&B |
| **Business** | Vocabulary coverage (% of a word list that returns results); gold EN→ML translation accuracy set; answer length distribution as a TTS quality proxy |

## CI

The `eval.yml` workflow (manual trigger) spins up a pgvector service container, seeds a minimal fixture corpus, and runs `poetry run eval`. See `.github/workflows/eval.yml`.

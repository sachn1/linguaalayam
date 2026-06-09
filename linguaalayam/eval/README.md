# Evaluation Harness

Four eval commands, all LLM-free, deterministic, no API key needed.

| Command | What it tests | Needs DB? |
|---|---|---|
| `eval-prepare-queries` | Generate query sets from live corpus | Yes |
| `eval-prepare-corpus` | Build corpus sample and pin eval headwords | Yes |
| `eval-retrieval` | Full pipeline (exact + fuzzy + semantic) against live DB | Yes |
| `eval-embedding` | Embedding model quality offline, multiple models side-by-side | No (uses corpus sample) |

**First-time setup order:**
```bash
poetry run eval-prepare-queries   # generate queries_en.jsonl + queries_ml.jsonl
poetry run eval-prepare-corpus    # pin headwords, sample corpus_sample.jsonl
poetry run eval-retrieval         # pipeline eval
poetry run eval-embedding         # model comparison
```

---

## `eval-prepare-queries` — generate query sets

Samples entries from the live DB and derives query/expected-headword pairs for each intent.
Writes `data/eval/queries_en.jsonl` (Latin/English input) and `data/eval/queries_ml.jsonl` (Malayalam input).

```bash
poetry run eval-prepare-queries
poetry run eval-prepare-queries --per-intent 15 --seed 42
poetry run eval-prepare-queries --out-en data/eval/queries_en.jsonl
```

Re-run whenever the corpus changes or you want a fresh sample.

---

## `eval-prepare-corpus` — build corpus sample

Pulls a stratified sample from the DB (by source), guarantees every eval headword is present,
and writes `data/eval/corpus_sample.jsonl`. The corpus sample is gitignored — it must be
generated locally before running `eval-embedding`.

```bash
poetry run eval-prepare-corpus
poetry run eval-prepare-corpus --sample-size 3000
poetry run eval-prepare-corpus --output data/eval/corpus_sample.jsonl
```

Re-run whenever query files change or the DB is re-ingested.

---

## `eval-retrieval` — pipeline quality

Tests the full retrieval pipeline (exact + fuzzy + semantic) against the live DB.
Runs against both EN and ML query sets and reports metrics broken down by tool and by intent.

```bash
poetry run eval-retrieval
poetry run eval-retrieval eval.top_k=10
poetry run eval-retrieval eval.fuzzy_threshold=0.2
poetry run eval-retrieval eval.output=results/v2.2.jsonl

# single dataset only
poetry run eval-retrieval eval.datasets=null eval.dataset=data/eval/queries_ml.jsonl
```

### Metrics

| Metric | Description |
|---|---|
| **Hit@1** | Fraction of queries where the correct headword is ranked #1 |
| **Hit@k** | Fraction where the correct headword appears anywhere in top-k results |
| **MRR** | Mean Reciprocal Rank: average of 1/rank across all queries. 1.0 = always rank 1 |
| **Latency** | Average end-to-end retrieval time per query in ms |
| **miss_count** | Queries where the correct headword was not found in top-k |

#### Tool attribution

| Attribution | Meaning |
|---|---|
| `exact` | Hit came from exact headword string match |
| `fuzzy` | Hit came from trigram (pg_trgm) similarity |
| `semantic` | Hit came from HNSW vector cosine similarity |
| `miss` | Correct headword not found in top-k by any tool |

#### Intent breakdown

Per-intent Hit@1, Hit@k, MRR so you can see which query types the pipeline handles well and which it doesn't.
See [Query sets](#query-sets) for intent definitions.

---

## `eval-embedding` — embedding model comparison

Tests multiple embedding models offline (no re-ingestion or live DB needed after corpus sample is built).
Encodes `corpus_sample.jsonl` once per model, then scores against **semantic intents only** — exact
and fuzzy queries are excluded because their pass/fail is independent of the embedding model.

```bash
# compare all enabled models (stdout + MLflow)
poetry run eval-embedding
poetry run eval-embedding eval.compare.top_k=10
poetry run eval-embedding eval.compare.mlflow=false   # stdout only

# browse results
mlflow ui --port 5001
```

Models and their `enabled:` flags live in `config/eval/default.yaml` under `compare.models`.

### Metrics

Same definitions as eval-retrieval (Hit@1, Hit@k, MRR, miss_count, latency_ms),
calculated purely from cosine similarity.

#### Per-intent breakdown and MLflow

Each model × dataset combination is logged as an MLflow run with:
- Aggregate metrics: `hit_at_1`, `hit_at_{k}`, `mrr`, `latency_ms`, `miss_count`
- Per-intent metrics: `{intent}_hit_at_1`, `{intent}_hit_at_k`, `{intent}_mrr`
- Per-query CSV artifact: `per_query_results.csv` (query, expected_headword, intent, hit_at_1, hit_at_k, reciprocal_rank, retrieved_top3, latency_ms)

---

## Query sets

### EN-input — `data/eval/queries_en.jsonl`

Queries where the input is English or Latin script (Manglish).

| Intent | Query form | Expected result |
|---|---|---|
| `en_from_en_exact` | English headword (Olam) | Same English headword |
| `en_from_en_semantic` | English synonym (Ekkurup) | English headword |
| `ml_from_en_exact` | English headword (Ekkurup bridge) | Malayalam headword (Datuk) |
| `ml_from_en_semantic` | English synonym → Malayalam | Malayalam headword (Datuk) |
| `en_from_manglish` | ISO-romanised Malayalam | English headword |

`en_from_en_exact` and `ml_from_en_exact` are scored in **`eval-retrieval` only** (exact tool).
All `*_semantic` and `*_manglish` intents are scored in **both** commands.

### ML-input — `data/eval/queries_ml.jsonl`

Queries where the input is Malayalam script or Manglish (romanised Malayalam).

| Intent | Query form | Expected result |
|---|---|---|
| `ml_from_ml_exact` | Malayalam headword (Datuk) | Same Malayalam headword |
| `ml_from_ml_semantic` | Malayalam definition fragment (Datuk) | Malayalam headword |
| `en_from_ml_exact` | Malayalam headword (Ekkurup bridge) | English headword |
| `en_from_ml_semantic` | Malayalam definition → English | English headword |
| `ml_from_manglish` | ISO-romanised Malayalam | Malayalam headword |

`ml_from_ml_exact` and `en_from_ml_exact` are scored in **`eval-retrieval` only** (exact tool).
All `*_semantic` and `*_manglish` intents are scored in **both** commands.

`corpus_sample.jsonl` is generated by `eval-prepare-corpus` and is gitignored (derived data, ~5 MB).
Re-run it whenever query files change or the DB is re-ingested.

---

## CI

The `eval.yml` workflow (manual trigger) runs `eval-retrieval` against a seeded pgvector container.
See `.github/workflows/eval.yml`.

## Local GPU setup

Use `make install-local` - auto-detects `nvidia-smi` and installs CUDA torch if a GPU is present.
Speeds up `eval-embedding` ~5–10x. CPU torch is used in CI and production.

```bash
make install-local   # local dev (GPU auto-detected)
poetry install       # CI / CPU-only
```

See `CLAUDE.md` for details on the GPU/CPU torch split.

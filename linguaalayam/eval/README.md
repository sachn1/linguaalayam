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

`eval-retrieval` has two modes, chosen automatically:
- **Multi-model compare** — runs whenever `data/eval/corpus_sample.jsonl` exists (built by
  `eval-prepare-corpus`) and `eval.compare.models` has at least one enabled entry. Iterates over
  every enabled embedding model; ignores `eval.rerank`.
- **Single-model** — the production embedding model against the live DB (real pgvector semantic
  search). This is the only mode that applies `eval.rerank`. Force it even when a corpus sample
  is present with `eval.compare=null`.

Both modes log one MLflow run per (model, dataset) — or (model, dataset, reranked) in single-model
mode — to the `retrieval_pipeline` experiment, unless disabled.

```bash
poetry run eval-retrieval
poetry run eval-retrieval eval.top_k=10
poetry run eval-retrieval eval.fuzzy_threshold=0.2
poetry run eval-retrieval eval.output=results/v2.2.jsonl

# single dataset only
poetry run eval-retrieval eval.datasets=null eval.dataset=data/eval/queries_ml.jsonl

# force single-model mode (production model, live DB) even if corpus_sample.jsonl exists
poetry run eval-retrieval eval.compare=null

# with cross-encoder reranking (single-model mode only — ignored by multi-model compare)
poetry run eval-retrieval eval.compare=null eval.rerank=true
poetry run eval-retrieval eval.compare=null eval.rerank=true eval.reranker_model=cross-encoder/some-other-model
poetry run eval-retrieval eval.compare=null eval.rerank=true eval.rerank_candidate_k=50

# stdout only, skip MLflow
poetry run eval-retrieval eval.compare=null eval.mlflow=false

# browse results
mlflow ui --port 5001
```

Run once with `eval.rerank=false` (the default) and once with `eval.rerank=true` — both logged to
MLflow with a `reranked` tag/param so you can pull up both runs side by side — and compare
Hit@1/Hit@k/MRR against the added latency to decide whether reranking earns its cost before
turning it on by default in `config/rag/default.yaml`.

When `eval.rerank=true`, retrieval fetches `eval.rerank_candidate_k` (default 25, shared with
`rag.rerank_candidate_k`) candidates instead of `top_k` before the cross-encoder reorders and cuts
down to `top_k` — otherwise the reranker only reshuffles a pool already truncated to `top_k` and
can never promote a candidate that was retrieved but ranked below it.

**Finding (2026-09-06, `cross-encoder/mmarco-mMiniLMv2-L12-H384-v1`, pre-collision-fix dataset):**
reranking did not help even after widening the candidate pool to 25. EN-input got slightly worse
(Hit@1 0.20→0.18, MRR 0.20→0.19) with roughly 2x latency; ML-input's Hit@1 improved marginally
(0.217→0.239) but Hit@5 got *worse* (0.283→0.261) — the reranker demoted a correct candidate out of
the top-5 that was already there. Do not flip `rerank: true` in `config/rag/default.yaml` on this
evidence alone. Investigating *why* led to the [Known limitations](#known-limitations-found-while-investigating-why-reranking-showed-no-lift-2026-09-06)
below: most of the miss rate driving this result was eval-dataset/architecture artifacts, not
genuine retrieval failures reranking could fix. Re-run this comparison against the current
(collision-filtered) query files before drawing further conclusions about reranking itself.

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

## Known limitations (found while investigating why reranking showed no lift, 2026-09-06)

- **Fixed — exact-match collisions in `*_semantic` intents.** `prepare_eval_queries.py` used to
  pick a synonym/gloss word for `en_from_en_semantic` and `ml_from_ml_semantic` without checking
  whether that word was *also* a real headword elsewhere in the corpus (e.g. "cowardly" as a
  synonym of "pusillanimous", when "cowardly" is itself an Olam headword; or "സുഗന്ധം" as the
  one-word Datuk gloss for "ഘ്രാണതർപ്പണം", when "സുഗന്ധം" is itself a Datuk headword).
  `merge_candidates` always ranks exact > fuzzy > semantic, so the exact tool correctly returned
  the colliding word's own entry — not a retrieval failure, but it scored as one. Both generators
  now take an `exclude_headwords` set and filter these out. This inflated `ml_from_ml_semantic`'s
  apparent Hit@1 before the fix (collisions look like "free" exact-match wins); after the fix the
  intent measures genuine semantic recall and both the number and the *reason* for a miss are
  meaningful.
- **Still open — cross-lingual "exact" intents can't be satisfied by the exact tool.**
  `ml_from_en_exact`, `en_from_ml_exact`, `ml_from_en_semantic`, and `en_from_ml_semantic` bridge
  English and Malayalam via Ekkurup, but Ekkurup stores exactly one headword string per row (the
  English side) — the Malayalam translation only ever lives inside the row's body text, never as
  an indexed headword. `exact_lookup` is a literal string match on the `headword` column, so it
  structurally cannot resolve an EN query to an ML headword or vice versa; these intents sit at
  0% regardless of retrieval or reranking quality. Not yet decided whether to rescope them
  (semantic-only scoring), require LLM-based query understanding (which production uses but this
  LLM-free harness deliberately doesn't), or drop them.
- **Still open — Manglish intents test a feature this pipeline doesn't have.**
  `en_from_manglish` and `ml_from_manglish` feed raw ISO-romanised Malayalam directly into
  exact/fuzzy/semantic lookup with no conversion step, so they sit at 0% by construction.
  Manglish→Malayalam conversion (Varnam) is only wired into `linguaalayam/api/web.py`'s request
  handler — `rag/pipeline.py`, `rag/tools.py`, and this eval harness never call it. These intents
  are measuring an integration gap between the web app and the shared RAG/eval/MCP pipeline, not
  retrieval quality. Fixing this means deciding whether Varnam belongs in the shared query
  understanding path (`rag/query_understanding.py`) rather than only in the web layer — out of
  scope for an eval-only fix.

## Future work (low priority)

- **RAGAS faithfulness eval for the RAG pipeline.** Current metrics (Hit@k, MRR) score retrieval
  only. A RAGAS-style faithfulness/answer-relevance check on `rag/pipeline.py`'s synthesized
  answers (`llm=anthropic`/`openai`/`togetherai`) would catch hallucination against retrieved
  candidates that retrieval metrics can't see. Needs an LLM-as-judge budget, so it's a separate,
  non-deterministic eval track from this harness rather than an addition to it.
- **One embedding per sense for Ekkurup.** Ekkurup entries currently embed one vector per headword
  even when a headword has multiple distinct senses/synonym groups, which dilutes the embedding
  and can hurt semantic recall for polysemous words. Splitting `to_embed_text()` per sense (see
  `linguaalayam/models/entries.py` / `linguaalayam/corpus/ekkurup.py`) would mean one DB row (and
  one HNSW-indexed vector) per sense instead of per headword — a schema and ingestion change, so
  it needs its own design pass before starting.

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

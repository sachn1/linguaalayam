# LinguAalayam

A Malayalam dictionary knowledge base and RAG pipeline. Ingests open-source Malayalam lexical data into a vector database, enables hybrid retrieval (exact, fuzzy, semantic), and synthesises answers via a LangGraph pipeline backed by Claude or any HuggingFace model.

> Built with the assistance of [Claude](https://claude.ai) (Anthropic).

---

## Current State (v0.2)

- Ingests the **Olam EN→ML corpus** (~58,000 English headwords with Malayalam definitions) into a local Postgres + pgvector instance
- Generates embeddings using a multilingual sentence transformer model
- Checkpoint-based ingestion — resumable after failures, never re-embeds already-vectorized entries
- **Hybrid retrieval** — three tools per query: exact headword match, trigram fuzzy search (pg_trgm), and HNSW cosine semantic search
- **LangGraph RAG pipeline** — query understanding → retrieval → optional cross-encoder reranking → answer synthesis
- **Pluggable LLM** — Claude (default) or any HuggingFace instruction model
- **Evaluation harness** — offline retrieval metrics (Hit@k, MRR, tool attribution) against a labeled query set

---

## Database

LinguAalayam runs against a **local Postgres + pgvector** instance (via Docker). This replaced an earlier Supabase free-tier setup, which was dropped because the embedded data alone exceeds the 500 MB free-tier limit.

Other vector store options were considered and ruled out:

- **FAISS** — ruled out. No metadata filtering (source, entry\_type), no SQL, no persistence model — would require a full rewrite of the query layer and lose the ability to filter by corpus or do hybrid search.
- **Qdrant** — ruled out. Different client API, different query semantics — would require replacing SQLAlchemy, the ORM, and Alembic migrations with a new stack for no meaningful gain on a private, single-machine project.

Local Postgres + pgvector keeps the full SQLAlchemy + Alembic stack intact, has no storage limits, adds no network latency, and works offline.

---

## Roadmap

### v0.2 — RAG ready
- [x] Query preprocessing — extract target word from natural language queries ("what does X mean", "define X")
- [x] Hybrid search — exact headword match, trigram fuzzy search, and semantic fallback
- [x] Response formatting — structured answer synthesis from top-k retrieved entries
- [x] Evaluation harness — retrieval metrics on a labeled query set

### v0.3 — MCP server (first release)
- [ ] Wrap retriever as an MCP server with three tools: `lookup_definition`, `lookup_in_corpus`, `cross_lingual_lookup`
- [ ] Plug into Claude Code for live testing
- [ ] Claude Desktop config and setup instructions

### v0.4 — Additional corpora
- [ ] **Datuk** — ML→ML corpus (~83,000 Malayalam headwords with Malayalam definitions)
- [ ] **Dravidian comparative** — cross-lingual corpus with Kannada, Tamil, and Telugu equivalents
- [ ] **EK Kurup** — EN→ML thesaurus with 900,000+ synset entries (requires separate chunking strategy)
- [ ] Per-corpus filtering in retrieval

### v0.5 — Second release
- [ ] MCP server updated with multi-corpus support
- [ ] Cross-lingual lookup tool backed by real data
- [ ] End-to-end integration tests against Claude Code

### v0.6 — Improvements and optimisations
- [ ] Embedding model evaluation — compare `multilingual-mpnet` vs `multilingual-e5-large` on retrieval quality
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — track retrieval latency and top-k quality metrics

---

## Setup

### Prerequisites

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)
- Docker (for the Postgres + pgvector container)

### Start the database

```bash
docker run -d --name linguaalayam-pg \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  ankane/pgvector

docker exec -it linguaalayam-pg psql -U postgres -c "CREATE DATABASE linguaalayam;"
```

### Install

```bash
poetry install
poetry run pre-commit install
```

### Configure

Copy `.env.example` to `.env` and fill in your values:

```bash
DB_USER=postgres
DB_PASSWORD=yourpassword
DB_HOST=localhost
DB_PORT=5432
DB_NAME=linguaalayam
ANTHROPIC_API_KEY=sk-ant-...   # required for the RAG pipeline (Claude)
# DB_SSLMODE=require           # uncomment for Supabase or other hosted Postgres
```

### Run migrations

```bash
poetry run alembic upgrade head
```

### Download data

Download the EN→ML dataset from [olam.in/p/open](https://olam.in/p/open) and place it at:

```
data/
└── enml/
    └── enml
```

---

## Ingestion

```bash
# Full ingest
poetry run ingest

# Debug run — 50 entries only
poetry run ingest corpus=debug

# Switch embedding model
poetry run ingest embedding=multilingual_e5_large
```

Ingestion is resumable — re-running skips already-inserted entries and restores in-progress embeddings from a checkpoint file in `.checkpoints/`.

---

## RAG Pipeline

```bash
# Simple query — Hydra override (avoid special characters: commas, quotes, dashes)
poetry run rag 'rag.query=run'
poetry run rag 'rag.query=ഓടുക' rag.source=olam_enml

# Complex / prose queries — env var sidesteps Hydra's lexer
RAG_QUERY='what does the word "pastoral" mean?' poetry run rag
RAG_QUERY='translate justice to Malayalam' poetry run rag rag.rerank=true

# Tune retrieval
poetry run rag 'rag.query=run' rag.top_k=10 rag.rerank=true

# Switch LLM
RAG_QUERY='define ephemeral' poetry run rag llm=huggingface
```

The pipeline runs four nodes: **query understanding** (regex patterns with LLM fallback) → **retrieval** (exact + fuzzy + semantic in parallel, merged and deduplicated) → **reranking** (optional cross-encoder) → **synthesis** (LLM answer constrained by `linguaalayam/rag/SKILLS.md`).

Each candidate shows its source tool and similarity score:

```
  [1] run     [exact    1.000]  word: run  [v] ഓടുക...
  [2] runs    [fuzzy    0.612]  word: runs  [n] ഓട്ടങ്ങൾ...
  [3] sprint  [semantic 0.873]  word: sprint  [v] ദ്രുതഗതിയിൽ...
```

To use HuggingFace models instead of Claude, install the optional dependency group:

```bash
poetry install --with huggingface
poetry run rag 'rag.query=run' llm=huggingface
```

---

## Retrieval (debug)

```bash
# Default — searches for "run" across all ingested data
poetry run debug-retriever

# Custom query
poetry run debug-retriever --query "what does run mean"

# Filter by corpus
poetry run debug-retriever --query "ഓടുക" --source olam_enml --top-k 3
```

---

## Evaluation

The evaluation harness measures **retrieval quality** against a labeled query set. It is LLM-free — deterministic, requires no API key, and runs against the real ingested corpus.

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

### Metrics (currently implemented)

| Metric | Description |
|---|---|
| **Hit@1** | Fraction of queries where the expected headword is the top result |
| **Hit@k** | Fraction of queries where the expected headword appears in the top-k results |
| **MRR** | Mean Reciprocal Rank — average of 1/rank across all queries |
| **Tool attribution** | How many hits came from exact / fuzzy / semantic search |
| **Intent breakdown** | Hit@1, Hit@k, MRR sliced by query intent (define, translate, etc.) |
| **Latency** | Average retrieval time per query in milliseconds |

The eval set (`data/eval/queries.jsonl`) contains 50 labeled queries across six categories:

| Category | Count | Examples |
|---|---|---|
| Exact single-word | 15 | `run`, `water`, `peace` |
| Prose define | 10 | `what does run mean`, `define ephemeral` |
| Translation | 5 | `run in Malayalam`, `translate love to Malayalam` |
| Fuzzy / typo | 5 | `runing`, `watter`, `beautifull` |
| Semantic / paraphrase | 10 | `to move quickly on foot`, `complete absence of sound` |
| Edge cases | 5 | `urn`, `pastoral`, `nostalgia` |

---

## Testing

```bash
# Run all tests
poetry run pytest

# Run a specific module
poetry run pytest tests/corpus
poetry run pytest tests/database
poetry run pytest tests/embeddings
```

---

## CI

Two GitHub Actions workflows are included:

**`ci.yml`** — runs on every push and pull request to `develop` and `main`:
- `ruff check` and `ruff format --check`
- Full pytest suite (SQLite in-memory, no database needed)
- Venv cached by `poetry.lock` hash for fast runs

**`eval.yml`** — manual trigger (`workflow_dispatch`) only:
- Spins up a pgvector service container, runs migrations, seeds a minimal eval corpus fixture
- Runs `poetry run eval` with configurable `top_k` and `fuzzy_threshold` inputs
- Optionally writes results to a JSONL file
- HuggingFace model cached between runs to avoid re-downloading (~400 MB)

---

## Data sources

All data is open source and sourced from [Olam](https://olam.in/p/open):

| Corpus | Type | Entries | Status |
|---|---|---|---|
| Olam EN→ML | English → Malayalam | ~58,000 headwords | ✅ Ingested |
| Datuk | Malayalam → Malayalam | ~83,000 headwords | 🔜 v0.4 |
| Dravidian comparative | ML / KN / TA / TE | ~few thousand | 🔜 v0.4 |
| EK Kurup | EN→ML thesaurus | ~900,000 entries | 🔜 v0.4 |

---

## Tech stack

- **Python 3.11+**, Poetry
- **SQLAlchemy 2.0** + psycopg2 + pgvector
- **Postgres + pgvector** (local Docker container) for vector storage
- **sentence-transformers** (`paraphrase-multilingual-mpnet-base-v2`) for embeddings
- **LangGraph** + **LangChain** for the RAG pipeline graph
- **Anthropic Claude** (default LLM) or **HuggingFace** models (optional)
- **Hydra** for configuration management
- **Alembic** for schema migrations
- **pytest** + ruff + pre-commit for testing and linting

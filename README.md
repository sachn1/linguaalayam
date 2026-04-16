# LinguAalayam

A Malayalam dictionary knowledge base and semantic retrieval pipeline. Ingests open-source Malayalam lexical data into a vector database and enables semantic search over definitions — built toward a RAG-ready, agent-accessible tool for Malayalam language understanding.

---

## Current State (v0.1)

- Ingests the **Olam EN→ML corpus** (~58,000 English headwords with Malayalam definitions) into Supabase (Postgres + pgvector)
- Generates embeddings using a multilingual sentence transformer model
- Checkpoint-based ingestion — resumable after failures, never re-embeds already-vectorized entries
- Debug retrieval script for top-k semantic search against the ingested data

---

## Roadmap

### v0.2 — RAG ready
- [ ] Query preprocessing — extract target word from natural language queries ("what does X mean", "define X")
- [ ] Hybrid search — exact headword match with semantic fallback
- [ ] Response formatting — structured answer synthesis from top-k retrieved entries
- [ ] Evaluation harness — measure retrieval precision on a held-out query set

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
- A [Supabase](https://supabase.com) project (free tier works)

### Install

```bash
poetry install
poetry run pre-commit install
```

### Configure

Create a `.env` file in the project root:

```bash
DB_USER=postgres
DB_PASSWORD=your-password
DB_HOST=db.xxxxxxxxxxxx.supabase.co
DB_PORT=5432
DB_NAME=postgres
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
- **Supabase** (Postgres) for vector storage
- **sentence-transformers** (`paraphrase-multilingual-mpnet-base-v2`) for embeddings
- **Hydra** for configuration management
- **Alembic** for schema migrations
- **pytest** + ruff + pre-commit for testing and linting

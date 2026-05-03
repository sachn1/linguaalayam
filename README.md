# LinguAalayam

A Malayalam dictionary knowledge base and semantic retrieval pipeline. Ingests open-source Malayalam lexical data into a vector database and enables semantic search over definitions — built toward a RAG-ready, agent-accessible tool for Malayalam language understanding.

---

## Current State (v0.1)

- Ingests the **Olam EN→ML corpus** (~58,000 English headwords with Malayalam definitions) into a local Postgres + pgvector instance
- Generates embeddings using a multilingual sentence transformer model
- Checkpoint-based ingestion — resumable after failures, never re-embeds already-vectorized entries
- Debug retrieval script for top-k semantic search against the ingested data

---

## Database

LinguAalayam runs against a **local Postgres + pgvector** instance (via Docker). This replaced an earlier Supabase free-tier setup, which was dropped because the embedded data alone exceeds the 500 MB free-tier limit.

Other vector store options were considered and ruled out:

- **Supabase** — dropped. Free tier capped at 500 MB; the olam_enml corpus alone exceeds this. No longer actively supported.
- FAISS — ruled out. No metadata filtering (source, entry\_type), no SQL, no persistence model — would require a full rewrite of the query layer and lose the ability to filter by corpus or do hybrid search.
- Qdrant — ruled out. Different client API, different query semantics — would require replacing SQLAlchemy, the ORM, and Alembic migrations with a new stack for no meaningful gain on a private, single-machine project.

Local Postgres + pgvector keeps the full SQLAlchemy + Alembic stack intact, has no storage limits, adds no network latency, and works offline.

---

## Roadmap

### v0.2 — RAG ready
- [x] Query preprocessing — extract target word from natural language queries ("what does X mean", "define X")
- [x] Hybrid search — exact headword match with semantic fallback
- [x] Response formatting — structured answer synthesis from top-k retrieved entries
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
# DB_SSLMODE=require   # uncomment for Supabase or other hosted Postgres
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
- **Postgres + pgvector** (local Docker container) for vector storage
- **sentence-transformers** (`paraphrase-multilingual-mpnet-base-v2`) for embeddings
- **Hydra** for configuration management
- **Alembic** for schema migrations
- **pytest** + ruff + pre-commit for testing and linting

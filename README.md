# LinguAalayam

A Malayalam dictionary knowledge base, RAG pipeline, and MCP server. Ingests open-source Malayalam lexical data into a vector database, enables hybrid retrieval (exact, fuzzy, semantic), synthesises answers via a LangGraph pipeline backed by Claude or any HuggingFace model, and exposes the retrieval tools as an MCP server for use with Claude Code and Claude Desktop.

> Built with the assistance of [Claude](https://claude.ai) (Anthropic).

---

## Current State (v0.3)

- Ingests the **Olam EN→ML corpus** (~58,000 English headwords with Malayalam definitions) into a local Postgres + pgvector instance
- Checkpoint-based ingestion — resumable after failures, never re-embeds already-vectorised entries
- **Hybrid retrieval** — exact headword match, trigram fuzzy search (pg_trgm), and HNSW cosine semantic search
- **LangGraph RAG pipeline** — query understanding → retrieval → optional cross-encoder reranking → answer synthesis
- **Pluggable LLM** — Claude via Anthropic API; no-LLM mode returns structured text from the reranker directly
- **Evaluation harness** — offline retrieval metrics (Hit@k, MRR, tool attribution) against a labeled query set
- **MCP server** — exposes `exact_lookup`, `fuzzy_lookup`, and `semantic_lookup` as MCP tools; works with Claude Code and Claude Desktop out of the box

---

## Database

LinguAalayam runs against a **local Postgres + pgvector** instance (via Docker). This replaced an earlier Supabase free-tier setup, which was dropped because the embedded data alone exceeds the 500 MB free-tier limit.

Other vector store options were considered and ruled out:

- **FAISS** — no metadata filtering, no SQL, no persistence model — would require a full rewrite of the query layer and lose hybrid search.
- **Qdrant** — different client API and query semantics — would require replacing SQLAlchemy, the ORM, and Alembic for no meaningful gain on a single-machine project.

Local Postgres + pgvector keeps the full SQLAlchemy + Alembic stack intact, has no storage limits, adds no network latency, and works offline.

---

## Roadmap

### v0.2 — RAG ready
- [x] Query preprocessing — extract target word from natural language queries
- [x] Hybrid search — exact, fuzzy, and semantic retrieval
- [x] Response synthesis — LLM answer from top-k retrieved entries
- [x] Evaluation harness — retrieval metrics on a labeled query set

### v0.3 — MCP server (first release)
- [x] MCP server with three tools: `exact_lookup`, `fuzzy_lookup`, `semantic_lookup`
- [x] Claude Code integration via `.mcp.json` project config
- [x] Claude Desktop setup instructions

### v0.4 — LLM adapter + MCP resources
- [ ] Replace direct Anthropic/HuggingFace calls with a provider adapter pattern (LiteLLM-backed `AnthropicAdapter`, `OpenAIAdapter`, `NoLLMAdapter`)
- [ ] Remove HuggingFace text-generation option — reranker and embeddings are the only local models; LLM is always API-backed or absent
- [ ] `NoLLMAdapter` — no API key is not an error; synthesis falls back to structured reranker output
- [ ] MCP resources — expose dictionary entries as browsable URI-addressed resources (`dictionary://{headword}`) alongside the existing tools

### v0.5 — Additional corpora
- [ ] **Datuk** — ML→ML corpus (~83,000 Malayalam headwords with Malayalam definitions)
- [ ] **Dravidian comparative** — cross-lingual corpus with Kannada, Tamil, and Telugu equivalents
- [ ] **EK Kurup** — EN→ML thesaurus with 900,000+ synset entries (requires separate chunking strategy)
- [ ] Per-corpus filtering in retrieval

### v0.6 — Frontend and self-hosting
- [ ] Thin FastAPI layer over `DictionaryTools` for HTTP access (shared by MCP server and web clients)
- [ ] Web frontend (Next.js / SvelteKit)
- [ ] Mobile — Progressive Web App first; native (Flutter) if needed
- [ ] Minimal-cost self-hosted deployment on a single Hetzner CX22 VPS (~€4/month): Postgres + pgvector + embedding service + app on one machine, no managed DB required

### v0.7 — Improvements and optimisations
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
# DB_SSLMODE=require           # uncomment for hosted Postgres
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

## Quick start

```bash
# Ingest the corpus
poetry run ingest

# Query the RAG pipeline
poetry run rag 'rag.query=run'
RAG_QUERY='what does ephemeral mean?' poetry run rag

# Debug all three retrieval tools
poetry run debug-retriever 'debug.query=run'

# Run the MCP server
poetry run mcp-server

# Evaluate retrieval quality
poetry run eval
```

See the module READMEs for full usage and config options:

- [`linguaalayam/rag/`](linguaalayam/rag/README.md) — RAG pipeline, nodes, config, HuggingFace usage
- [`linguaalayam/mcp/`](linguaalayam/mcp/README.md) — MCP server tools, Claude Code and Claude Desktop setup
- [`linguaalayam/eval/`](linguaalayam/eval/README.md) — evaluation metrics, query categories, planned additions

---

## Testing

```bash
poetry run pytest

# Run a specific module
poetry run pytest tests/corpus
poetry run pytest tests/database
poetry run pytest tests/embeddings
```

---

## CI

**`ci.yml`** — runs on every push and pull request to `develop` and `main`:
- `ruff check` and `ruff format --check` (standalone ruff install, no Poetry)
- Full pytest suite (SQLite in-memory, no database needed)
- Venv cached by `poetry.lock` hash for fast runs

**`eval.yml`** — manual trigger only:
- Spins up a pgvector service container, runs migrations, seeds a minimal eval corpus fixture
- Runs `poetry run eval` with configurable `top_k` and `fuzzy_threshold` inputs

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
- **Anthropic Claude** (default LLM); **LiteLLM** adapter planned for v0.4 to support multiple providers
- **FastMCP** (`mcp` SDK) for the MCP server
- **Hydra** for configuration management
- **Alembic** for schema migrations (`migrations/`)
- **pytest** + **ruff** + **pre-commit** for testing and linting

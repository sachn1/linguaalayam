# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinguAalayam is a Malayalam lexical knowledge base and MCP server. It ingests three corpora — Olam (EN→ML), Datuk (ML→ML), and Ekkurup (EN→ML thesaurus) — into a local Postgres + pgvector database and exposes hybrid retrieval (exact headword, trigram fuzzy, HNSW semantic) through both a LangGraph RAG pipeline and an MCP server for Claude.

## Local database setup

```bash
docker run -d --name linguaalayam-pg \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  ankane/pgvector

# Create the database
docker exec -it linguaalayam-pg psql -U postgres -c "CREATE DATABASE linguaalayam;"
```

Copy `.env.example` to `.env` — DB values must match the Docker setup above. Then run migrations.

## Commands

```bash
# Setup
poetry install
poetry run pre-commit install
poetry run alembic upgrade head

# Ingest corpora
poetry run ingest                               # Full ingest (all corpora)
poetry run ingest corpus=debug                  # 50-entry test ingest, small batches
poetry run ingest embedding=multilingual_e5_large

# Test retrieval interactively
poetry run debug-retriever                      # Default query: "run"
poetry run debug-retriever --query "ഓടുക" --top-k 3 --source olam_enml

# RAG pipeline
poetry run rag 'rag.query=run'
RAG_QUERY='what does ephemeral mean?' poetry run rag
poetry run rag 'rag.query=run' llm=openai
poetry run rag 'rag.query=run' llm=nollm       # no API key needed

# Tests
poetry run pytest                               # All tests
poetry run pytest tests/corpus                  # Corpus parser tests only
poetry run pytest tests/database                # DB tests (SQLite in-memory, no Postgres needed)

# Lint / format
poetry run ruff check .
poetry run ruff format .
```

## Architecture

See [docs/architecture.md](docs/architecture.md) for full diagrams and module reference.

**Ingestion flow:**

```
TSV corpus files
  → corpus parsers (linguaalayam/corpus/)
  → EmbeddingService (linguaalayam/embeddings/)   # sentence-transformers → Vector(768)
  → VectorCheckpoint (linguaalayam/scripts/)       # JSONL fault-tolerance
  → batch_insert() (linguaalayam/database/)        # Postgres ON CONFLICT DO NOTHING
```

**RAG query flow:**

```
user query
  → understand_query (regex → LLMAdapter fallback)
  → DictionaryTools (exact / fuzzy / semantic)
  → CrossEncoderReranker (optional)
  → LLMAdapter.complete() or formatted candidates (nollm)
```

**MCP server:** tools (exact/fuzzy/semantic) + resource `dictionary://{headword}` → DictionaryTools → Postgres

### Key modules

| Module | Purpose |
|---|---|
| `linguaalayam/models/entries.py` | Entry types (`EnMlEntry`, `MlMlEntry`, `EkkurupEntry`), each with `to_embed_text()` |
| `linguaalayam/models/orm.py` | SQLAlchemy `DictionaryEntry` ORM — headword, embed_text, JSONB data, Vector(768) |
| `linguaalayam/corpus/base.py` | `parse_definition_tsv()` — shared 3-column TSV helper used by `enml.py` and `datuk.py` |
| `linguaalayam/corpus/` | One parser per corpus (`enml.py`, `datuk.py`, `ekkurup.py`), each exposes `parse()` |
| `linguaalayam/embeddings/service.py` | `EmbeddingService` wraps `paraphrase-multilingual-mpnet-base-v2`; exposes `batch_size` and `vector_size` |
| `linguaalayam/database/queries.py` | `batch_insert()`, `similarity_search()` (HNSW cosine), `get_ingested_headwords()` |
| `linguaalayam/llm/adapters/` | `LLMAdapter` ABC + `AnthropicAdapter`, `OpenAIAdapter`, `NoLLMAdapter` |
| `linguaalayam/rag/pipeline.py` | LangGraph graph: understand → retrieve → rerank? → synthesize |
| `linguaalayam/rag/tools.py` | `DictionaryTools` — exact, fuzzy, semantic lookup over a live DB session |
| `linguaalayam/mcp/server.py` | FastMCP server — three tools + `dictionary://{headword}` resource |
| `linguaalayam/scripts/ingest.py` | Ingestion entry point with checkpoint-based resumability |

### Configuration (Hydra)

Config lives in `config/` with override groups:
- `corpus`: `all` (full ingest) or `debug` (limit=50). Each source entry carries `parser._target_` pointing to its `parse` function — no hardcoded parser map in Python.
- `embedding`: `model` (multilingual-mpnet) or `multilingual_e5_large`
- `llm`: `anthropic` (default), `openai`, `nollm`
- `database`: `local` (default) or `supabase` (adds `sslmode=require`)
- `rag`: query, top_k, source, rerank flag, `reranker_model` (cross-encoder HuggingFace ID)

### Database schema

Table `dictionary_entries`: `source` + `headword` have a UNIQUE constraint (ON CONFLICT DO NOTHING). HNSW index on the embedding column (`m=16, ef_construction=64`, cosine distance).

## Adding a new corpus

1. Create a parser in `linguaalayam/corpus/` exposing a `parse(filepath: Path) -> list[Embeddable]` function.
   - If the format is a 3-column definition TSV (headword, POS, definition), use `parse_definition_tsv` from `corpus/base.py` — one-line body.
   - Otherwise implement parsing directly as in `ekkurup.py` (YAML).
2. Add a source entry to `config/corpus/all.yaml` and `config/corpus/debug.yaml` with `parser._target_` pointing to your `parse` function and `parser._partial_: true`. No Python code change needed in `ingest.py`.

## Adding a new LLM provider

1. Subclass `LLMAdapter` in `linguaalayam/llm/adapters/`.
2. Add a YAML config in `config/llm/` with `_target_` pointing to your class.

## Testing notes

Unit tests use an SQLite in-memory database via the `db_cfg` fixture — no running Postgres needed. The `dummy_service` fixture provides a mock `EmbeddingService` with 4-dimensional vectors for fast tests.

## Environment

Requires a `.env` file with: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`. Set `DB_SSLMODE=require` for hosted Postgres.

## Versioning

Schema: `major.minor.patch` (semantic versioning, `major_version_zero = true` until v1.0).

Trunk-based flow — all feature and fix branches target `master` directly via PR. The bump workflow runs automatically on every push to `master` and calls `cz bump` which reads conventional commits to determine the increment:

| Commit prefix | Bump |
|---|---|
| `fix:` | patch |
| `feat:` | minor |
| `feat!:` / `BREAKING CHANGE:` footer | major (minor while `major_version_zero = true`) |

To cut v1.0.0: set `major_version_zero = false` in `pyproject.toml`, then include a `feat!:` or `BREAKING CHANGE:` commit in the PR to `master`.

## Embedding models

The sentence-transformer and cross-encoder models download from HuggingFace on first use and cache to `~/.cache/huggingface`. Pre-warm the cache before the first `mcp-server` start:

```bash
python -c "
from sentence_transformers import SentenceTransformer, CrossEncoder
SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
CrossEncoder('cross-encoder/mmarco-mMiniLMv2-L12-H384-v1')
"
```

Baking models into a Docker image layer is planned for v0.6 when the REST API is containerised.

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

LinguAalayam is a Malayalam dictionary RAG pipeline — it ingests open-source Malayalam lexical corpora (~58,000 entries from the Olam EN→ML corpus) into a local Postgres+pgvector database and enables semantic search via sentence-transformer embeddings.

## Local database setup

```bash
docker run -d --name linguaalayam-pg \
  -e POSTGRES_PASSWORD=yourpassword \
  -p 5432:5432 \
  ankane/pgvector

# Create the database
docker exec -it linguaalayam-pg psql -U postgres -c "CREATE DATABASE linguaalayam;"
```

Copy `.env.example` to `.env` and fill in credentials, then run migrations.

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

# Tests
poetry run pytest                               # All tests
poetry run pytest tests/corpus                  # Corpus parser tests only
poetry run pytest tests/database               # DB tests (SQLite in-memory, no Supabase needed)

# Lint / format
poetry run ruff check .
poetry run ruff format .
```

## Architecture

**Data flow:**

```
TSV corpus files
  → corpus parsers (linguaalayam/corpus/)     # produce Embeddable entries
  → EmbeddingService (linguaalayam/embeddings/) # sentence-transformers → Vector(768)
  → VectorCheckpoint (linguaalayam/scripts/vector_checkpoint.py)  # JSONL fault-tolerance
  → batch_insert() (linguaalayam/database/queries.py)   # Postgres ON CONFLICT DO NOTHING
```

**Query flow:**

```
user query → EmbeddingService.encode_query() → similarity_search() (HNSW cosine) → ranked results
```

### Key modules

| Module | Purpose |
|---|---|
| `linguaalayam/models/entries.py` | Protocol-based entry types (`EnMlEntry`, `MlMlEntry`, `CrossLingualEntry`). Each implements `to_embed_text()`. |
| `linguaalayam/models/orm.py` | SQLAlchemy `DictionaryEntry` ORM — id, source, headword, embed_text, JSONB data, Vector(768) embedding. |
| `linguaalayam/corpus/` | One parser per corpus format (`enml.py`, `datuk.py`, `dravidian.py`). Each exposes a `parse()` function. |
| `linguaalayam/embeddings/service.py` | `EmbeddingService` wraps `paraphrase-multilingual-mpnet-base-v2`. Batch encodes entries or single queries. |
| `linguaalayam/database/queries.py` | `batch_insert()` (with ON CONFLICT), `similarity_search()` (HNSW cosine), `get_ingested_headwords()`. |
| `linguaalayam/rag/retriever.py` | `Retriever` class — combines embed + similarity search + result formatting. |
| `linguaalayam/scripts/ingest.py` | Main ingestion entry point. Checkpoint-based resumability: skips already-embedded entries on restart. |
| `linguaalayam/scripts/vector_checkpoint.py` | `VectorCheckpoint` — append-only JSONL file mapping headword → vector. Survives crashes mid-ingest. |

### Configuration (Hydra)

Config lives in `config/` with three override groups:
- `corpus`: `all` (full ingest, batch_size=512) or `debug` (limit=50, batch_size=10)
- `embedding`: `model` (multilingual-mpnet, batch_size=256) or `multilingual_e5_large`
- `database`: `local` (default, localhost postgres, no SSL) or `supabase` (adds `sslmode=require`)

### Database schema

Table `dictionary_entries`: `source` (corpus id) + `headword` have a UNIQUE constraint (ON CONFLICT DO NOTHING). HNSW index on the embedding column (`m=16, ef_construction=64`, cosine distance).

### Checkpoint files

`.checkpoints/` stores JSONL checkpoint files during ingest. Safe to delete after a successful ingest completes.

## Adding a new corpus

1. Create a parser in `linguaalayam/corpus/` that returns a list of objects implementing the `Embeddable` protocol (`source`, `headword`, `to_embed_text()`).
2. Register it in the `_PARSERS` dict in `linguaalayam/scripts/ingest.py`.
3. Add a Hydra corpus config under `config/corpus/`.

## Testing notes

Unit tests use an SQLite in-memory database via the `db_cfg` fixture — no running postgres needed. The `dummy_service` fixture provides a mock `EmbeddingService` with 4-dimensional vectors for fast tests.

## Environment

Requires a `.env` file with: `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`, `DB_NAME`. Set `DB_SSLMODE=require` for Supabase or other hosted postgres that requires SSL.

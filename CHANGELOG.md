## v0.3.0 (2026-05-07)

### Feat

- introduce mcp server into the project
- point alembic.ini to migrations directory, introduce naming convention for constraints or indices via alembic migration autogeneration

### Refactor

- update debugging script for retriever, remove legacy rudimentary retriever script
- rename alembic to migrations directory

### Ci

- add bump.yml workflow for sem-ver and add retroactive CHANGELOG

### Docs

- update and refactor README structure
- update README

### Test

- add and update tests

## v0.2.0 (2026-05-05)

### Feat

- add eval harness for rag
- migrate to local postgres, introduce langgraph pipeline for rag support with claude and hf, reranking and response synthesizer
- migrate to add pg_trgm for fuzzy search over headword
- first working version of linguaalayam that can ingest to supabase and retrieve top-k similar results
- add db migrations
- update ingest script and add a debug retriever script

### Refactor

- cleanup project with new project goals
- refactor data_reviewer to support database
- update database tables and adapt scripts

### Fix

- linter issues
- fix WordURL to WordUrl

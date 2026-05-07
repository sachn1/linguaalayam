## 0.2.0 (2026-05-05)

### Feat

- add eval harness for rag
- migrate to local postgres, introduce langgraph pipeline for rag support with claude and hf, reranking and response synthesizer with skills.md
- migrate to add pg_trgm for fuzzy search over headword
- first working version of linguaalayam that can ingest to supabase and retrieve top-k similar results
- add db migrations
- update ingest script and add a debug retriever script
- add train script, update crud and data reviewer script, remove datuk file
- adapt train_data_extractor for crud operation changes
- update crud operations
- add non-nullable word column to word definitions table, upgrade alembic
- add alembic for database migrations
- update wiktionary training data extractor
- update crud, url_scrapper, notebook
- update scripts
- remove data with postgres support
- add script for creating db tables
- update scripts
- add script to scrape samam data
- add streamlit for human-in-the-loop data creation, change data format to tab space
- add scripts to extract clean-data
- add data/raw files, scraper script
- add ml word urls to data/raw dir
- update files with more info
- update notebook
- add pyproject.toml and draft notebook
- add data

### Fix

- linter issues
- fix WordURL to WordUrl

### Refactor

- cleanup project with new project goals
- refactor data_reviewer to support database
- update database tables and adapt scripts

## v0.3.0 (2026-05-07)

### Feat

- point alembic.ini to migrations directory, introduce naming convention for constraints or indices via alembic migration autogeneration
- introduce mcp server into the project
- add eval harness for rag
- migrate to local postgres, introduce langgraph pipeline for rag support with claude and hf, reranking and response synthesizer with skills.md
- migrate to add pg_trgm for fuzzy search over headword
- first working version of linguaalayam that can ingest to supabase and retrieve top-k similar results
- add db migrations
- update ingest script and add a debug retriever script
- add train script, update crud and data reviewer script, remove datuk file
- adapt train_data_extractor for crud operation changes
- update crud operations
- add non-nullable word column to word definitions table, upgrade alembic
- add alembic for database migrations
- update wiktionary training data extractor
- update crud, url_scrapper, notebook
- update scripts
- remove data with postgres support
- add script for creating db tables
- update scripts
- add script to scrape samam data
- add streamlit for human-in-the-loop data creation, change data format to tab space
- add scripts to extract clean-data
- add data/raw files, scraper script
- add ml word urls to data/raw dir
- update files with more info
- update notebook
- add pyproject.toml and draft notebook
- add data

### Fix

- linter issues
- fix WordURL to WordUrl

### Refactor

- rename alembic to migrations directory
- update debugging script for retriever, remove legacy rudimentary retriever script
- cleanup project with new project goals
- refactor data_reviewer to support database
- update database tables and adapt scripts

## v2.15.0 (2026-10-19)

### Fix

- scope citation quote verification to the specific cited headword's own entry

## v2.14.0 (2026-10-19)

## v2.13.2 (2026-10-13)

### Feat

- clarify mic/language picker and flag low-confidence voice transcripts
- nudge AI decomposition for 2+ word queries even with a confident literal match
- ground AI Answer citations against real dictionary text, split web.py into a modular package
- phrase decomposition fallback for AI Answer, with a debug trace panel

### Fix

- address code review — stale MCP doc, fragile assert in LazyEmbeddingService
- deploy workflow was pinning to a one-release-stale commit
- decompose sentence-length queries even when one word resolves confidently
- recalibrate stale pg_trgm-era fuzzy threshold defaults to edit-distance scale

### Perf

- lazy-import heavy ML deps and background-load the embedding model
- lazy-import langchain_anthropic to cut cold-start cost

## v2.13.1 (2026-10-13)

### Fix

- address code review — format, stale comment, doc duplication, test fixture
- disable unreliable Marian translation by default, hide its picker options
- run fuzzy lookup on every query, retire semantic_lookup from web search
- drop unused pg_trgm extension, index, and dead fuzzy_search()

## v2.13.0 (2026-10-12)

### Feat

- fuzzy matching tries mlmorph lemma first, then edit distance over trigram

## v2.12.3 (2026-10-02)

### Fix

- fetch the gitignored GeoIP database from GCS before building in CI

## v2.12.2 (2026-10-02)

### Fix

- build via docker buildx instead of gcloud builds submit

## v2.12.1 (2026-10-02)

### Fix

- set explicit project_id on the CD workflow's WIF auth step
- grant linguaalayam-cd the IAM roles it needs to submit a Cloud Build

## v2.12.0 (2026-10-02)

### Feat

- add automated build/migrate/deploy pipeline for Cloud Run
- add a write-capable Cloud Run deploy identity, scoped to master only
- scroll long tables within their own card instead of stretching the page
- show per-search-term location, not just country, in Top queries
- add one-off script to backfill city/region on old request_log rows
- restore dashboard visibility into in-app feature usage
- add 30-day and 365-day windows to the analytics dashboard
- resolve client city/region/country via local GeoIP instead of Cloudflare headers
- add terraform safe-apply workflow, RUNBOOK, and a read-only CI plan-review workflow via Workload Identity Federation
- route Cloud Run to Hetzner Postgres via Cloud NAT static IP, bypassing Cloudflare's proxied hostname

### Fix

- remove DB_SSLMODE from the migration job — Hetzner Postgres has no SSL
- bring the two live domain mappings under Terraform management
- wrap long table cells instead of overflowing the dashboard layout
- scope geoip backfill to route types a dashboard view actually shows
- restore feature-event logging broken by the GeoIP change
- stop blanket-excluding data/ from Cloud Build uploads
- correct down_revision for the city/region migration
- restore deletion_protection on Cloud Run service
- add DB connect_timeout so an unreachable host fails fast instead of hanging 5 minutes

## v2.11.0 (2026-09-13)

### Feat

- guard Marian translation against a stale input-language flag via langdetect
- add AI Answer toggle with cost-aware nudging, sidebar settings, and smarter query-understanding regex fallback
- add TogetherAI (Qwen) LLM adapter as the web app's server-side AI Answer default, and dedupe adapter internals into a shared LangChainAdapter base

### Fix

- restrict readme-drift to backtick symbol references to avoid plain-text false positives, and bump to v3.2.0

### Refactor

- rework analytics dashboard to show per-query country/client/timestamp breakdowns, restricted to real search traffic

## v2.10.0 (2026-07-23)

### Feat

- track per-tool MCP usage; fix event-loop-blocking analytics writes and a tool-call crash risk
- show top user agents and split static assets out of the 'other' route bucket

### Fix

- lowercase Manglish input before Varnam to avoid its capital-letter doubling convention

## v2.9.1 (2026-07-23)

### Fix

- pass ADMIN_USER/ADMIN_PASSWORD through to the app container

## v2.9.0 (2026-07-23)

### Feat

- add voice search language picker with first-time onboarding modal
- add traffic analytics with admin dashboard and click tracking
- add lemma-aware fuzzy matching via mlmorph root lookup
- add jayasree npm for handwriting feature
- remove not contribution worthy features from the UI but keep api endpoint active, cleanup UI, add manglish support with varnam

### Fix

- validate Varnam candidates against real dictionary entries, suggest Malayalam readings for ambiguous words

## v2.8.0 (2026-06-24)

### Feat

- add sayahnam data handling support, refactor workflow

### Refactor

- introduce new deployment strategy, add more linter restrictions
- minor cleanups

## v2.7.3 (2026-06-11)

### Fix

- ui layout for small screens

## v2.7.2 (2026-06-09)

### Fix

- cosmetic changes, fix in the commit scope for intentional patch versioning

## v2.7.1 (2026-06-08)

### Fix

- issues with morphology parsing and display

## v2.7.0 (2026-06-07)

### Feat

- voice search with EN/ML toggle, mobile-responsive header, corpus attribution in footer and settings
- swap ml2en for romanisation; add mlmorph tags; fix datuk and ekkurup romanisation

### Fix

- upgrade service worker to v2 with cache-first static assets and offline page fallback

## v2.6.0 (2026-06-04)

### Feat

- add /privacy page for Play Store compliance

## v2.5.0 (2026-06-04)

### Feat

- v2.5 Android TWA — PWA icons, assetlinks endpoint, Bubblewrap project

### Fix

- unignore static/manifest.json in .gitignore
- MCP OAuth root proxy, OIDC discovery, session manager lifespan

## v2.4.1 (2026-06-04)

### Fix

- mcp server issues

## v2.4.0 (2026-06-04)

### Feat

- ux updates
- ux updates

### Fix

- test

## v2.3.5 (2026-06-03)

### Fix

- disable FastMCP DNS rebinding protection and add OAuth discovery endpoints at domain root

## v2.3.4 (2026-06-03)

### Fix

- linter issues
- disable FastMCP DNS rebinding protection, proxy OAuth discovery to root

## v2.3.3 (2026-06-03)

### Fix

- proxy OAuth discovery to domain root so Claude.ai can authenticate against /mcp

## v2.3.2 (2026-06-03)

### Fix

- add MCP_ISSUER_URL to docker-compose.yml

## v2.3.1 (2026-06-03)

### Fix

- set resource_server_url=None to avoid broken RFC 9728 route under sub-path mount

## v2.3.0 (2026-06-03)

### Feat

- fix: register web router before MCP mount; update roadmap for v2.3
- OAuth 2.0 passthrough provider for Claude.ai browser MCP connector
- add one-click MCP setup page at /mcp/setup
- add elephant logo, transparent PNG, update PWA icons

## v2.2.0 (2026-06-02)

### Feat

- smart search routing, Manglish fallback, and corpus-derived eval harness
- register romanise_ml Jinja2 filter, add i18n JS, data-i18n attrs on search inputs, help text, toggle buttons with tooltip
- add English & Malayalam locale bundle (2*35 i18n keys)
- add malayalam_to_roman transliteration helper (ISO 15919)

### Fix

- increase test coverage, linting errors

## v2.1.0 (2026-05-31)

### Feat

- add etymology hint to search page; restore English tab title
- Malayalam/English hybrid title and README header with etymology
- intent-based source filter (EN→ML, Thesaurus, Malayalam word)

## v2.0.3 (2026-05-31)

### Fix

- use --extra-index-url for pytorch-cpu so sentence-transformers resolves from PyPI

## v2.0.2 (2026-05-31)

### Fix

- use heredoc in Dockerfile.base to avoid FROM parse error

## v2.0.1 (2026-05-31)

### Fix

- use git reset --hard in deploy script to handle force pushes

## v2.0.0 (2026-05-31)

### Fix

- set CPU-only PyTorch in pyproject.toml, split into base image and ci to avoid rebuild of full image always

## v1.0.0 (2026-05-31)

### BREAKING CHANGE

- MCP clients must update config from uvx-based local
install to URL-based hosted server: { "url": "https://linguaalayam.org/mcp" }
The mcp-server-http script is removed.

### Feat

- promote to v1.0 — hosted MCP, stable REST API, CI/CD deploy
- settings sidebar, structured results, live filter refresh
- mount remote MCP server at /mcp and harden REST API
- add icons to footer links
- add github link to webpage
- containerization
- pwa manifest and service worker
- add app, web, templates, byok, query understanding and branding
- add web app support for the application
- add REST support and endpoints for the application

### Fix

- fail-fast DB_PASSWORD in db service, add Windows Credential Manager notes to env example
- align Docker to Python 3.11, fix package install, add app healthcheck
- copy README.md and use --no-root for package install in Docker

## v0.5.0-rc.0 (2026-05-30)

### Feat

- ingest new data corpus and update code accordingly, remove deadcode

### Fix

- make linting step thinner in ci
- update poetry lock

## v0.4.0 (2026-05-09)

### Feat

- add mcp resource
- introduce adaptor pattern to use any LLM or No LLM for RAG

### Fix

- linter issues

## v0.3.1 (2026-05-07)

### Fix

- changelog, bump ci, test coverage

## v0.3.0 (2026-05-07)

### Feat

- point alembic.ini to migrations directory, introduce naming convention for constraints or indices via alembic migration autogeneration
- introduce mcp server into the project

### Refactor

- rename alembic to migrations directory
- update debugging script for retriever, remove legacy rudimentary retriever script

## v0.2.0 (2026-05-04)

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

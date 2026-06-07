<p align="center">
  <img src="linguaalayam/static/logo.svg" alt="lingua·ആലയം" width="440" />
</p>

> ഏതു വാക്കും അറിയൂ — Every word, explained.
>
> *From Latin "lingua" (language) and Malayalam "ആലയം" (abode) — a home for words.*

**[linguaalayam.org](https://linguaalayam.org)** · [API docs](https://linguaalayam.org/docs) · [MCP endpoint](https://linguaalayam.org/mcp)

lingua·ആലയം is an open-source Malayalam lexical knowledge base and AI integration layer. It ingests three corpora — **Olam** (English→Malayalam), **Datuk** (Malayalam→Malayalam), and **Ekkurup** (English→Malayalam thesaurus) — into a Postgres + pgvector database and enables hybrid retrieval: exact headword, trigram fuzzy, and HNSW semantic search. A LangGraph RAG pipeline synthesises natural-language answers through a configurable LLM adapter (Anthropic, OpenAI, or no LLM). The retrieval layer is exposed as a hosted MCP server — any MCP-compatible AI client can use it with just a URL.

The web UI at [linguaalayam.org](https://linguaalayam.org) supports English and Malayalam interface languages, romanised output alongside Malayalam definitions (toggle with the **A ↔ അ** button), voice input via the mic button (Chrome, Edge, Android — follows the EN/ML locale toggle; hidden on Firefox which does not support the Web Speech API), intent-based corpus selection, and Manglish input with automatic transliteration and semantic fallback.

> Built with the assistance of [Claude](https://claude.ai) (Anthropic).

---

## REST API

The hosted API is available at `https://linguaalayam.org`. No API key required for dictionary lookup.

```
GET /lookup/exact?query=run&source=olam_enml
GET /lookup/fuzzy?query=run&top_k=5
GET /lookup/semantic?query=ഓടുക&top_k=5
```

Full OpenAPI docs: [linguaalayam.org/docs](https://linguaalayam.org/docs)

---

## MCP setup (Claude Code, Claude Desktop, Cursor, Windsurf, Cline, and more)

The MCP server is hosted at `linguaalayam.org/mcp`. Three tools: `exact_lookup`, `fuzzy_lookup`, `semantic_lookup`. Works with any LLM backend. OAuth is automatic (RFC 7591 + PKCE, no login, no API key) — the URL alone is enough.

See [linguaalayam/mcp/README.md](linguaalayam/mcp/README.md) for the JSON snippet, client-specific config file paths (Claude Desktop, Cursor, Windsurf, Cline, Continue), and self-hosted setup.

---

## RAG pipeline

```bash
poetry run rag 'rag.query=ephemeral'
RAG_QUERY='what does pastoral mean?' poetry run rag
poetry run rag 'rag.query=run' llm=nollm    # no API key needed
poetry run rag 'rag.query=run' llm=openai   # switch provider
```

See [linguaalayam/rag/README.md](linguaalayam/rag/README.md) for pipeline details and config options.

---

## Quick start

```bash
poetry install
cp .env.example .env        # see docs/setup.md
poetry run alembic upgrade head
poetry run ingest
```

See [docs/setup.md](docs/setup.md) for database setup, environment variables, and data download.

---

## Docs

- [User guide](docs/user-guide.md) — search modes, corpora, AI synthesis explained
- [Architecture](docs/architecture.md) — system flow, module reference, tech stack
- [Roadmap](docs/roadmap.md) — versioned goals
- [Setup](docs/setup.md) — database, environment, migrations, corpora
- [API docs](https://linguaalayam.org/docs) — live OpenAPI / Swagger UI
- [MCP server](linguaalayam/mcp/README.md) — tools, resources, testing
- [RAG pipeline](linguaalayam/rag/README.md) — nodes, config, debug tool
- [Evaluation](linguaalayam/eval/README.md) — metrics, query categories

---

## Testing

```bash
poetry run pytest
poetry run pytest tests/corpus      # corpus parsers
poetry run pytest tests/database    # DB layer (SQLite, no Postgres needed)
```

---

## Data sources

Three corpora, all under the Open Database License (ODbL). See [DATA_SOURCES.md](DATA_SOURCES.md) for full attribution and licence terms.

| Corpus | Description | Source |
|---|---|---|
| Olam EN→ML | English–Malayalam dictionary | [olam.in/p/open](https://olam.in/p/open) |
| Datuk | Malayalam–Malayalam dictionary | [olam.in/p/open/datuk](https://olam.in/p/open/datuk) |
| Ekkurup | English–Malayalam thesaurus | [olam.in/p/open/ekkurup](https://olam.in/p/open/ekkurup) |

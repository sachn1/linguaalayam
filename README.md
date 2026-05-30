# LinguAalayam

LinguAalayam is an open-source Malayalam lexical knowledge base and AI integration layer. It ingests three Malayalam corpora — **Olam** (English→Malayalam), **Datuk** (Malayalam→Malayalam), and **Ekkurup** (English→Malayalam thesaurus) — into a local Postgres + pgvector database and enables hybrid retrieval: exact headword, trigram fuzzy, and HNSW semantic search. A LangGraph RAG pipeline synthesises natural-language answers through a configurable LLM adapter (Anthropic, OpenAI, or no LLM). The retrieval layer is also exposed as an MCP server for Claude Code and Claude Desktop, with both callable tools and URI-addressed dictionary resources.

> Built with the assistance of [Claude](https://claude.ai) (Anthropic).

---

## MCP setup (Claude Code / Claude Desktop)

Add to `.mcp.json` (Claude Code) or your Claude Desktop config:

```json
{
  "mcpServers": {
    "linguaalayam": {
      "command": "poetry",
      "args": ["run", "mcp-server"],
      "cwd": "/path/to/LinguAalayam"
    }
  }
}
```

Three tools: `exact_lookup`, `fuzzy_lookup`, `semantic_lookup`.
One resource: `dictionary://{headword}`.

See [linguaalayam/mcp/README.md](linguaalayam/mcp/README.md) for the Inspector, notebook testing, and Claude Desktop config.

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

- [Architecture](docs/architecture.md) — system flow, module reference, tech stack
- [Roadmap](docs/roadmap.md) — versioned goals
- [Setup](docs/setup.md) — database, environment, migrations, corpora
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

All corpora are sourced from [olam.in/p/open](https://olam.in/p/open), which is the open-data initiative by the [Olam](https://olam.in) project — a free Malayalam dictionary. Dataset citations and licence information are available on that page.

| Corpus | Description | Source |
|---|---|---|
| Olam EN→ML | English–Malayalam dictionary | [olam.in/p/open](https://olam.in/p/open) |
| Datuk | Malayalam–Malayalam dictionary | [olam.in/p/open/datuk](https://olam.in/p/open/datuk) |
| Ekkurup | English–Malayalam thesaurus | [olam.in/p/open/ekkurup](https://olam.in/p/open/ekkurup) |

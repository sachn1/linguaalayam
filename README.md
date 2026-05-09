# LinguAalayam

LinguAalayam is an open-source Malayalam lexical knowledge base and AI integration layer. It ingests the Olam English–Malayalam corpus into a local Postgres + pgvector database and enables hybrid retrieval — exact headword, trigram fuzzy, and HNSW semantic search. A LangGraph RAG pipeline synthesises natural-language answers through a configurable LLM adapter (Anthropic, OpenAI, or no LLM). The retrieval layer is also exposed as an MCP server for Claude Code and Claude Desktop, with both callable tools and URI-addressed dictionary resources. Support for additional Malayalam corpora (ML→ML, cross-Dravidian) is planned for v0.5.

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

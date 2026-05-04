# MCP Server

LinguAalayam exposes its three retrieval tools as an [MCP](https://modelcontextprotocol.io) server. The server loads the embedding model (~500 MB) once at startup and keeps the DB connection pool alive for the session.

The server also auto-starts the local Postgres Docker container (`linguaalayam-pg`) if it is stopped — so opening Claude Code or Claude Desktop is enough, no manual `docker start` required.

## Tools

| Tool | Description |
|---|---|
| `exact_lookup(word, source?)` | Case-insensitive exact headword match |
| `fuzzy_lookup(query, threshold?, top_k?, source?)` | Trigram similarity search via pg_trgm |
| `semantic_lookup(query, top_k?, source?)` | Embedding cosine search via HNSW |

All tools accept an optional `source` parameter to filter by corpus (e.g. `olam_enml`). Omit it to search across all ingested corpora.

The server instructions tell the LLM to try `exact_lookup` first, fall back to `fuzzy_lookup` for approximate matches, and use `semantic_lookup` for meaning-based queries.

## Testing

### 1. MCP Inspector (interactive web UI)

The `mcp` CLI ships a `dev` command that starts an interactive browser UI — call each tool and inspect raw inputs/outputs without Claude involved.

**Requires Node.js.** Install it once with [fnm](https://github.com/Schniz/fnm) (works on Linux, macOS, and Windows/WSL):

```bash
curl -fsSL https://fnm.vercel.app/install | bash
fnm install --lts
```

Then run the Inspector:

```bash
poetry run mcp dev linguaalayam/mcp/server.py
```

This opens `localhost:6274` in the browser. The Inspector defaults to launching the server via `uv`, which doesn't use the Poetry virtualenv. In the connection form, override the command before clicking **Connect**:

| Field | Value |
|---|---|
| **Command** | `poetry` |
| **Arguments** | `run mcp-server` |

Alternatively, point directly at the venv Python to bypass Poetry entirely:

| Field | Value |
|---|---|
| **Command** | `.venv/bin/python` |
| **Arguments** | `-m linguaalayam.mcp.server` |

The first connection attempt prints:

```
Use pytorch device_name: cuda
Load pretrained SentenceTransformer: ...
```

This is normal — the embedding model is loading. Wait ~30 seconds for it to finish, then the Inspector becomes interactive.

### 2. Python notebook (direct function calls)

[`notebooks/mcp_testing.ipynb`](../../notebooks/mcp_testing.ipynb) initialises `_tools` directly and calls each tool function without the MCP protocol layer — fastest way to iterate on output format or debug retrieval behaviour.

```python
from linguaalayam.mcp import server
server._ensure_docker_db()
server._tools = server._init_tools()

print(server.exact_lookup("run"))
print(server.fuzzy_lookup("runing", threshold=0.2))
print(server.semantic_lookup("to move quickly on foot", top_k=5))
```

### 3. Claude Code (end-to-end)

`.mcp.json` is included in the project root. When you open this repository in Claude Code, the `linguaalayam` server is registered automatically. Ask Claude:

> *"Look up the word 'ephemeral' in the Malayalam dictionary"*

Claude Code will select the appropriate tool, show the raw result, and synthesise an answer.

## Claude Desktop

Add the following to your Claude Desktop config file:

| Platform | Path |
|---|---|
| Linux | `~/.config/Claude/claude_desktop_config.json` |
| macOS | `~/Library/Application Support/Claude/claude_desktop_config.json` |
| Windows | `%APPDATA%\Claude\claude_desktop_config.json` |

```json
{
  "mcpServers": {
    "linguaalayam": {
      "command": "poetry",
      "args": ["--directory", "/absolute/path/to/LinguAalayam", "run", "mcp-server"]
    }
  }
}
```

Replace `/absolute/path/to/LinguAalayam` with the actual path on your machine. Claude Desktop starts the server on launch and restarts it automatically if it crashes.

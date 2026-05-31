# MCP Server

LinguAalayam exposes its three retrieval tools as an [MCP](https://modelcontextprotocol.io) server directly from the hosted app — no local install, no Python, no database setup required.

The MCP endpoint is live at `https://linguaalayam.org/mcp`.

---

## Tools

| Tool | Description |
|---|---|
| `exact_lookup(word, source?)` | Case-insensitive exact headword match |
| `fuzzy_lookup(query, threshold?, top_k?, source?)` | Trigram similarity search via pg_trgm |
| `semantic_lookup(query, top_k?, source?)` | Embedding cosine search via HNSW |

All tools accept an optional `source` parameter to filter by corpus (`olam_enml`, `datuk`, `ekkurup`). Omit to search all corpora.

---

## Client setup

Add this block to your MCP client config. No command, no package, no local database.

```json
{
  "mcpServers": {
    "linguaalayam": {
      "url": "https://linguaalayam.org/mcp"
    }
  }
}
```

Where to put the file:

| Client | Config file | Notes |
|---|---|---|
| **Claude Code** | `.mcp.json` in your project root | Picked up automatically — no restart |
| **Claude Desktop** (macOS) | `~/Library/Application Support/Claude/claude_desktop_config.json` | Restart Claude Desktop after saving |
| **Claude Desktop** (Windows) | `%APPDATA%\Claude\claude_desktop_config.json` | Restart Claude Desktop after saving |
| **Claude Desktop** (Linux) | `~/.config/Claude/claude_desktop_config.json` | Restart Claude Desktop after saving |
| **Cursor** (global) | `~/.cursor/mcp.json` | Reload Window (Cmd/Ctrl+Shift+P) after saving |
| **Cursor** (project) | `.cursor/mcp.json` in project root | Reload Window after saving |
| **Windsurf** | `~/.codeium/windsurf/mcp_config.json` | Restart Windsurf; tools appear in Cascade panel |

---

### Cline (VS Code)

Cline uses a different settings key. Open VS Code settings (`Cmd/Ctrl+,`), search for `Cline MCP`, click **Edit in settings.json**:

```json
{
  "cline.mcpServers": {
    "linguaalayam": {
      "url": "https://linguaalayam.org/mcp"
    }
  }
}
```

Or use the Cline sidebar → MCP Servers tab → Add Server → paste the URL.

---

### Continue (VS Code / JetBrains)

Continue uses YAML. In `~/.continue/config.yaml`:

```yaml
mcpServers:
  - name: linguaalayam
    url: https://linguaalayam.org/mcp
```

---

## A note on LLM providers

The MCP server is LLM-agnostic — it returns plain text from the dictionary. Any LLM backend your client uses (Claude, GPT-4o, Gemini, Mistral, Llama, etc.) can call the tools and synthesise answers from the results. You do not need an Anthropic API key to use these tools.

---

## Client not listed?

If your IDE or MCP client is not covered above, [open an issue](https://github.com/sachn1/linguaalayam/issues/new) and mention which client you are using. Most clients that support MCP use the same JSON format — only the config file path differs.

---

## Self-hosted instance

Running the full stack locally (see [docs/setup.md](../../docs/setup.md))? The MCP server is already mounted at `/mcp` on the local app. Point your client at:

```json
{
  "mcpServers": {
    "linguaalayam": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

No separate MCP process needed — it runs inside the same FastAPI app.

---

## Testing

### MCP Inspector (interactive web UI)

Requires Node.js (install with [fnm](https://github.com/Schniz/fnm)):

```bash
poetry run mcp dev linguaalayam/mcp/server.py
```

Opens `localhost:6274`. In the connection form, override the command:

| Field | Value |
|---|---|
| **Command** | `poetry` |
| **Arguments** | `run mcp-server` |

### Python notebook

[`notebooks/mcp_testing.ipynb`](../../notebooks/mcp_testing.ipynb) calls tool functions directly without the MCP protocol layer — fastest way to iterate on output format or debug retrieval.

```python
from linguaalayam.mcp import server
server._ensure_docker_db()
server._tools = server._init_tools()

print(server.exact_lookup("run"))
print(server.fuzzy_lookup("runing", threshold=0.2))
print(server.semantic_lookup("to move quickly on foot", top_k=5))
```

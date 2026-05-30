# Roadmap

### v0.2 — RAG ready
- [x] Query preprocessing — extract target word from natural language queries
- [x] Hybrid search — exact, fuzzy, and semantic retrieval
- [x] Response synthesis — LLM answer from top-k retrieved entries
- [x] Evaluation harness — retrieval metrics on a labeled query set

### v0.3 — MCP server
- [x] MCP server with three tools: `exact_lookup`, `fuzzy_lookup`, `semantic_lookup`
- [x] Claude Code integration via `.mcp.json` project config
- [x] Claude Desktop setup instructions

### v0.4 — LLM adapter + MCP resources
- [x] `LLMAdapter` ABC with `AnthropicAdapter`, `OpenAIAdapter`, `NoLLMAdapter`
- [x] Provider selected via Hydra `_target_` — adding a new provider requires only a subclass and a YAML file
- [x] `NoLLMAdapter` — no API key needed; synthesis returns formatted reranker output
- [x] Remove HuggingFace text-generation; LLM is always API-backed or absent
- [x] MCP resource `dictionary://{headword}` alongside the existing tools

### v0.5 — Additional corpora + code quality
- [x] **Datuk** — ML→ML corpus (Malayalam headwords with Malayalam definitions)
- [x] **Ekkurup** — EN→ML thesaurus (synset entries with grouped EN synonyms and ML translations)
- [x] Per-corpus filtering in retrieval via `source` parameter on all three tools
- [x] Hydra-driven corpus parsers — adding a corpus requires only a YAML config entry, no Python change
- [x] Code quality sweep — dead code removed, encapsulation fixed, silent failures logged

### v0.6 — REST API and self-hosting
- [ ] Thin FastAPI layer over `DictionaryTools` for HTTP access
- [ ] Web frontend (Next.js / SvelteKit)
- [ ] Mobile — Progressive Web App first; native (Flutter) if needed
- [ ] Minimal-cost self-hosted deployment on a Hetzner CX22 VPS (~€4/month)
- [ ] Docker image with pre-baked embedding and reranker model weights

### v1.0 — Stable release (post v0.6)
- [ ] Promote to stable after v0.6 ships and REST API is proven in production

### v1.x — Improvements and optimisations
- [ ] Embedding model evaluation — compare `multilingual-mpnet` vs `multilingual-e5-large`
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — retrieval latency and top-k quality metrics

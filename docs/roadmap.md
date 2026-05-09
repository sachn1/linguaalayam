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

### v0.5 — Additional corpora
- [ ] **Datuk** — ML→ML corpus (~83,000 Malayalam headwords with Malayalam definitions)
- [ ] **Dravidian comparative** — cross-lingual corpus with Kannada, Tamil, and Telugu equivalents
- [ ] **EK Kurup** — EN→ML thesaurus with 900,000+ synset entries (requires separate chunking strategy)
- [ ] Per-corpus filtering in retrieval

### v0.6 — Frontend and self-hosting
- [ ] Thin FastAPI layer over `DictionaryTools` for HTTP access
- [ ] Web frontend (Next.js / SvelteKit)
- [ ] Mobile — Progressive Web App first; native (Flutter) if needed
- [ ] Minimal-cost self-hosted deployment on a Hetzner CX22 VPS (~€4/month)

### v0.7 — Improvements and optimisations
- [ ] Embedding model evaluation — compare `multilingual-mpnet` vs `multilingual-e5-large`
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — retrieval latency and top-k quality metrics

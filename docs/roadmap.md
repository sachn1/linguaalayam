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

### v0.6 — REST API, web UI, and mobile app
- [ ] Thin FastAPI layer over `DictionaryTools` for HTTP access
- [ ] Web UI — HTMX + Jinja2 served from FastAPI; search page for SEO, link sharing, and desktop users
- [ ] Mobile — Flutter app (Android + iOS); calls the same FastAPI endpoints; Android / Play Store first
- [ ] Self-hosted deployment on a Hetzner CX32 VPS (~€6/month) — CX32 (8 GB RAM) required; embedding model alone is 1.1 GB, reranker ~400 MB, leaving safe headroom for Postgres + app
- [ ] Docker image with pre-baked embedding and reranker model weights
- [ ] `NoLLMAdapter` as default for the web app — core dictionary lookup needs no LLM or API key
- [ ] Bring-your-own-key LLM synthesis (Anthropic / OpenAI) — optional power-user feature via settings UI

### v1.0 — Stable release (post v0.6)
- [ ] Promote to stable after v0.6 ships and REST API is proven in production

### v1.x — Improvements and optimisations
- [ ] Embedding model evaluation — compare `multilingual-mpnet` vs `multilingual-e5-large`
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — retrieval latency and top-k quality metrics

### v2.0 — On-device AI synthesis (in-app purchase)
- [ ] Generate synthetic (query → answer) training pairs from existing corpus (headword + POS + definition + synonyms)
- [ ] Fine-tune a small multilingual model (Gemma 2B or Qwen 2.5 1.5B) on Malayalam dictionary Q&A
- [ ] Quality eval harness before shipping — answer quality metrics (BLEU + human eval on Malayalam output); do not ship without passing eval
- [ ] Serverless inference (Modal or RunPod) — pay-per-request, no idle GPU cost
- [ ] AI synthesis as in-app purchase — core app stays free, premium tier unlocks prose answers at lower price point than user-managed API keys

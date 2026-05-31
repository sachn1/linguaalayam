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

### v2.0 — REST API, hosted MCP, and stable release
- [x] Thin FastAPI layer over `DictionaryTools` — `/lookup/exact`, `/lookup/fuzzy`, `/lookup/semantic`
- [x] Web UI — HTMX + Jinja2 served from FastAPI; settings sidebar, structured POS-grouped results, live filter refresh
- [x] Hosted MCP server at `/mcp` — zero-config for AI clients (`{ "url": "https://linguaalayam.org/mcp" }`)
- [x] Bring-your-own-key LLM synthesis (Anthropic / OpenAI) — key stored in browser localStorage, injected as request header, never persisted server-side
- [x] Self-hosted deployment on Hetzner CX33 (Nuremberg, €7.72/month) — Docker Compose, nginx reverse proxy
- [x] Domain and HTTPS — [linguaalayam.org](https://linguaalayam.org) live with Let's Encrypt cert
- [x] CI/CD — GitHub Actions deploy to VPS on `bump:` commit via forced-command SSH key
- [x] User guide, MCP client setup guide (Claude Code, Claude Desktop, Cursor, Windsurf, Cline, Continue)
- [x] CPU-only PyTorch in Docker — explicit `pytorch-cpu` source, no CUDA packages on VPS

### v2.1 — Diaspora, accessibility, and i18n
- [x] **Intent-based source filter** — corpus dropdown replaced with human-readable intents (EN → Malayalam, Thesaurus, Malayalam word); backend unchanged
- [ ] **UI language toggle** — English / Malayalam interface labels; JSON message bundles, no page reload
- [ ] **Manglish input** — blocked on embedding eval (see ⚠ Critical below); if LaBSE bridges romanised → Malayalam semantically, smart search handles it without a separate transliteration layer; build only if eval shows the gap remains
- [ ] **Romanised output** — Malayalam definitions returned with Roman transliteration alongside for users who cannot read the script
- [ ] **PWA baseline** — `manifest.json` + service worker; enables "Add to Home Screen" on Android/iOS and is prerequisite for Play Store TWA


### ⚠ Critical: Malayalam embedding quality (target v2.2)
Malayalam semantic search quality is untested. `paraphrase-multilingual-mpnet-base-v2` was trained on predominantly European and high-resource languages — Malayalam coverage is unknown and likely poor. Symptoms: semantically similar Malayalam words may not retrieve each other; cross-lingual EN→ML semantic search may be unreliable.

- [ ] **Eval harness on Malayalam queries** — add Malayalam-specific labeled query set to `eval/`; run retrieval metrics (MRR, recall@k) separately for EN and ML headwords
- [ ] **Embedding model comparison** — benchmark `multilingual-mpnet` vs `multilingual-e5-large` vs `LaBSE` on the Malayalam eval set; LaBSE has stronger Indic language coverage
- [ ] **Replace model if needed** — if LaBSE or e5-large significantly outperforms, swap in via Hydra config; no schema change required (both produce 768-d vectors)
- [ ] **Re-ingest if model changes** — embeddings are model-specific; a model swap requires full re-ingest; budget ~2h on CPU

Do not ship Manglish input or any Malayalam semantic feature without passing this eval first.

### v2.2 — Multilingual query and broader i18n
- [ ] **Multilingual query input** — detect non-EN/ML query language, translate to EN via LLM adapter, show detected translation in grey below search box; lookup proceeds on translated query
- [ ] **i18n foundation** — locale JSON bundles for UI strings; architecture supports adding community-translated locales beyond EN/ML

### v3.0 — Android app
- [ ] **Android TWA via PWABuilder** — wrap the existing PWA for Play Store; no separate codebase; requires icons, Play Developer account, and `assetlinks.json` on domain
- [ ] **iOS** — evaluate PWABuilder or thin WKWebView wrapper; ship after Android is stable

### v3.1 — Word of the Day
- [ ] **Word of the Day** — daily featured word, filtered by frequency list to exclude common words (top 5k excluded); alternates EN/ML by default
- [ ] **User preference** — app settings: EN only / ML only / alternate; stored in `localStorage`
- [ ] **Push notifications** — service worker push for word-of-the-day on Android (requires v2.1 PWA baseline)

### v3.2 — On-device AI synthesis (in-app purchase)
- [ ] Generate synthetic (query → answer) training pairs from existing corpus (headword + POS + definition + synonyms)
- [ ] Fine-tune a small multilingual model (Gemma 2B or Qwen 2.5 1.5B) on Malayalam dictionary Q&A
- [ ] Quality eval harness before shipping — answer quality metrics (BLEU + human eval on Malayalam output); do not ship without passing eval
- [ ] Serverless inference (Modal or RunPod) — pay-per-request, no idle GPU cost
- [ ] AI synthesis as in-app purchase — core app stays free, premium tier unlocks prose answers at lower price point than user-managed API keys


### Backlog
- [ ] Explore English gloss of ML→ML definitions (requires hosted model or translation API budget)
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — retrieval latency and top-k quality metrics

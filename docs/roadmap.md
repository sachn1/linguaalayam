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

### v2.1 — Intent-based source filter
- [x] **Intent-based source filter** — corpus dropdown replaced with human-readable intents (EN → Malayalam, Thesaurus, Malayalam word); backend unchanged

### v2.2 — Diaspora, accessibility, i18n, and search quality
- [x] **UI language toggle** — English / Malayalam interface labels; JSON locale bundles, no page reload
- [x] **Romanised output toggle** — Malayalam definitions returned with ISO romanisation alongside for users who cannot read the script (toggle with **A ↔ അ** button)
- [x] **Smart multi-word search** — phrases and definition queries (multiple words in fuzzy mode) automatically route to semantic retrieval instead of trigram matching
- [x] **Manglish input (formal romanisation)** — Latin queries that miss exact/fuzzy are tried against multiple formal transliteration schemes; falls back to semantic if no match. Known limitation: informal romanisation ("oduka") is not reliably handled — see v2.3.
- [x] **Evaluation harness** — corpus-derived query sets (10 intents, EN + ML inputs, generated from live DB); offline model comparison with per-intent metrics and MLflow tracking

### v2.3 — Logo, MCP setup page, and OAuth
- [x] **Elephant logo** — amber elephant mark; transparent PNG; used as favicon, navbar logo, and PWA install icon
- [x] **One-click MCP setup page** — `/mcp/setup` with prominent URL copy box, per-client step-by-step guide, and developer configs collapsed; connection test button
- [x] **OAuth 2.0 for Claude.ai browser connector** — passthrough `OAuthAuthorizationServerProvider` (RFC 7591 dynamic registration, PKCE/S256, token refresh, revocation); `MCP_ISSUER_URL` env var; FastMCP 2.x wires all endpoints automatically

### v3.0 — i18n foundation and Android
- [ ] **i18n foundation** — locale JSON bundles for UI strings; architecture supports adding community-translated locales beyond EN/ML
- [ ] **Android TWA via PWABuilder** — wrap the existing PWA for Play Store; no separate codebase; requires icons, Play Developer account, and `assetlinks.json` on domain

### v3.1 — Word of the Day
- [ ] **Word of the Day** — daily featured word, filtered by frequency list to exclude common words (top 5k excluded); alternates EN/ML by default
- [ ] **User preference** — app settings: EN only / ML only / alternate; stored in `localStorage`
- [ ] **Push notifications** — service worker push for word-of-the-day on Android (requires v2.1 PWA baseline)

### v3.2 — On-device AI synthesis (in-app purchase)
- [ ] Generate synthetic (query → answer) training pairs from existing corpus (headword + POS + definition + synonyms)
- [ ] Fine-tune a small multilingual model on Malayalam dictionary Q&A
- [ ] Quality eval harness before shipping — answer quality metrics (BLEU + human eval on Malayalam output); do not ship without passing eval
- [ ] Serverless inference (Modal or RunPod) — pay-per-request, no idle GPU cost
- [ ] AI synthesis as in-app purchase — core app stays free, premium tier unlocks prose answers at lower price point than user-managed API keys


### Backlog
- [ ] **Production embedding upgrade** — eval confirms the current model underperforms on Malayalam semantic and cross-lingual queries; upgrade and re-ingest (~2h CPU); no schema change
- [ ] **Phonetic romanisation index** — add `headword_roman` column (diacritic-stripped ISO romanisation) with pg_trgm index; enables reliable informal Manglish matching (e.g. "oduka" → "ഓടുക")
- [ ] **Cross-lingual result bridging** — EN query surfaces Malayalam equivalents; ML query surfaces English equivalents
- [ ] **Multilingual query input** — detect non-EN/ML query language, translate to EN via LLM adapter
- [ ] `ml_from_ml_semantic` retrieval quality — definition → headword currently at 20% hit@1; revisit after embedding upgrade
- [ ] Reranker for mixed-script result sets — deduplicate and rerank exact + fuzzy + semantic hits in a single pass
- [ ] Explore English gloss of ML→ML definitions (requires hosted model or translation API budget)
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — retrieval latency and top-k quality metrics in production

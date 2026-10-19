# Roadmap

> Section headers use real shipped package versions (from `CHANGELOG.md`/`cz bump`), not a separate
> hand-numbered scheme — the two used to drift apart (e.g. the old "v2.8" milestone actually shipped as
> real v2.9.0; a hand-picked future milestone once collided with an already-shipped real v2.9). Where a
> milestone's bullets span more than one real version, the header shows the full range. Bullet-to-version
> mapping below is anchored to real `CHANGELOG.md` commit subjects, not individually verified for every
> single bullet against a diff — treat the version as "shipped in this range," not a guaranteed per-bullet
> citation. Not-yet-shipped future work is deliberately left **unnumbered** (`Next`, `Later`) instead of
> pre-assigned a version, to avoid this collision happening again.

### v0.2.0 — RAG ready
- [x] Query preprocessing — extract target word from natural language queries
- [x] Hybrid search — exact, fuzzy, and semantic retrieval
- [x] Response synthesis — LLM answer from top-k retrieved entries
- [x] Evaluation harness — retrieval metrics on a labeled query set

### v0.3.0–v0.3.1 — MCP server
- [x] MCP server with three tools: `exact_lookup`, `fuzzy_lookup`, `semantic_lookup`
- [x] Claude Code integration via `.mcp.json` project config
- [x] Claude Desktop setup instructions

### v0.4.0 — LLM adapter + MCP resources
- [x] `LLMAdapter` ABC with `AnthropicAdapter`, `OpenAIAdapter`, `NoLLMAdapter`
- [x] Provider selected via Hydra `_target_` — adding a new provider requires only a subclass and a YAML file
- [x] `NoLLMAdapter` — no API key needed; synthesis returns formatted reranker output
- [x] Remove HuggingFace text-generation; LLM is always API-backed or absent
- [x] MCP resource `dictionary://{headword}` alongside the existing tools

### v0.5.0-rc.0 — Additional corpora + code quality
- [x] **Datuk** — ML→ML corpus (Malayalam headwords with Malayalam definitions)
- [x] **Ekkurup** — EN→ML thesaurus (synset entries with grouped EN synonyms and ML translations)
- [x] Per-corpus filtering in retrieval via `source` parameter on all three tools
- [x] Hydra-driven corpus parsers — adding a corpus requires only a YAML config entry, no Python change
- [x] Code quality sweep — dead code removed, encapsulation fixed, silent failures logged

### v1.0.0–v2.0.3 — REST API, hosted MCP, and stable release
- [x] Thin FastAPI layer over `DictionaryTools` — `/lookup/exact`, `/lookup/fuzzy`, `/lookup/semantic`
- [x] Web UI — HTMX + Jinja2 served from FastAPI; settings sidebar, structured POS-grouped results, live filter refresh
- [x] Hosted MCP server at `/mcp` — zero-config for AI clients (`{ "url": "https://linguaalayam.org/mcp" }`)
- [x] Bring-your-own-key LLM synthesis (Anthropic / OpenAI) — key stored in browser localStorage, injected as request header, never persisted server-side
- [x] Self-hosted deployment on Hetzner CX33 (Nuremberg, €7.72/month) — Docker Compose, nginx reverse proxy
- [x] Domain and HTTPS — [linguaalayam.org](https://linguaalayam.org) live with Let's Encrypt cert
- [x] CI/CD — GitHub Actions deploy to VPS on `bump:` commit via forced-command SSH key
- [x] User guide, MCP client setup guide (Claude Code, Claude Desktop, Cursor, Windsurf, Cline, Continue)
- [x] CPU-only PyTorch in Docker — explicit `pytorch-cpu` source, no CUDA packages on VPS

### v2.1.0 — Intent-based source filter
- [x] **Intent-based source filter** — corpus dropdown replaced with human-readable intents (EN → Malayalam, Thesaurus, Malayalam word); backend unchanged

### v2.2.0 — Diaspora, accessibility, i18n, and search quality
- [x] **UI language toggle** — English / Malayalam interface labels; JSON locale bundles, no page reload
- [x] **Romanised output toggle** — Malayalam definitions returned with ISO romanisation alongside for users who cannot read the script (toggle with **A ↔ അ** button)
- [x] **Smart multi-word search** — phrases and definition queries (multiple words in fuzzy mode) automatically route to semantic retrieval instead of fuzzy headword matching. *Superseded in v2.13.1 below ("Retire semantic fallback from web search"): removed because it wasn't found to work reliably — fuzzy/edit-distance now runs on every query instead.*
- [x] **Manglish input (formal romanisation)** — Latin queries that miss exact/fuzzy are tried against multiple formal transliteration schemes; falls back to semantic if no match. Known limitation: informal romanisation ("oduka") is not reliably handled — resolved in v2.9.0 via Varnam.
- [x] **Evaluation harness** — corpus-derived query sets (10 intents, EN + ML inputs, generated from live DB); offline model comparison with per-intent metrics and MLflow tracking

### v2.3.0–v2.3.5 — Logo, MCP setup page, and OAuth
- [x] **Elephant logo** — amber elephant mark; transparent PNG; used as favicon, navbar logo, and PWA install icon
- [x] **One-click MCP setup page** — `/mcp/setup` with prominent URL copy box, per-client step-by-step guide, and developer configs collapsed; connection test button
- [x] **OAuth 2.0 for Claude.ai browser connector** — passthrough `OAuthAuthorizationServerProvider` (RFC 7591 dynamic registration, PKCE/S256, token refresh, revocation); `MCP_ISSUER_URL` env var; FastMCP 2.x wires all endpoints automatically

### v2.4.0–v2.5.0 — i18n foundation and Android
- [x] **i18n foundation** — EN/ML locale bundles complete; architecture is locale-file-based (drop a new JSON in `static/locales/` to add a language); additional UI languages tracked in backlog
- [x] **Android TWA** — PWA icons generated (48–512px PNG + maskable); `manifest.json` updated for Android; `/.well-known/assetlinks.json` endpoint live; `android/twa-manifest.json` (Bubblewrap config) checked in; `android/README.md` documents full build + Play Store publish flow
- [x] **MCP OAuth** — passthrough OAuth 2.0 (RFC 7591 dynamic registration, PKCE/S256); root-level proxy so origin-based clients (Claude Desktop, Inspector) and path-aware clients both work from the URL alone

### v2.6.0 — Play Store compliance and Android production
- [x] **Privacy policy** — `/privacy` page for Play Store listing compliance
- [x] **Android build artifacts** — gitignore for APK/AAB/keystore; Play Store closed testing active (12 testers, 14-day window)

### v2.7.0–v2.7.3 — Search quality, voice input, and attribution
- [x] **ml2en romanisation** — swapped ISO 15919 for informal ml2en; correct chillu handling (ൺ→n, ൽ→l, ർ→r); romanisation now covers Datuk definitions and Ekkurup Malayalam synonym groups
- [x] **Morphological analysis** — `mlmorph` integration; human-readable labels per headword (e.g. *past verb of ഓടുക*); shown inline in results
- [x] **Voice search** — Web Speech API mic button with EN/ML language toggle; hidden on unsupported browsers; `ml-IN` recognition returns Malayalam Unicode script
- [x] **Mobile layout** — header stacks logo above tagline on ≤600px; fixes cramped Android TWA layout
- [x] **Open data attribution** — `DATA_SOURCES.md` with per-dataset authors and licences (ODbL for Olam/Datuk, CC BY-SA 4.0 for Ekkurup by E.K. Kurup); footer and settings sidebar updated
- [x] **Service worker v2** — static assets cached first, pages network-first with offline fallback

### v2.8.0 — Sayahna corpus and deployment hardening
- [x] **Shabdataaravali / Sayahna corpus added** — the fourth active corpus (ML→ML, classical 1917 dictionary)
- [x] **Deployment and linting hardening** — new deployment strategy, additional linter restrictions, cleanups

### v2.9.0–v2.9.1 — Informal Manglish, ingest-time morphology, and UI cleanup
- [x] **Informal Manglish via Varnam** — Latin queries that miss exact/fuzzy now try the [Varnam](https://varnamproject.com) API for informal romanisation (e.g. *oduka* → *ഓടുക*) before falling back to the local formal transliteration schemes from v2.2.0; resolves the informal-romanisation gap noted there
- [x] **Search mode removed** — the exact/fuzzy/semantic selector is gone from both UI and `/search`; retrieval is always fuzzy-first (exact matches score 1.0). *The "automatic semantic fallback" part was itself removed later — see v2.13.1 below ("Retire semantic fallback from web search").*
- [x] **`ml_ml` source filter** — Datuk + Sayahna merged under one "All Malayalam → Malayalam" UI option; the old `datuk`-expands-to-both behaviour is now explicit
- [x] **Morphology computed at ingest time** — `DatukEntry`/`SayahnaEntry` store mlmorph analysis at parse time instead of recomputing it per search request
- [x] **Clickable definitions** — ML→ML definition tokens that exist as their own headword become links, via a cached `DictionaryTools.ml_headword_set()`
- [x] **`transliteration/` package** — `morphology.py`, `varnam.py`, and the existing romanisation helpers (`core.py`) consolidated under one package
- [x] **Search UI simplification** — visible language dropdown removed (kept only as a hidden field driven by speech recognition / browser locale); mode selector and its help text removed
- [x] **Handwriting trace** — [jayasree](https://github.com/sachn1/jayasree) (published to npm, formerly the malayalam-stroker repo) animates stroke-by-stroke handwriting for Malayalam headwords; trace button on Datuk/Sayahna entries, lazy-loaded client-side so the ~11.6MB glyph/stroke data is never fetched unless clicked; vendored from npm at build time via `make sync-jayasree`, no runtime CDN dependency
- [x] **Varnam candidate validation** — suggestions are validated against real dictionary entries before being shown, instead of trusting Varnam's ranking blindly

### v2.9.0–v2.10.0 — Traffic analytics, voice UX, and Manglish search quality

*Shares v2.9.0 with the milestone above — the same release shipped both the Varnam/UI-cleanup work and the
first cut of traffic analytics; grouped separately here by topic, not by a second release.*

- [x] **Traffic/usage analytics** — `request_log` table + `RequestLoggingMiddleware` logs real search-bar queries (route type, search term, IP/country, bot heuristic); `/admin/analytics` dashboard (HTMX-polling, HTTP Basic Auth) shows traffic by route, top search terms, top clients, and outbound-link clicks
- [x] **Click-beacon tracking** — `POST /track/click` (label allow-list) covers interactions with no server route of their own: handwriting trace (`jayasree`), the romanise toggle (`ml2en`), voice search (`web_speech`), and outbound links (GitHub, docs, mlmorph credit)
- [x] **Route classification fixes** — `/mcp/setup` (human page view) no longer conflated with `/mcp` (actual AI-assistant protocol traffic); `/docs` classified as `api_docs` instead of falling into a generic bucket; top user agents shown, static assets split out of the "other" bucket
- [x] **Voice search language picker** — flag icon grouped directly against the mic button (not elsewhere on the page) so it reads unambiguously as "language to speak," not an interface/search-language setting; a first-time onboarding modal (opened by either the mic or the flag) replaces the previous silent browser-locale default
- [x] **Manglish/English ambiguity handling** — words valid in both (e.g. *kali* → the goddess Kali, or *കലി*, "anger") now show the confident English result plus a collapsed "Did you mean this in Malayalam?" suggestion (Varnam candidates capped at 5), instead of silently picking one interpretation
- [x] **Search-quality fixes** — Varnam candidates are validated via exact/lemma lookup instead of fuzzy match, eliminating false "did you mean" links to words that don't actually exist; fallback triggers (Varnam, semantic) now check for a *confident* result, not just a non-empty one, so weak spelling coincidences (e.g. "kundi" matching unrelated entries like "Kunti" at 30%) no longer silently block better matches or show a misleading empty "0 results" heading
- [x] **Search box sync** — clicking a definition word-link or a "did you mean" suggestion now updates the visible search box to match, instead of leaving it showing the original query

### v2.11.0 — AI Answer introduced

- [x] **AI Answer toggle** — cost-aware nudging and sidebar settings in the web UI; TogetherAI (Qwen 3.5 9B) added as the web app's free server-side default, alongside bring-your-own-key Anthropic/OpenAI; adapter internals deduped into a shared `LangChainAdapter` base
- [x] **Smarter query-understanding fallback** — regex patterns still tried first; LLM fallback improved for phrasings the patterns miss
- [x] **Marian translation guard** — translation is no longer applied against a stale input-language flag, guarded via `langdetect`
- [x] **Analytics dashboard rework** — per-query country/client/timestamp breakdowns, restricted to real search traffic

### v2.12.0–v2.12.3 — Cloud Run migration and GeoIP-based location analytics
- [x] **Migrated the app to Google Cloud Run** — scale-to-zero serverless hosting, replacing the always-on Hetzner VPS as the live deploy target. Postgres stays on Hetzner unchanged, reached from Cloud Run via Direct VPC egress + a Cloud Router/Cloud NAT static IP, allow-listed on Hetzner's firewall (see `terraform/` and `terraform/RUNBOOK.md`)
- [x] **DNS cutover** — `linguaalayam.org`/`www.linguaalayam.org` now point at Cloud Run via Google-managed domain mappings (DNS-only, not Cloudflare-proxied — required for Google's managed TLS certificate issuance)
- [x] **Hetzner kept as a manual rollback path** — the app container there is stopped (not deleted); `.github/workflows/cd.yml` can redeploy it on demand via `workflow_dispatch` if Cloud Run costs or behavior ever justify rolling back
- [x] **GeoIP-based location analytics** — Cloud Run has no Cloudflare-style `CF-IPCountry`/`CF-Connecting-IP` header, so `/admin/analytics` now resolves city/region/country from a local MaxMind GeoLite2-City database (`observability/geoip.py`) instead; `scripts/backfill_geoip.py` retroactively resolved historical rows
- [x] **Automated Cloud Run deploys** — `.github/workflows/cd-cloud-run.yml` builds, runs pending Alembic migrations via a Cloud Run Job, and deploys, replacing the manual `gcloud` commands used during the migration itself
- [ ] **Parked: Pub/Sub + BigQuery search analytics** — a deeper analytics pipeline (which corpus answered, AI-answer economics, query-understanding regex-vs-LLM rate, Manglish signals, language mix, query shape, MCP-vs-web split) designed but not built — see `docs/pubsub_bigquery_design.md` on `feature/pubsub-bigquery-analytics`

### v2.13.0 — Fuzzy matching: mlmorph lemma first, edit distance over trigram
- [x] **mlmorph lemma tried before fuzzy matching, for every caller** — `DictionaryTools.fuzzy_lookup()` now runs the existing lemma-lookup step internally (previously wired into `web.py`'s search only); the MCP tools, REST `/lookup/fuzzy`, the CLI RAG pipeline, the eval harness, and the debug script all get it automatically with no call-site changes. Fixes real inflected-form queries (e.g. എഴുതുന്നു → എഴുതുക) that neither trigram nor edit distance alone could retrieve
- [x] **Fuzzy fallback switched from pg_trgm trigram similarity to normalized Levenshtein edit distance** — trigram's similarity ratio structurally penalizes short words (a fixed-size typo costs a much bigger fraction of a short word's trigram set), silently hiding real typos below the confidence bar; edit distance doesn't have this bias. Confirmed empirically against the real corpus (precision/recall/F1/AUC analysis across English and Malayalam) before switching, not assumed
- [x] **Thresholds recalibrated for the new metric, not carried over from pg_trgm** — the retrieval-time gate (`fuzzy_lookup`'s own `threshold`) moved `0.3` → `0.75`; the display-confidence gate (`_MIN_CONFIDENT_SCORE`/`MIN_SCORE`) moved `0.55` → `0.80`. At the old `0.55`, edit distance's own precision is only ~0.51 — carrying the number over uncalibrated would have been worse than keeping trigram
- [x] **Embeddings ruled out as a secondary semantic check** — tested twice against the real corpus (a single-pair test, then a proper candidate-list test with pairwise word-to-word comparison); genuinely unrelated real words scored 0.65–0.92 semantic similarity against each other, no usable separation from "same word" (1.0). Not pursued further

### v2.13.1 — Retire semantic fallback from web search

- [x] **`semantic_lookup` removed from the web search path** — the web UI's `/search` route now always runs fuzzy
  (edit-distance) lookup regardless of word count, and never falls back to semantic/HNSW retrieval. It wasn't
  found to work reliably for meaning-based queries in practice. This supersedes v2.2.0's "Smart multi-word search"
  and the "automatic semantic fallback" part of v2.9.0's "Search mode removed" entry above — both are now
  inaccurate as written. `semantic_lookup` itself is unchanged and still live via MCP, the REST `/lookup/semantic`
  endpoint, the CLI RAG pipeline, and the eval harness — only the web UI stopped calling it.
- [x] **AI hint split into two honest variants** — "empty" (nothing confident found at all) vs. "weak" (something
  shown but may not be what was meant), instead of one generic nudge regardless of which case applies.

### v2.13.2 — Cold-start latency fix

- [x] **Lazy ML imports** — `langchain_anthropic`, `sentence-transformers`, and the cross-encoder reranker are now
  imported inside the functions that need them instead of at module load time, cutting cold-start import time
  from ~14.3s to ~7.9s locally.
- [x] **Background-loaded embedding model** — `LazyEmbeddingService` lets the app start serving `/health` and
  other non-search routes immediately, while the real embedding model loads in a background thread; any request
  that actually needs it blocks only until that load finishes, not until the next cold start. Measured on
  production Cloud Run: cold starts dropped from ~38.6s to ~7.9s average.

### Unreleased — Phrase decomposition for AI Answer

*Genuinely unreleased: not yet merged to `master`, currently on a feature branch. Unlike every section above,
this one may still change before it ships — not a stable historical record.*

- [x] **Per-word decomposition fallback** — when a whole-phrase lookup finds nothing confident, each word is
  looked up individually (fuzzy + Varnam fallback) and fed to the LLM to stitch into a compositional answer,
  instead of giving up (e.g. Manglish "Dayavayi Irikkoo sahodara" → "please sit, brother")
- [x] **`?debug=1` trace panel** — shows per-word Varnam candidates, what the dictionary returned, and the exact
  prompt sent to the LLM, for developer debugging

### Next — Word of the Day
- [ ] **Phonetic Manglish index** — add `headword_roman` column storing ml2en output for each Malayalam headword; fuzzy-matching against it enables reliable informal Manglish matching (e.g. "oduka" → "otuka" → "ഓടുക") without the ISO 15919 formalism gap; requires migration + re-ingest. Re-evaluate which similarity metric to use against `headword_roman` now that headword fuzzy matching itself has moved from pg_trgm to edit distance — the same length-bias reasoning may or may not carry over to romanized text
- [ ] **Word of the Day** — daily featured word, filtered by frequency list to exclude common words (top 5k excluded); alternates EN/ML by default
- [ ] **User preference** — app settings: EN only / ML only / alternate; stored in `localStorage`
- [ ] **Push notifications** — service worker push for word-of-the-day on Android

### Later — On-device AI synthesis (in-app purchase)
- [ ] Generate synthetic (query → answer) training pairs from existing corpus (headword + POS + definition + synonyms)
- [ ] Fine-tune a small multilingual model on Malayalam dictionary Q&A
- [ ] Quality eval harness before shipping — answer quality metrics (BLEU + human eval on Malayalam output); do not ship without passing eval
- [ ] Serverless inference (Modal or RunPod) — pay-per-request, no idle GPU cost
- [ ] AI synthesis as in-app purchase — core app stays free, premium tier unlocks prose answers at lower price point than user-managed API keys


### Backlog
- [ ] **Rate limiting** — no request-rate limiting exists yet on `/search` or any other route; referenced as a
  known gap in `SECURITY.md`'s "Out of scope" section (DoS via high query volume)
- [ ] **Find a reliable non-EN/ML translation model** — `MarianTranslationService` (Helsinki-NLP/opus-mt-mul-en) is disabled by default (`TRANSLATION_BACKEND=noop`) as of 2026-10-13 after real-data testing found it unreliable on both single words and full sentences, confirmed across several languages, not one family: single-word misses in Hindi (`தமிழ்`/`विसर्जन` → "Slow"/"Distortion"), Russian (`кот` → "Cut"), Mandarin (`快` → "Come on."), Arabic (`قطة` → "Cut"), and German (`Katze` echoed untranslated); a full Hindi sentence translated into unrelated nonsense ("Fishing wire makes bad dental floss") while the equivalent German, Russian, and Tamil sentences were all correct. Spanish and Portuguese were clean in this sample. `MarianTranslationService` and the `TranslationService`/`NoOpTranslationService` plugin architecture (`linguaalayam/translation/`) are unchanged and ready — re-enabling or swapping in a new backend is a factory addition plus an env var, not a revert
- [ ] **Morphology tree for search hits** — mlmorph exposes a `Generator` (same FST as the existing `Analyser`, run in reverse) that can produce other inflected surface forms from a root + grammatical tag, e.g. `generate('എഴുതുക<v><past>') → 'എഴുതി'`; confirmed working directly against the real model. A search hit could show root + part of speech inline (already available from `Analyser`, just not surfaced) with an expand control revealing a small tree of other forms (past/present/future tense, etc.) generated live. No `get_all_forms(root)` API exists — several plausible tags (`<imp>`, `<inf>`, `<neg>`, `<caus>`, noun case markers) returned empty on probing, so the real tag vocabulary mlmorph supports needs to be found from its FST source/grammar before building `morphology_tree(root)` — don't assume Apertium-style tag names carry over
- [ ] **Production embedding upgrade** — eval confirms the current model underperforms on Malayalam semantic and cross-lingual queries; upgrade and re-ingest (~2h CPU); no schema change
- [ ] **Cross-lingual result bridging** — EN query surfaces Malayalam equivalents; ML query surfaces English equivalents
- [ ] `ml_from_ml_semantic` retrieval quality — definition → headword currently at 20% hit@1; revisit after embedding upgrade
- [ ] Reranker for mixed-script result sets — deduplicate and rerank exact + fuzzy + semantic hits in a single pass
- [ ] Explore English gloss of ML→ML definitions (requires hosted model or translation API budget)
- [ ] `int8` quantisation for faster inference
- [ ] Query caching for repeated lookups
- [ ] Monitoring — retrieval latency and top-k quality metrics in production

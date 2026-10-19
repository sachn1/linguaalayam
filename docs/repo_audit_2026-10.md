# Repo audit — October 2026

Produced at the owner's request after several AI-assisted sessions accumulated features
(phrase decomposition, grounding/citations, cold-start fixes, fuzzy-matching rewrite,
translation gating, MCP OAuth, observability/analytics) across many branches. Four
parallel, read-only investigations (architecture-vs-docs, dead code/duplication,
docs-vs-reality, test-suite health) were run against `feature/ai-answer-grounding-and-mcp-nudge`
(HEAD `ed9fe14`), which is 2 merged PRs behind `master` (HEAD `d00a821`, v2.13.2) — see the
caveat in section 1.

This document is **findings only** — nothing in the repo has been changed as a result of
this audit. It is not yet committed; the owner should review and decide what to act on.

---

## Headline: the "AI slop" worry is real but narrow

**No genuinely dead code was found.** Every top-level function/class checked has a real
caller (including FastAPI route handlers and HTMX/JS call sites that a naive grep misses).
This is the single most reassuring finding — the codebase has not accumulated orphaned
functions despite many sessions of iteration.

The real problems are concentrated in four places:

1. **One function has outgrown its shape**: `linguaalayam/api/web.py`'s `search()` route.
2. **Documentation has drifted from the code it describes**, in several concrete,
   falsifiable ways — not vague staleness, but specific wrong claims.
3. **One real user-facing capability was quietly removed** without the docs catching up.
4. **Housekeeping backlog**: unmerged/stale branches, an uncommitted notebook, duplicated
   test helpers, and a few untested modules.

---

## 1. `linguaalayam/api/web.py::search()` — the single highest-value structural fix

This function (currently ~283 lines, backed by ~340 more lines of module-level helpers that
exist only to support it — roughly **620 of the file's 762 lines** are "the search feature")
has absorbed at least **seven distinct concerns** into one request handler with no
sub-boundaries:

- translation pre-processing (optional Marian)
- LLM adapter selection/construction (BYOK vs. server-side default)
- query understanding (regex → LLM fallback)
- fuzzy retrieval
- Manglish/Varnam transliteration, its own candidate validation and "did you mean" ranking
- a confidence heuristic (`_has_confident_result`, 0.80 threshold) that gates three
  independent downstream decisions
- phrase decomposition + citation-grounded synthesis (a second, structurally different
  retrieval+synthesis path with its own system prompt)
- query morphology display, "feature tip" selection, and 17-key template context assembly

Control flow is deeply stateful: `headword`, `results`, `answer`, `already_confident`,
`varnam_used`, `word_entries` are mutated and re-derived across the function in an order
that matters (e.g. the Varnam block can overwrite `headword`/`results` set earlier, and the
decomposition block's behavior depends on whether that overwrite happened). Any future
change to one concern has to be reasoned about against all the others in the same function.

**This is where the owner's instinct that something has drifted is best-founded.** It's not
bad code — each block is well-commented and individually reasonable — but it's no longer a
clean pipeline, and every new feature (like the grounding/citations work just added) makes
it harder to reason about the next one.

*Recommendation (not yet actioned): break `search()` into named sub-steps — e.g. a
translation step, a headword-resolution step (query understanding + Manglish), a retrieval
step, a synthesis step (whole-phrase vs. decomposition) — each independently testable,
composed by a thinner route handler. This is a refactor, not a rewrite; the logic itself is
sound.*

---

## 2. A real, currently-advertised capability regression

**"Search by description/phrase"** (e.g. *"feeling of nostalgia"*) is documented as working
in `docs/user-guide.md:16` and `docs/roadmap.md`'s v2.8 entry ("multi-word queries route to
semantic retrieval"). Commit `16783c0` ("fix: run fuzzy lookup on every query, retire
semantic_lookup from web search") removed this from the web UI entirely — confirmed
independently by two of the four audits: `api/web.py` never calls `tools.semantic_lookup()`
anywhere, only `fuzzy_lookup()` (edit-distance over headwords). `semantic_lookup` itself
still works fine — it's just not reachable from `/search` anymore, only from MCP, the REST
`/lookup/semantic` endpoint, the CLI RAG pipeline, and the eval harness.

A genuine free-text description query will now very likely return nothing useful on the web
UI, while the docs still promise it does.

**This needs an explicit product decision, not just a doc fix**: either restore some form of
semantic fallback in the web path (if AI Answer handling meaning-based queries isn't
considered an adequate replacement), or update `user-guide.md`/`roadmap.md` to stop
promising it. Right now the docs are making a promise the code doesn't keep.

**Decision (owner, 2026-10-18)**: semantic_lookup was removed from the web path because it
wasn't found to work well — not an oversight. Update the docs now to describe current
reality (no separate semantic-search path; AI Answer/decomposition is the meaning-based
query story). Do not restore semantic_lookup as part of this cleanup. A *new* LLM-based
replacement may come later, with its own docs written once that work actually lands —
don't pre-document it now.

---

## 3. Documentation drift, file by file

### CLAUDE.md — the most drifted of the two architecture docs
- **Wrong class names**: the module table lists entry types `EnMlEntry`, `MlMlEntry` —
  these don't exist anywhere in the repo. Real classes are `OlamEntry`, `DatukEntry`,
  `SayahnaEntry`, `EkkurupEntry` (`linguaalayam/models/entries.py`), correctly named in
  `docs/architecture.md` itself. CLAUDE.md disagrees with its own sibling doc, not just
  with the code.
- **Missing modules entirely**: `eval/` (6 files, a whole harness), `mcp/remote.py` and
  `mcp/shared.py` (the actual production MCP server mounted at `/mcp` — far more
  consequential than the standalone `mcp/server.py`, which *is* listed), `api/web.py` and
  `api/app.py` themselves (the two largest, most-changed files in the repo),
  `api/dependencies.py`, `api/oauth.py`, `database/session.py`, `env.py`, `translation/`,
  `transliteration/`, `templates/`, `static/vendor/jayasree/`.
- Reads like an early/abridged snapshot that was never grown alongside `docs/architecture.md`.

### docs/architecture.md — more current than CLAUDE.md, but has its own errors
- **Observability section is wrong**: claims every inbound request is logged once and
  classified; real behavior (`observability/middleware.py:63-68,101-105`) only writes a row
  for `/search` requests with a non-empty query from a non-bot client — everything else is
  classified but never persisted. This matches `docs/observability.md` (which is correct) —
  architecture.md contradicts its own sibling doc here too.
- **LLM-synthesis-is-opt-in claim is incomplete**: says the user supplies their own key via
  BYOK; omits that `X-LLM-Enabled: 1` triggers a free server-side TogetherAI default
  (`_get_server_llm()`, web.py) with no user key at all. `docs/user-guide.md` describes this
  correctly — architecture.md doesn't.
- **REST/web-UI wiring diagram is wrong**: shows the web UI calling the `/lookup/*` REST
  endpoints. It doesn't — `web.py` calls `DictionaryTools` directly via the same singleton
  the REST endpoints use, never over internal HTTP.
- Module table, tech stack, ingestion/RAG/MCP mermaid flows, fuzzy-matching thresholds,
  translation module description: all confirmed accurate.

### docs/roadmap.md — one confirmed regression, one undocumented shipped feature
- v2.8's "smart multi-word search → semantic retrieval" entry is now false (see section 2).
- Cold-start lazy-import work is merged to `master` (PR #48) with **no roadmap entry at
  all** — shipped but undocumented.
- `SECURITY.md`'s claim that rate-limiting is "tracked in backlog" has zero matching entry
  in roadmap.md's actual backlog — unverifiable as stated.

### docs/setup.md — would actively mislead a new contributor
- Says ingest covers "all three corpora" — there are **four** (`olam_enml`, `datuk`,
  `ekkurup`, `sayahna`); setup.md's own data-sources table two sections down correctly
  lists all four, so the doc contradicts itself.
- Data-download directory layout is missing the `db_corpus/` path prefix entirely and
  **omits the Sayahna corpus path** completely, despite Sayahna being listed as Active
  right below.

### CHANGELOG.md — structurally broken, not just neglected
- Last real entry is v0.4.0; current version is 2.13.2 — **~60+ releases undocumented**.
- Root cause is mechanical: `pyproject.toml` has `update_changelog_on_bump = false`, and the
  bump workflow calls `cz bump --yes` with no `--changelog` flag. The automation has never
  been wired to write to this file since whatever commit first wrote it retroactively.
- Easiest, highest-confidence fix in this whole audit: flip the config flag or remove the
  file's false promise of being maintained.

### Accurate, no action needed
`README.md`, `docs/observability.md`, `DATA_SOURCES.md`, `CONTRIBUTING.md`, `.env.example`
(a few undocumented-but-harmless env vars with working defaults), `SECURITY.md` (bar the
roadmap cross-reference above).

---

## 4. Dead code, duplication, stale thresholds — mostly a non-issue

- **No dead top-level functions/classes found**, after checking FastAPI route registration,
  HTMX/JS call sites, and Hydra `_target_` config references (not just name-grep).
- **`web.py` vs. `rag/pipeline.py` overlap is intentional, not sloppy duplication**: shared
  primitives (`_SYNTHESIS_SYSTEM`, `_SYNTHESIS_TEMPLATE`, `_format_entries`,
  `understand_query`) are factored out and reused; the extra surface in `web.py` (Varnam,
  decomposition, citations, nudges) is additive web-UI-specific logic with no equivalent
  need in the generic pipeline used by CLI/eval/MCP. The one real gap: `web.py` never calls
  `semantic_lookup` (see section 2) — undocumented, not clearly a bug, but worth a decision.
- **Stale hardcoded threshold**: `rag/pipeline.py` and `eval/runner.py` still have
  `fuzzy_threshold: 0.3` as their Python-level default (left over from the pg_trgm era,
  before PR #45's edit-distance rewrite set the real value to 0.75). Every actual Hydra
  config overrides this correctly, so it's latent, not live-broken — but any future caller
  building a config by hand without the yaml would silently get a stale, uncalibrated value.
- **`eval/` scripts**: `seed.py` and `main.py` are CI-wired; `prepare_corpus_sample.py`,
  `prepare_eval_queries.py`, `model_compare.py` are intentionally excluded from coverage
  (documented in `pyproject.toml`, "require live DB or HF models") and are human-run
  one-off tooling, not dead code.

---

## 5. Branch hygiene

**20 of 24 local branches are fully merged into `master` — safe to delete.** 4 need an
explicit decision, not a blanket delete:

| Branch | Why it needs a look |
|---|---|
| `feature/phrase-decomposition-and-whats-new` | Tip commit's subject matches current branch's HEAD (`ed9fe14`) exactly — likely cherry-picked/rebased forward, but not diff-confirmed identical. |
| `fix/deploy-pins-stale-version` | Only a merge commit resolving a PR conflict — may already be fully superseded by PR #46's actual merge. |
| `perf/cpu-torch-and-optimizations` | From May 2026, predates later torch/CI changes — may be an abandoned early experiment or already absorbed into `feature/v0.6-rest-api`'s same-day "v1.0" commit. |
| `research/embedding-quality-eval` | Research branch; findings may already be absorbed into `eval/model_compare.py` or the reranker notebooks without the branch itself landing. |

---

## 6. Notebooks

| Notebook | Verdict |
|---|---|
| `explore.ipynb` | Pure disposable scratch — generic row counts, no findings worth keeping. |
| `fuzzy_vs_edit_retrieval_quality.ipynb` | Real research backing the PR #45 fuzzy-matching rewrite. Keep. |
| `malayalam_fuzzy_matching_research.ipynb` | Origin analysis for the same rewrite. Keep. |
| `mcp_testing.ipynb` | Closer to a manual runbook than research — not harmful, but could live in `docs/` instead. |
| `phrase_decomposition_sense_ranking.ipynb` | Real research behind the decomposition feature's design, including an honestly-documented unresolved tradeoff. Keep. |
| `sense_cleanup_llm_test.ipynb` | **Untracked, sitting in limbo.** Real finding (directly informed `_verify_citations`'s design) but framed by its own markdown as a "quick gut-check." Needs a decision: commit it, or extract the one real finding into a comment/doc and drop the notebook. |

---

## 7. Test suite — mechanically healthy, with real coverage gaps

- `poetry run pytest -q`: **415 passed, 0 failed, 0 skipped.**
- `ruff check .` / `ruff format --check .`: **both clean.**
- Aggregate coverage: **87%**, against a real, CI-enforced 80% gate
  (`.github/workflows/ci.yml`, `--cov-fail-under=80`). The aggregate gate is file-blind,
  though — it doesn't surface the specific gaps below.

**Modules with real, untested logic:**
- `observability/queries.py` — 41% (no `test_queries.py` at all; `traffic_by_route_type`,
  `top_queries`, `top_clients`, `top_outbound_clicks` are essentially unverified).
- `api/admin.py` — 43% (no `test_admin.py`; the `/admin/analytics` dashboard + Basic Auth
  gating is untested).
- `scripts/backfill_geoip.py` — 0%, no test file at all.
- `api/oauth.py` (62%) and `mcp/remote.py` (65%) — only incidentally covered as a side
  effect of OAuth tests, no dedicated test files.
- `translation/marian.py` — 59%, only a thin 36-line test file.

**Duplicated test infrastructure**: the same `DictionaryTools`-result-shaped dict is
independently reimplemented **4-5 times** across test files — including **two incompatible
versions in the same file** (`tests/api/test_web.py`'s `_result()` and `_entry()`). None of
this lives in `conftest.py`. Concrete consolidation candidate.

**`tests/api/test_web.py` has outgrown itself**: 1036 lines, ~40 test functions, testing at
least 5 distinct concerns (routing, source/lang params, AI-hint heuristics, decomposition,
debug panel, locale files) — already organized with section-comment banners that mark
exactly where it could be split into separate files.

**3 brittle tests** found that assert on internal call mechanics rather than observable
behavior (e.g. `rag/test_pipeline.py`'s `test_source_passed_to_tools` has an `or` fallback
checking both keyword- and positional-arg forms — a sign a prior refactor already broke this
assertion once and it was patched to tolerate both instead of being re-pinned). Worth a
second look during any related refactor, not urgent on their own.

---

## Priority ranking (suggested, not decided)

1. **Decide on the semantic-search regression** (section 2) — either restore it or stop
   promising it in docs. This is the one place code and docs actively disagree about a
   real user-facing capability.
2. **CHANGELOG.md** — mechanical, five-minute fix, highest confidence finding in the audit.
3. **`docs/architecture.md`'s observability and LLM-opt-in claims**, and **CLAUDE.md's
   wrong class names + missing-module list** — both doc sets actively mislead about current
   behavior.
4. **`docs/setup.md`'s corpus count and directory layout** — would mislead a new contributor
   immediately on first setup.
5. **Branch cleanup** — delete the 20 confirmed-merged branches; look at the 4 flagged ones
   individually before deciding.
6. **`sense_cleanup_llm_test.ipynb`** — commit it or extract-and-drop; don't leave it
   untracked.
7. **Structural**: break up `web.py::search()` — highest long-term value, but a real
   refactor, not a quick fix; best scheduled deliberately rather than squeezed in.
8. **Test-suite housekeeping**: consolidate duplicate result-dict builders into
   `conftest.py`, consider splitting `test_web.py`, add tests for the 5 undertested modules.
9. **Minor**: fix the stale `0.3` threshold defaults in `pipeline.py`/`eval/runner.py`.

None of this has been actioned — this document is the "findings report" requested before
any decision on what to fix.

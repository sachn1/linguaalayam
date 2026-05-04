# RAG Pipeline

LangGraph pipeline that takes a natural-language query, runs hybrid retrieval, optionally reranks, and synthesises a concise answer via Claude or a HuggingFace model.

## Usage

```bash
# Simple query — Hydra override (avoid special characters: commas, quotes, dashes)
poetry run rag 'rag.query=run'
poetry run rag 'rag.query=ഓടുക' rag.source=olam_enml

# Complex / prose queries — env var sidesteps Hydra's lexer
RAG_QUERY='what does the word "pastoral" mean?' poetry run rag
RAG_QUERY='translate justice to Malayalam' poetry run rag rag.rerank=true

# Tune retrieval
poetry run rag 'rag.query=run' rag.top_k=10 rag.rerank=true

# Switch LLM
RAG_QUERY='define ephemeral' poetry run rag llm=huggingface
```

To use HuggingFace models, install the optional dependency group first:

```bash
poetry install --with huggingface
```

## Pipeline nodes

```
understand → retrieve → [rerank?] → synthesize
```

| Node | Description |
|---|---|
| **understand** | Extracts the target headword and intent from the query using regex patterns with LLM fallback |
| **retrieve** | Runs exact, fuzzy, and semantic search in parallel; merges and deduplicates results |
| **rerank** | Optional cross-encoder reranking (`mmarco-mMiniLMv2-L12-H384-v1`); enabled with `rag.rerank=true` |
| **synthesize** | LLM answer constrained by `SKILLS.md` — 1–3 plain sentences, no markdown, TTS-ready |

Each candidate in the output shows its source tool and similarity score:

```
  [1] run     [exact    1.000]  word: run  [v] ഓടുക...
  [2] runs    [fuzzy    0.612]  word: runs  [n] ഓട്ടങ്ങൾ...
  [3] sprint  [semantic 0.873]  word: sprint  [v] ദ്രുതഗതിയിൽ...
```

## Config options (`config/rag/default.yaml`)

| Key | Default | Description |
|---|---|---|
| `rag.query` | `""` | Query string — use `RAG_QUERY` env var for complex text |
| `rag.source` | `null` | Corpus filter (e.g. `olam_enml`) |
| `rag.top_k` | `5` | Candidates passed to the synthesizer |
| `rag.rerank` | `false` | Enable cross-encoder reranking |
| `rag.fuzzy_threshold` | `0.3` | pg_trgm similarity threshold (0–1) |
| `rag.fuzzy_limit` | `10` | Max fuzzy candidates before merge |

## Debug tool (all three retrieval methods)

```bash
poetry run debug-retriever 'debug.query=run'
DEBUG_QUERY='to move quickly on foot' poetry run debug-retriever
poetry run debug-retriever 'debug.query=run' debug.top_k=10 debug.fuzzy_threshold=0.2
```

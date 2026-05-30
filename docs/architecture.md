# Architecture

Three independent subsystems share the same Postgres + pgvector database:
the **ingestion pipeline**, the **RAG pipeline**, and the **MCP server**.

Three corpora are active: **Olam** (EN→ML), **Datuk** (ML→ML), and **Ekkurup** (EN→ML thesaurus). Each corpus is wired via a `parser._target_` entry in `config/corpus/all.yaml`; no Python code change is needed to add a new corpus.

---

## Ingestion

```mermaid
flowchart LR
    A[corpus files\nTSV · YAML] --> B[corpus parsers\nenml · datuk · ekkurup]
    B --> C[EmbeddingService\nsentence-transformers]
    C --> D[VectorCheckpoint\nJSONL fault-tolerance]
    D --> E[(PostgreSQL\npgvector)]
```

Checkpoint-based — restarts safely after a crash without re-embedding already-vectorised entries.

---

## RAG pipeline

```mermaid
flowchart LR
    Q[user query] --> U[understand_query\nregex → LLMAdapter]
    U --> DT[DictionaryTools\nexact · fuzzy · semantic]
    DT --> R{rerank?}
    R -- yes --> RR[CrossEncoderReranker]
    R -- no --> S
    RR --> S[synthesize\nLLMAdapter.complete\nor formatted candidates]
    DB[(PostgreSQL)] --> DT
    S --> A[answer]
```

`understand_query` tries regex patterns first and only calls the LLM adapter for unrecognised phrasings.
When `llm=nollm`, synthesis skips the LLM and returns formatted top-k candidates directly.

---

## MCP server

```mermaid
flowchart LR
    C[Claude / MCP client] --> T[tools\nexact_lookup\nfuzzy_lookup\nsemantic_lookup]
    C --> R[resource\ndictionary://headword]
    T & R --> DT[DictionaryTools]
    DT --> DB[(PostgreSQL\npgvector)]
```

No LLM involvement — pure retrieval. The embedding model loads once at startup.

---

## Module reference

| Module | Purpose |
|---|---|
| `linguaalayam/models/entries.py` | Entry types (`EnMlEntry`, `MlMlEntry`, `EkkurupEntry`), each with `to_embed_text()` |
| `linguaalayam/models/orm.py` | SQLAlchemy `DictionaryEntry` ORM — headword, embed_text, JSONB data, Vector(768) |
| `linguaalayam/corpus/base.py` | `parse_definition_tsv()` — shared 3-column TSV helper used by `enml.py` and `datuk.py` |
| `linguaalayam/corpus/` | One parser per corpus (`enml.py`, `datuk.py`, `ekkurup.py`), each exposes `parse()` |
| `linguaalayam/embeddings/service.py` | `EmbeddingService` — wraps sentence-transformers, exposes `batch_size` and `vector_size` |
| `linguaalayam/database/queries.py` | `batch_insert()`, `similarity_search()` (HNSW cosine), `get_ingested_headwords()` |
| `linguaalayam/llm/adapters/` | `LLMAdapter` ABC + `AnthropicAdapter`, `OpenAIAdapter`, `NoLLMAdapter` |
| `linguaalayam/rag/pipeline.py` | LangGraph graph: understand → retrieve → rerank? → synthesize |
| `linguaalayam/rag/tools.py` | `DictionaryTools` — exact, fuzzy, semantic lookup over a live DB session |
| `linguaalayam/mcp/server.py` | FastMCP server — three tools + `dictionary://{headword}` resource |
| `linguaalayam/scripts/ingest.py` | Ingestion entry point; corpus parsers injected via Hydra `_target_` — no hardcoded parser map |
| `config/` | Hydra config groups: `corpus` (with per-source `parser._target_`), `embedding`, `database`, `llm`, `rag` |
| `migrations/` | Alembic schema migrations |

---

## Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11+ |
| DB | PostgreSQL + pgvector (local Docker) |
| ORM / migrations | SQLAlchemy 2.0, Alembic |
| Embeddings | sentence-transformers (`paraphrase-multilingual-mpnet-base-v2`) |
| RAG graph | LangGraph + LangChain |
| LLM | Anthropic Claude or OpenAI via `LLMAdapter`; `NoLLMAdapter` for zero-key usage |
| MCP | FastMCP (`mcp` SDK) |
| Config | Hydra |
| Testing | pytest, ruff, pre-commit |

---

## API examples

Query understanding — regex-based, no external dependencies:

```python
from linguaalayam.rag.query_understanding import understand_query

result = understand_query("define serendipity")
assert result.headword == "serendipity"
assert result.intent == "define"

result = understand_query("translate water to malayalam")
assert result.intent == "translate"
```

LLM adapters — the `NoLLMAdapter` needs no API key:

```python
from linguaalayam.llm.adapters.nollm import NoLLMAdapter

adapter = NoLLMAdapter()
assert not adapter.has_llm
```

Entry text representations:

```python
from linguaalayam.models.entries import EnMlEntry, EkkurupEntry, EkkurupSense, MlMlEntry

entry = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
text = entry.to_embed_text()
assert text.startswith("word: run")
assert "ഓടുക" in text

ml_entry = MlMlEntry(headword="ഓടുക", definitions=[("v", "to run fast")])
ml_text = ml_entry.to_embed_text()
assert "ഓടുക" in ml_text

ek_entry = EkkurupEntry(
    headword="run",
    senses=[EkkurupSense(pos="verb", en=[["sprint", "dash"]], ml=[["ഓടുക"]])],
)
ek_text = ek_entry.to_embed_text()
assert "[verb]" in ek_text
assert "sprint" in ek_text
assert "ഓടുക" in ek_text
```

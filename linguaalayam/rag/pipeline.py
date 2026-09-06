"""LangGraph RAG pipeline for the LinguAalayam dictionary assistant."""

from typing import TypedDict

from langgraph.graph import END, StateGraph
from omegaconf import DictConfig

from linguaalayam.llm.adapters.base import LLMAdapter
from linguaalayam.rag.query_understanding import understand_query
from linguaalayam.rag.reranker import CrossEncoderReranker
from linguaalayam.rag.tools import DictionaryTools, merge_candidates

_SYNTHESIS_SYSTEM = (
    "Answer questions about Malayalam and English words directly and"
    " concisely using only the dictionary entries provided. Respond "
    "in one to three plain sentences as if speaking aloud — no markdown, "
    "no bullet points, no preamble, no meta-commentary. State the"
    " meaning, translation, or usage directly from the entries. Never use "
    "your own general knowledge to supply something the entries do not "
    "contain — this dictionary does not cover grammatical analysis such as "
    "sandhi/samasa decomposition (vigraham), etymology, or word derivation. "
    "If the question asks for that, or anything else the entries do not "
    "contain, say plainly that this dictionary does not have that "
    "information, while still sharing whatever relevant meaning the "
    "entries do provide."
)

_SYNTHESIS_TEMPLATE = "Question: {query}\n\nDictionary entries:\n{entries}"


class RAGState(TypedDict):
    """Shared state passed between LangGraph nodes in the RAG pipeline."""

    query: str
    headword: str | None
    intent: str | None
    candidates: list[dict]
    answer: str


def _format_entries(candidates: list[dict]) -> str:
    """Format a list of candidate dicts as a numbered text block."""
    lines = []
    for i, c in enumerate(candidates, 1):
        score_str = f"{c['score']:.3f}" if c.get("score") is not None else ""
        header = f"[{i}] {c['headword']}  ({c['source']}, {c['match_type']}"
        header += f", score={score_str})" if score_str else ")"
        lines.append(header)
        lines.append(f"    {c['embed_text']}")
    return "\n".join(lines)


def build_pipeline(
    tools: DictionaryTools,
    llm: LLMAdapter,
    cfg: DictConfig,
    reranker: CrossEncoderReranker | None = None,
):
    """Build and compile the LangGraph RAG pipeline.

    Graph: understand → retrieve → [rerank?] → synthesize

    Parameters
    ----------
    tools : DictionaryTools
        Dictionary retrieval tools backed by a live DB session.
    llm : LLMAdapter
        Language model adapter for query understanding and synthesis.
        When ``llm.has_llm`` is ``False`` (e.g. ``NoLLMAdapter``), the
        synthesize node returns formatted top-k candidates without an API call.
    cfg : DictConfig
        Pipeline configuration; recognised keys: ``top_k`` (int, default 5),
        ``source`` (str, default None), ``rerank`` (bool, default False),
        ``rerank_candidate_k`` (int, default 25) — candidates fetched before
        reranking cuts down to ``top_k``, ignored when ``rerank`` is False,
        ``fuzzy_threshold`` (float, default 0.3), ``fuzzy_limit`` (int, default 10).
    reranker : CrossEncoderReranker or None, optional
        Cross-encoder reranker; only used when ``cfg.rerank`` is ``True``.

    Returns
    -------
    CompiledGraph
        Compiled LangGraph graph ready to invoke with ``{"query": "..."}``.
    """
    top_k: int = cfg.get("top_k", 5)
    source: str | None = cfg.get("source", None)
    use_rerank: bool = cfg.get("rerank", False)
    rerank_candidate_k: int = cfg.get("rerank_candidate_k", 25)
    fuzzy_threshold: float = cfg.get("fuzzy_threshold", 0.3)
    fuzzy_limit: int = cfg.get("fuzzy_limit", 10)

    # Retrieve a wider pool ahead of reranking so the cross-encoder can promote
    # a correct-but-lower-ranked candidate rather than only reshuffling a pool
    # already truncated to top_k.
    fetch_k = max(top_k, rerank_candidate_k) if use_rerank else top_k

    def understand_node(state: RAGState) -> dict:
        """Extract headword and intent from the query."""
        result = understand_query(state["query"], llm=llm)
        return {"headword": result.headword, "intent": result.intent}

    def retrieve_node(state: RAGState) -> dict:
        """Fetch exact, fuzzy, and semantic candidates; merge deduped."""
        headword = state["headword"] or state["query"]
        query = state["query"]

        exact = tools.exact_lookup(headword, source=source)
        fuzzy = tools.fuzzy_lookup(
            headword, source=source, threshold=fuzzy_threshold, top_k=max(fuzzy_limit, fetch_k)
        )
        semantic = tools.semantic_lookup(query, top_k=fetch_k, source=source)

        return {"candidates": merge_candidates([exact, fuzzy, semantic])}

    def rerank_node(state: RAGState) -> dict:
        """Re-score merged candidates with the cross-encoder if enabled."""
        if reranker is None or not state["candidates"]:
            return {"candidates": state["candidates"]}
        reranked = reranker.rerank(state["query"], state["candidates"], top_n=top_k)
        return {"candidates": reranked}

    def synthesize_node(state: RAGState) -> dict:
        """Generate an answer from top-k candidates using the LLM or formatted text."""
        if not state["candidates"]:
            return {"answer": "No dictionary entries found for your query."}

        entries_text = _format_entries(state["candidates"][:top_k])

        if not llm.has_llm:
            return {"answer": entries_text}

        content = _SYNTHESIS_TEMPLATE.format(query=state["query"], entries=entries_text)
        return {"answer": llm.complete(_SYNTHESIS_SYSTEM, content)}

    graph: StateGraph = StateGraph(RAGState)
    graph.add_node("understand", understand_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("rerank", rerank_node)
    graph.add_node("synthesize", synthesize_node)

    graph.set_entry_point("understand")
    graph.add_edge("understand", "retrieve")
    graph.add_conditional_edges(
        "retrieve",
        lambda _: "rerank" if use_rerank else "synthesize",
        {"rerank": "rerank", "synthesize": "synthesize"},
    )
    graph.add_edge("rerank", "synthesize")
    graph.add_edge("synthesize", END)

    return graph.compile()

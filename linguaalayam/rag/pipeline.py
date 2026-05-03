"""LangGraph RAG pipeline for the LinguAalayam dictionary assistant."""

from pathlib import Path
from typing import TypedDict

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from omegaconf import DictConfig

from linguaalayam.rag.query_understanding import understand_query
from linguaalayam.rag.reranker import CrossEncoderReranker
from linguaalayam.rag.tools import DictionaryTools

_SYNTHESIS_SYSTEM = (Path(__file__).parent / "SKILLS.md").read_text().strip()

_SYNTHESIS_TEMPLATE = (
    "Question: {query}\n\n"
    "Dictionary entries:\n{entries}"
)


class RAGState(TypedDict):
    query: str
    headword: str | None
    intent: str | None
    candidates: list[dict]
    answer: str


def _merge_candidates(lists: list[list[dict]]) -> list[dict]:
    """Merge results from multiple tools, deduplicating on (source, headword).

    Priority: exact > fuzzy > semantic — the first tool to surface an entry wins.
    """
    seen: set[tuple[str, str]] = set()
    merged = []
    for results in lists:
        for item in results:
            key = (item["source"], item["headword"])
            if key not in seen:
                seen.add(key)
                merged.append(item)
    return merged


def _format_entries(candidates: list[dict]) -> str:
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
    llm: BaseChatModel,
    cfg: DictConfig,
    reranker: CrossEncoderReranker | None = None,
):
    """Build and compile the LangGraph RAG pipeline.

    Graph: understand → retrieve → [rerank?] → synthesize

    cfg keys (all optional):
      top_k          int   5    candidates passed to synthesizer
      source         str   None corpus filter (e.g. "olam_enml")
      rerank         bool  False enable cross-encoder reranking
      fuzzy_threshold float 0.3  pg_trgm similarity threshold
      fuzzy_limit    int   10   max fuzzy candidates before merge
    """
    top_k: int = cfg.get("top_k", 5)
    source: str | None = cfg.get("source", None)
    use_rerank: bool = cfg.get("rerank", False)
    fuzzy_threshold: float = cfg.get("fuzzy_threshold", 0.3)
    fuzzy_limit: int = cfg.get("fuzzy_limit", 10)

    def understand_node(state: RAGState) -> dict:
        result = understand_query(state["query"], llm=llm)
        return {"headword": result.headword, "intent": result.intent}

    def retrieve_node(state: RAGState) -> dict:
        headword = state["headword"] or state["query"]
        query = state["query"]

        exact = tools.exact_lookup(headword, source=source)
        fuzzy = tools.fuzzy_lookup(
            headword, source=source, threshold=fuzzy_threshold, top_k=fuzzy_limit
        )
        semantic = tools.semantic_lookup(query, top_k=top_k, source=source)

        return {"candidates": _merge_candidates([exact, fuzzy, semantic])}

    def rerank_node(state: RAGState) -> dict:
        if reranker is None or not state["candidates"]:
            return {}
        reranked = reranker.rerank(state["query"], state["candidates"], top_n=top_k)
        return {"candidates": reranked}

    def synthesize_node(state: RAGState) -> dict:
        if not state["candidates"]:
            return {"answer": "No dictionary entries found for your query."}

        entries_text = _format_entries(state["candidates"][:top_k])
        content = _SYNTHESIS_TEMPLATE.format(query=state["query"], entries=entries_text)

        response = llm.invoke([
            SystemMessage(content=_SYNTHESIS_SYSTEM),
            HumanMessage(content=content),
        ])
        return {"answer": response.content}

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

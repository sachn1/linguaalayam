"""Shared formatting utility for MCP server implementations."""


def format_results(results: list[dict], query: str, method: str) -> str:
    """Format a list of lookup result dicts as a human-readable string for MCP responses."""
    if not results:
        return f"No {method} results found for {query!r}."
    lines = [f"{len(results)} {method} result(s) for {query!r}:\n"]
    for i, r in enumerate(results, 1):
        lines.append(
            f"[{i}] {r['headword']}  [{r['source']} · {r['match_type']} · {r['score']:.3f}]"
        )
        lines.append(r["embed_text"])
        lines.append("")
    return "\n".join(lines).strip()

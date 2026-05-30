"""Query understanding — extract headword and intent from natural language queries.

Strategy: try regex patterns first (free, instant), fall back to LLM only
when no pattern matches (handles novel phrasings).
"""

import logging
import re
from typing import TYPE_CHECKING, Literal

from pydantic import BaseModel

if TYPE_CHECKING:
    from linguaalayam.llm.adapters.base import LLMAdapter

log = logging.getLogger(__name__)

Intent = Literal["define", "translate", "compare", "usage", "unknown"]

# (compiled pattern, intent) — tried in order, first match wins
_PATTERNS: list[tuple[re.Pattern, Intent]] = [
    (re.compile(r"what does ['\"]?(.+?)['\"]? mean", re.I), "define"),
    (re.compile(r"what is the meaning of ['\"]?(.+?)['\"]?$", re.I), "define"),
    (re.compile(r"define (?:the word )?['\"]?(.+?)['\"]?$", re.I), "define"),
    (re.compile(r"meaning of ['\"]?(.+?)['\"]?$", re.I), "define"),
    (re.compile(r"what is ['\"]?(.+?)['\"]?\??$", re.I), "define"),
    (re.compile(r"how (?:do you )?say ['\"]?(.+?)['\"]? in malayalam", re.I), "translate"),
    (re.compile(r"['\"]?(.+?)['\"]? in malayalam$", re.I), "translate"),
    (re.compile(r"translate ['\"]?(.+?)['\"]?(?: to malayalam)?$", re.I), "translate"),
    (re.compile(r"compare ['\"]?(.+?)['\"]? (?:and|with|vs\.?) ['\"]?.+['\"]?$", re.I), "compare"),
    (re.compile(r"usage of ['\"]?(.+?)['\"]?$", re.I), "usage"),
    # single word — Latin script or Malayalam Unicode block
    (re.compile(r"^([\wഀ-ൿ]+)$"), "define"),
]

_FALLBACK_PROMPT = (
    "Extract the target word or phrase and the user's intent from this dictionary query.\n\n"
    "Query: {query}\n\n"
    "Return a JSON object with exactly two keys:\n"
    '  "headword": the word or phrase to look up\n'
    '  "intent": one of define | translate | compare | usage | unknown'
)


class QueryUnderstanding(BaseModel):
    """Structured output from query understanding: extracted headword and intent."""

    headword: str
    intent: Intent


def understand_query(
    query: str,
    llm: "LLMAdapter | None" = None,
) -> QueryUnderstanding:
    """Extract headword and intent from a natural language query.

    Tries regex patterns first; only calls the LLM if no pattern matches.

    Parameters
    ----------
    query : str
        Raw natural-language query from the user.
    llm : LLMAdapter or None, optional
        Language model adapter for LLM-based fallback extraction.
        When ``None`` or ``has_llm=False``, unrecognised queries return
        ``intent="unknown"`` with the raw query as headword.

    Returns
    -------
    QueryUnderstanding
        Extracted headword and intent label.
    """
    q = query.strip()

    for pattern, intent in _PATTERNS:
        m = pattern.match(q)
        if m:
            return QueryUnderstanding(headword=m.group(1).strip(), intent=intent)

    if llm is None or not llm.has_llm:
        return QueryUnderstanding(headword=q, intent="unknown")

    try:
        return llm.extract_structured(QueryUnderstanding, _FALLBACK_PROMPT.format(query=q))
    except Exception:
        log.warning("LLM query understanding failed for %r — falling back to raw query", q, exc_info=True)
        return QueryUnderstanding(headword=q, intent="unknown")

"""Manglish/Varnam resolution for a Latin-script query with no confident direct match."""

from dataclasses import dataclass, field

from fastapi import Request

from linguaalayam.api.web.confidence import has_confident_result
from linguaalayam.observability import log_feature_event
from linguaalayam.rag.tools import DictionaryTools
from linguaalayam.transliteration import is_latin_script, roman_to_malayalam_candidates

_MAX_SUGGESTIONS = 5


@dataclass
class ManglishResolution:
    """Outcome of trying to resolve a Latin-script query as Manglish."""

    headword: str
    results: list[dict]
    varnam_used: bool = False
    varnam_alternatives: list[str] = field(default_factory=list)
    manglish_suggestions: list[str] = field(default_factory=list)


def resolve_manglish(
    headword: str,
    results: list[dict],
    *,
    translation,
    request: Request,
    tools: DictionaryTools,
    src: str | list[str] | None,
) -> ManglishResolution:
    """Try to resolve a Latin-script headword as informal Manglish via Varnam.

    Falls back to local transliteration schemes if Varnam is unavailable.
    Candidates are validated via exact/lemma lookup only (never fuzzy —
    fuzzy-matching a fabricated candidate spelling only tells you something
    resembles it, not that the candidate itself is real). When a confident
    result already exists, any Manglish candidates found become a secondary
    "did you mean" suggestion instead of overriding it.

    Parameters
    ----------
    headword : str
        The query's resolved headword, as extracted by query understanding.
    results : list[dict]
        The whole-phrase lookup's own results, before Manglish resolution.
    translation : TranslationResult or None
        The translation pre-processing result, if any; skips Manglish
        resolution entirely when a real translation already ran.
    request : Request
        The in-flight request, passed through to ``log_feature_event``.
    tools : DictionaryTools
        Retrieval tools backed by a live DB session.
    src : str or list[str] or None
        Corpus filter, as accepted by ``DictionaryTools`` methods.

    Returns
    -------
    ManglishResolution
        The resolved headword/results (replaced only when a confident
        Malayalam reading was found and nothing more confident already
        existed) plus any Varnam suggestions.
    """
    if not is_latin_script(headword) or (translation and translation.was_translated):
        return ManglishResolution(headword=headword, results=results)

    from linguaalayam.transliteration.varnam import manglish_to_malayalam  # lazy import

    already_confident = has_confident_result(results)
    manglish_query = headword.lower()
    ml_candidates = manglish_to_malayalam(manglish_query)
    if ml_candidates:
        log_feature_event("varnam", request, query=headword)
    elif not already_confident:
        ml_candidates = roman_to_malayalam_candidates(manglish_query)

    candidates_with_entries: list[tuple[str, list[dict]]] = []
    for ml_candidate in ml_candidates:
        candidate_results = tools.exact_lookup(ml_candidate, source=src) or tools.lemma_lookup(
            ml_candidate, source=src
        )
        if candidate_results:
            candidates_with_entries.append((ml_candidate, candidate_results))

    if not candidates_with_entries:
        return ManglishResolution(headword=headword, results=results)

    if already_confident:
        return ManglishResolution(
            headword=headword,
            results=results,
            manglish_suggestions=[c for c, _ in candidates_with_entries][:_MAX_SUGGESTIONS],
        )

    new_headword, new_results = candidates_with_entries[0]
    return ManglishResolution(
        headword=new_headword,
        results=new_results,
        varnam_used=True,
        varnam_alternatives=[c for c, _ in candidates_with_entries[1:]][:_MAX_SUGGESTIONS],
    )

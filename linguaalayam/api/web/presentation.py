"""Display-only helpers: feature tips, query morphology, and the AI-answer nudge."""

import random

from linguaalayam.api.web.confidence import has_confident_result
from linguaalayam.translation.marian import LANG_NAMES
from linguaalayam.transliteration import analyse_word, is_latin_script

# AI Answer is written in whatever language the input-language flag picked —
# never auto-detected from the query text. "en"/"ml" need no translation.
ANSWER_LANGUAGE_NAMES: dict[str, str] = {"en": "English", "ml": "Malayalam", **LANG_NAMES}

# A query this long reads more like a full question than a term lookup — the
# shape raw dictionary entries answer poorly, where nudging towards AI Answer helps.
AI_HINT_MIN_WORDS = 3

# Lower bar for the "weak" hint specifically: even when a confident literal
# match already displays, a 2+ word query may still benefit from AI breaking
# it down compositionally rather than showing one matched entry as-is.
DECOMPOSE_HINT_MIN_WORDS = 2


def feature_tip(
    headword: str, *, skip_mlmorph: bool = False, skip_jayasree: bool = False
) -> str | None:
    """Return a random mlmorph- or jayasree-flavoured tip for a Malayalam headword.

    Parameters
    ----------
    headword : str
        The resolved headword the search answered. Returns ``None`` for a
        Latin-script or multi-word headword — neither mlmorph nor the trace
        button applies.
    skip_mlmorph : bool, optional
        Pass True when the same word's mlmorph analysis is already shown
        elsewhere on the page, by default False.
    skip_jayasree : bool, optional
        Pass True when no trace button actually rendered on the page (e.g. no
        confident dictionary entry was displayed) — the tip would otherwise
        point at a button that isn't there, by default False.

    Returns
    -------
    str or None
        Tip text, or None if no tip applies.
    """
    if is_latin_script(headword) or " " in headword:
        return None

    def _mlmorph_tip() -> str | None:
        """Build the mlmorph-analysis tip, or None if mlmorph can't analyse the word."""
        labels = analyse_word(headword)
        if not labels:
            return None
        return f"mlmorph sees {headword} as: {' / '.join(labels)}."

    def _jayasree_tip() -> str:
        """Build the handwriting-trace tip."""
        return f"Curious how {headword} is written? Click the trace icon next to it above."

    choices = []
    if not skip_mlmorph:
        choices.append(_mlmorph_tip)
    if not skip_jayasree:
        choices.append(_jayasree_tip)
    random.shuffle(choices)
    for tip_fn in choices:
        tip = tip_fn()
        if tip:
            return tip
    return None


def compute_query_morphology(headword: str) -> str | None:
    """Return mlmorph analysis of the resolved headword, whenever it's Malayalam.

    Takes the already-resolved headword (post-Varnam, if the original query
    was Manglish) rather than the raw query, so the tag shows regardless of
    the input-language flag — script alone is a sufficient, unambiguous
    signal that mlmorph analysis applies.

    Parameters
    ----------
    headword : str
        The resolved headword the search answered.

    Returns
    -------
    str or None
        A ``/``-joined label string, or None if the headword isn't Malayalam
        or mlmorph can't analyse it.
    """
    if headword and not is_latin_script(headword):
        labels = analyse_word(headword)
        if labels:
            return " / ".join(labels)
    return None


def compute_ai_hint(
    *, answer: str | None, llm_key: str, llm_enabled: bool, query: str, results: list[dict]
) -> str | None:
    """Return the AI-answer nudge variant for a question-shaped query with AI off.

    Parameters
    ----------
    answer : str or None
        The already-synthesized answer, if any; suppresses the hint when set.
    llm_key : str
        The caller's bring-your-own-key header value, if any.
    llm_enabled : bool
        Whether the server-side AI Answer default is enabled for this request.
    query : str
        The raw user query.
    results : list[dict]
        The whole-phrase lookup's results, used to pick the hint variant.

    Returns
    -------
    str or None
        ``"empty"`` when nothing confident is shown at all, ``"weak"`` when
        something is shown but may not be what was meant, or None when no
        hint applies.
    """
    if answer is not None or llm_key or llm_enabled:
        return None
    word_count = len(query.split())
    if not has_confident_result(results):
        return "empty" if word_count >= AI_HINT_MIN_WORDS else None
    return "weak" if word_count >= DECOMPOSE_HINT_MIN_WORDS else None

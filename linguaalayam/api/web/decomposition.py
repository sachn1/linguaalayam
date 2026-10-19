"""Per-word decomposition fallback and citation grounding for AI Answer."""

from pydantic import BaseModel

from linguaalayam.rag.tools import DictionaryTools
from linguaalayam.transliteration import is_latin_script

# A real phrase worth decomposing is a handful of words — guards against a
# pasted paragraph turning into dozens of per-word lookups.
MAX_DECOMPOSITION_WORDS = 8

# Enough senses to let the LLM disambiguate a polysemous word, not just
# whichever sense a DB query happened to return first.
MAX_SENSES_PER_WORD = 3

# Mirrors results.html's own source_label mapping (kept here too since
# citations are built server-side).
SOURCE_LABELS = {
    "olam_enml": "Olam",
    "datuk": "Datuk",
    "sayahna": "Shabdataaravali 1917",
    "ekkurup": "Ekkurup",
}


class WordGloss(BaseModel):
    """One decomposed word's meaning in context, with optional dictionary grounding."""

    word: str
    meaning: str
    grounded: bool
    headword: str | None = None
    source: str | None = None
    quote: str | None = None


class GroundedAnswer(BaseModel):
    """Structured decomposition-synthesis output: prose answer plus a per-word grounding trail."""

    answer: str
    words: list[WordGloss]


def decompose_and_lookup(
    headword: str, tools: DictionaryTools, src: str | list[str] | None
) -> tuple[list[tuple[str, list[dict]]], list[dict]]:
    """Look up each word of a multi-word query individually.

    Each Latin-script word tries a real headword first (``fuzzy_lookup``),
    then falls back to Varnam's Manglish reading.

    Parameters
    ----------
    headword : str
        The multi-word phrase to decompose, already resolved by query
        understanding.
    tools : DictionaryTools
        Retrieval tools backed by a live DB session.
    src : str or list[str] or None
        Corpus filter, as accepted by ``DictionaryTools`` methods.

    Returns
    -------
    tuple[list[tuple[str, list[dict]]], list[dict]]
        The ``(word, senses)`` pairs used for synthesis, and a parallel
        per-word trace (every Varnam candidate tried, which validated, and
        the senses returned) for the ``?debug=1`` view.
    """
    from linguaalayam.transliteration.varnam import manglish_to_malayalam  # lazy import

    found: list[tuple[str, list[dict]]] = []
    trace: list[dict] = []
    for word in headword.split()[:MAX_DECOMPOSITION_WORDS]:
        word_trace = {
            "word": word,
            "fuzzy_senses": [],
            "varnam_candidates": [],
            "chosen_candidate": None,
            "final_senses": [],
        }
        word_results = tools.fuzzy_lookup(word, source=src, top_k=MAX_SENSES_PER_WORD)
        word_trace["fuzzy_senses"] = word_results
        if not word_results and is_latin_script(word):
            candidates = manglish_to_malayalam(word.lower())
            word_trace["varnam_candidates"] = candidates
            for candidate in candidates:
                candidate_results = tools.exact_lookup(candidate, source=src) or tools.lemma_lookup(
                    candidate, source=src
                )
                if candidate_results:
                    word_results = candidate_results[:MAX_SENSES_PER_WORD]
                    word_trace["chosen_candidate"] = candidate
                    break
        word_trace["final_senses"] = word_results
        trace.append(word_trace)
        if word_results:
            found.append((word, word_results))
    return found, trace


def format_word_entries(word_entries: list[tuple[str, list[dict]]]) -> str:
    """Format per-word senses as a numbered block, each tagged by its source word.

    Parameters
    ----------
    word_entries : list[tuple[str, list[dict]]]
        ``(word, senses)`` pairs, as returned by ``decompose_and_lookup``.

    Returns
    -------
    str
        A numbered, human-readable block suitable for an LLM prompt.
    """
    lines = []
    for i, (word, entries) in enumerate(word_entries, 1):
        lines.append(f'[{i}] "{word}":')
        for entry in entries:
            lines.append(f"    -> {entry['headword']} ({entry['source']}): {entry['embed_text']}")
    return "\n".join(lines)


def verify_citations(
    glosses: list[WordGloss], word_entries: list[tuple[str, list[dict]]]
) -> list[dict]:
    """Re-order and verify the LLM's per-word glosses against real dictionary text.

    Never trusts the LLM's citation at face value — a hallucinated or
    wrong-but-real quote is worse than no citation at all. ``word_entries``
    (not the LLM's own output order) is the authority for both ordering and
    verification, so citations always read left-to-right as the user typed
    them, regardless of what order the model produced its glosses in.

    Parameters
    ----------
    glosses : list[WordGloss]
        The model's own per-word output, in whatever order it produced.
    word_entries : list[tuple[str, list[dict]]]
        The same per-word dictionary lookups the model was given, already in
        input order.

    Returns
    -------
    list[dict]
        One dict per word in ``word_entries``, in that same order, each with
        ``word``, ``meaning``, ``grounded``, and (if grounded) ``headword``,
        ``source``, ``quote``.
    """
    by_word = {g.word.strip().lower(): g for g in glosses}
    citations: list[dict] = []
    for word, entries in word_entries:
        gloss = by_word.get(word.strip().lower())
        raw_text = "\n".join(e["embed_text"] for e in entries)
        valid_headwords = {e["headword"]: e for e in entries}
        grounded = False
        headword = source = quote = None
        if (
            gloss
            and gloss.grounded
            and gloss.quote
            and gloss.quote.strip()
            and gloss.quote.strip() in raw_text
            and gloss.headword in valid_headwords
        ):
            grounded = True
            headword = gloss.headword
            source = SOURCE_LABELS.get(
                valid_headwords[headword]["source"], valid_headwords[headword]["source"]
            )
            quote = gloss.quote.strip()
        citations.append(
            {
                "word": word,
                "meaning": gloss.meaning if gloss else word,
                "grounded": grounded,
                "headword": headword,
                "source": source,
                "quote": quote,
            }
        )
    return citations

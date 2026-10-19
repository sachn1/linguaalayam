"""Shared "is this result worth showing" gate used across the web search pipeline."""

# F1-optimal threshold for normalized edit-distance similarity (real labeled-typo
# precision/recall/AUC analysis — see notebooks/malayalam_fuzzy_matching_research.ipynb).
# Must match results.html's MIN_SCORE.
MIN_CONFIDENT_SCORE = 0.80


def has_confident_result(results: list[dict]) -> bool:
    """Return whether at least one result would actually be shown.

    Mirrors ``results.html``'s own display filter — a weak fuzzy match (e.g.
    an unrelated headword that happens to edit-distance-match) makes
    ``results`` non-empty without giving the user anything worth seeing.

    Parameters
    ----------
    results : list[dict]
        Candidate results, shaped like ``DictionaryTools``' ``_to_result()`` output.

    Returns
    -------
    bool
        True if at least one result is exact, a lemma match, or scores at or
        above ``MIN_CONFIDENT_SCORE``.
    """
    return any(
        r["match_type"] in ("exact", "lemma") or r["score"] >= MIN_CONFIDENT_SCORE for r in results
    )

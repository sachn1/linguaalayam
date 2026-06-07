"""Morphological analysis for Malayalam words using mlmorph."""

import re
from functools import lru_cache

_analyser = None

_POS = {
    "v": "verb",
    "n": "noun",
    "np": "proper noun",
    "adj": "adjective",
    "adv": "adverb",
    "num": "numeral",
    "pron": "pronoun",
    "conj": "conjunction",
    "post": "postposition",
    "part": "particle",
    "intj": "interjection",
}

_FEATURES = {
    "past": "past",
    "present": "present",
    "future": "future",
    "pl": "plural",
    "sg": "singular",
    "locative": "locative",
    "genitive": "genitive",
    "dative": "dative",
    "accusative": "accusative",
    "instrumental": "instrumental",
    "vocative": "vocative",
    "nominative": "nominative",
    "cvb-adv-part-past": "past participle",
    "cvb-adv-part-absolute": "converb",
    "causative-voice": "causative",
    "root": "root",
}

_TAG_RE = re.compile(r"<([^>]+)>")


def _get_analyser():
    global _analyser
    if _analyser is None:
        from mlmorph import Analyser

        _analyser = Analyser()
    return _analyser


@lru_cache(maxsize=4096)
def analyse_word(word: str) -> str | None:
    """Return a human-readable morphological label for a Malayalam word, or None."""
    try:
        results = _get_analyser().analyse(word)
    except Exception:
        return None
    if not results:
        return None

    best_analysis, _ = results[0]
    tags = _TAG_RE.findall(best_analysis)
    raw_root = _TAG_RE.sub("", best_analysis).strip()

    if not tags:
        return None

    pos_label = _POS.get(tags[0])
    if not pos_label:
        return None

    feature_tags = tags[1:]
    features = [_FEATURES[t] for t in feature_tags if t in _FEATURES]

    root_differs = raw_root and raw_root != word

    if not features:
        if root_differs:
            return f"{pos_label}, related to {raw_root}"
        return pos_label

    main = features[0]
    if root_differs:
        return f"{main} {pos_label} of {raw_root}"
    return f"{main} {pos_label}"

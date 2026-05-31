"""Transliteration helpers for Malayalam ↔ Roman script conversion."""

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate as _t


def malayalam_to_roman(text: str) -> str:
    """Transliterate a Malayalam string to ISO 15919 Roman script."""
    return _t(text, sanscript.MALAYALAM, sanscript.ISO)

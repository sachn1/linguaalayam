"""No-op translation backend — default while no reliable non-EN/ML model is in
place. See docs/roadmap.md's backlog for why Marian was disabled.
"""

from linguaalayam.translation.base import TranslationResult, TranslationService


class NoOpTranslationService(TranslationService):
    """TranslationService that never translates — every query passes through unchanged."""

    supports_translation = False

    def translate(self, text: str, source_lang: str = "") -> TranslationResult:
        """Return ``text`` unchanged, with ``was_translated=False``.

        Parameters
        ----------
        text : str
            Input text (not inspected).
        source_lang : str, optional
            BCP-47 or ISO 639-1 source language code; only its ISO 639-1 prefix
            is kept, for consistency with ``MarianTranslationService``'s result
            shape (e.g. telling the AI synthesis LLM which language the user
            picked, even though no translation happened).

        Returns
        -------
        TranslationResult
            ``text`` unchanged, ``was_translated=False``.
        """
        iso = source_lang.split("-")[0].lower() if source_lang else "en"
        return TranslationResult(text=text, source_lang=iso, was_translated=False)

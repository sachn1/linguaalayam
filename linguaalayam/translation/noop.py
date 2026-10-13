"""No-op translation backend — used while no reliable non-EN/ML model is in place.

Real-data testing (2026-10-13) found Helsinki-NLP/opus-mt-mul-en unreliable on both
single words and full sentences for several supported languages — not just one
language family, confirmed across Hindi, Tamil, Russian, Mandarin, and Arabic
single-word inputs, and a full Hindi sentence translated into unrelated nonsense.
Rather than rip out the TranslationService abstraction or the Marian
implementation, this backend disables translation at the factory level
(``TRANSLATION_BACKEND=noop``, the default) until a better model is evaluated — see
docs/roadmap.md's backlog. ``MarianTranslationService`` stays in place, unused but
ready, so re-enabling is a one-line env var change, not a revert.
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

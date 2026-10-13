"""Translation service factory — builds the configured backend implementation."""

from linguaalayam.translation.base import TranslationService
from linguaalayam.translation.marian import MarianTranslationService
from linguaalayam.translation.noop import NoOpTranslationService


def build_translation_service(backend: str = "noop") -> TranslationService:
    """Instantiate a translation service for the requested backend.

    Parameters
    ----------
    backend : str, optional
        Backend identifier — ``"noop"`` (default) disables translation
        entirely, passing non-EN/ML queries through unchanged; ``"marian"``
        uses Helsinki-NLP/opus-mt-mul-en. ``"noop"`` is the default as of
        2026-10-13: real-data testing found Marian unreliable on both single
        words and full sentences across several languages (Hindi, Tamil,
        Russian, Mandarin, Arabic) — not one language family, see
        docs/roadmap.md's backlog. Set ``TRANSLATION_BACKEND=marian`` to
        re-enable it.

    Returns
    -------
    TranslationService
        The configured translation service.

    Raises
    ------
    ValueError
        If ``backend`` is not a recognised identifier.
    """
    if backend == "noop":
        return NoOpTranslationService()
    if backend == "marian":
        return MarianTranslationService()
    raise ValueError(f"Unknown translation backend: {backend!r}")

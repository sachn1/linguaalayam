"""Translation service factory — builds the configured backend implementation."""

from linguaalayam.translation.base import TranslationService
from linguaalayam.translation.marian import MarianTranslationService


def build_translation_service(backend: str = "marian") -> TranslationService:
    """Instantiate a translation service for the requested backend.

    Parameters
    ----------
    backend : str, optional
        Backend identifier; currently only ``"marian"`` is supported.
        Defaults to ``"marian"``.

    Returns
    -------
    TranslationService
        The configured translation service.

    Raises
    ------
    ValueError
        If ``backend`` is not a recognised identifier.
    """
    if backend == "marian":
        return MarianTranslationService()
    raise ValueError(f"Unknown translation backend: {backend!r}")

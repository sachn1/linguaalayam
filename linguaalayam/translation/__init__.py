from linguaalayam.translation.base import TranslationService
from linguaalayam.translation.marian import MarianTranslationService


def build_translation_service(backend: str = "marian") -> TranslationService:
    if backend == "marian":
        return MarianTranslationService()
    raise ValueError(f"Unknown translation backend: {backend!r}")

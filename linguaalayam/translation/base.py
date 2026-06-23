"""Translation service ABC — swap implementations by changing the TRANSLATION_BACKEND env var."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TranslationResult:
    text: str
    source_lang: str  # ISO 639-1 code, e.g. "fr"
    was_translated: bool
    source_lang_name: str = field(default="")  # human-readable, e.g. "French"


class TranslationService(ABC):
    @abstractmethod
    def translate(self, text: str, source_lang: str = "") -> TranslationResult:
        """Return text in English.

        source_lang is a BCP-47 code (e.g. "fr-FR") or ISO 639-1 (e.g. "fr").
        Pass-through unchanged when source_lang is empty, "en-*", or "ml-*".
        """

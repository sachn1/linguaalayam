"""Translation service ABC — swap implementations by changing the TRANSLATION_BACKEND env var."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class TranslationResult:
    """Result returned by a translation service."""

    text: str
    source_lang: str  # ISO 639-1 code, e.g. "fr"
    was_translated: bool
    source_lang_name: str = field(default="")  # human-readable, e.g. "French"


class TranslationService(ABC):
    """Abstract base class for text-to-English translation backends."""

    @abstractmethod
    def translate(self, text: str, source_lang: str = "") -> TranslationResult:
        """Return ``text`` translated into English.

        Parameters
        ----------
        text : str
            Input text to translate.
        source_lang : str, optional
            BCP-47 (e.g. ``"fr-FR"``) or ISO 639-1 (e.g. ``"fr"``) language
            code of the source text.  Pass an empty string or omit to attempt
            pass-through detection.  Text is returned unchanged when
            ``source_lang`` is empty, ``"en-*"``, or ``"ml-*"``.

        Returns
        -------
        TranslationResult
            The translated text along with detected language metadata.
        """

"""Helsinki-NLP/opus-mt-mul-en translation service.

Lazy-loads the model on first non-EN/ML request so API startup stays fast.
The caller supplies the source language (from the UI selector) — no automatic
language detection is attempted.  To switch backends, implement TranslationService
and set TRANSLATION_BACKEND to the new key in build_translation_service().
"""

import logging

from transformers import MarianMTModel, MarianTokenizer

from linguaalayam.translation.base import TranslationResult, TranslationService

log = logging.getLogger(__name__)

_SKIP_PREFIXES = {"en", "ml"}

# ISO 639-1 code → human-readable name for the UI indicator.
# Add entries here when switching to a model that covers more languages.
_LANG_NAMES: dict[str, str] = {
    "de": "German",
    "fr": "French",
    "ru": "Russian",
    "es": "Spanish",
    "pt": "Portuguese",
    "zh": "Mandarin",
    "ar": "Arabic",
    "ur": "Urdu",
    "hi": "Hindi",
    "ta": "Tamil",
    "bn": "Bengali",
}

# Speech API locale codes exposed to the UI language selector.
# The list drives both voice recognition language and the translation trigger.
# Update this list when switching to a model with different language coverage.
SPEECH_LANGS: list[dict[str, str]] = [
    {"code": "en-US", "label": "EN", "flag": "us"},
    {"code": "ml-IN", "label": "മ", "flag": "in"},
    {"code": "de-DE", "label": "DE", "flag": "de"},
    {"code": "fr-FR", "label": "FR", "flag": "fr"},
    {"code": "ru-RU", "label": "RU", "flag": "ru"},
    {"code": "es-ES", "label": "ES", "flag": "es"},
    {"code": "pt-PT", "label": "PT", "flag": "pt"},
    {"code": "zh-CN", "label": "中文", "flag": "cn"},
    {"code": "ar-SA", "label": "عر", "flag": "sa"},
    {"code": "ur-PK", "label": "اردو", "flag": "pk"},
    {"code": "hi-IN", "label": "हि", "flag": "in"},
    {"code": "ta-IN", "label": "தமி", "flag": "in"},
    {"code": "bn-IN", "label": "বাং", "flag": "in"},
]


class MarianTranslationService(TranslationService):
    MODEL_NAME = "Helsinki-NLP/opus-mt-mul-en"

    def __init__(self) -> None:
        self._tokenizer: MarianTokenizer | None = None
        self._model: MarianMTModel | None = None

    def _load(self) -> None:
        if self._model is None:
            log.info("Loading translation model %s (first non-EN/ML query)", self.MODEL_NAME)
            self._tokenizer = MarianTokenizer.from_pretrained(self.MODEL_NAME)
            self._model = MarianMTModel.from_pretrained(self.MODEL_NAME)
            log.info("Translation model ready")

    def translate(self, text: str, source_lang: str = "") -> TranslationResult:
        # Normalise BCP-47 (e.g. "fr-FR") to ISO 639-1 prefix (e.g. "fr")
        iso = source_lang.split("-")[0].lower() if source_lang else "en"

        if iso in _SKIP_PREFIXES or iso not in _LANG_NAMES:
            return TranslationResult(text=text, source_lang=iso, was_translated=False)

        self._load()
        inputs = self._tokenizer(  # type: ignore[misc]
            [text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        translated_ids = self._model.generate(**inputs)  # type: ignore[union-attr]
        translated = self._tokenizer.batch_decode(  # type: ignore[union-attr]
            translated_ids, skip_special_tokens=True
        )[0]

        return TranslationResult(
            text=translated,
            source_lang=iso,
            was_translated=True,
            source_lang_name=_LANG_NAMES[iso],
        )

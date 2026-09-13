"""Helsinki-NLP/opus-mt-mul-en translation service.

Lazy-loads the model on first non-EN/ML request so API startup stays fast.
The caller supplies the source language (from the UI selector); a lightweight
langdetect check (see ``_detect_mismatch``) only ever corrects the two
"skip translation" declarations (en/ml) when the text is confidently a
different supported language — it never overrides an explicit real-language
choice. To switch backends, implement TranslationService and set
TRANSLATION_BACKEND to the new key in build_translation_service().
"""

import logging

from langdetect import DetectorFactory, LangDetectException, detect_langs
from transformers import MarianMTModel, MarianTokenizer

from linguaalayam.translation.base import TranslationResult, TranslationService

log = logging.getLogger(__name__)

# langdetect's algorithm samples internally; seed it so the same query always
# gets the same verdict instead of flapping between requests.
DetectorFactory.seed = 0

_SKIP_PREFIXES = {"en", "ml"}

# Below this word count, langdetect is unreliable and this dictionary's primary
# use case (single-word headword lookup) lives — never second-guess the flag there.
_MIN_WORDS_FOR_MISMATCH_CHECK = 2

# High bar so a genuine but ambiguous English/Malayalam query never gets
# reclassified on a coin-flip — this check only exists to catch confident,
# unambiguous mismatches (e.g. a full German sentence typed with "ml" still
# selected from a previous query).
_MIN_MISMATCH_CONFIDENCE = 0.90

# ISO 639-1 code → human-readable name for the UI indicator (and, in web.py,
# for telling the AI synthesis LLM which language to answer in).
# Add entries here when switching to a model that covers more languages.
LANG_NAMES: dict[str, str] = {
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


def _detect_mismatch(text: str, declared_iso: str) -> str | None:
    """Return a corrected ISO code if ``text`` confidently looks like a different
    supported language than ``declared_iso`` claims — otherwise ``None``.

    The input-language flag now drives both speech recognition (where the
    transcript is guaranteed to match the selected locale) and typed queries
    (where nothing stops a user from typing anything regardless of what the
    flag says — e.g. leaving it on "ml" from a previous query and then typing
    a German sentence). Only overrides the two "skip translation" claims
    (en/ml); an explicit choice of a real target language is trusted as-is.

    Parameters
    ----------
    text : str
        The raw query text as typed or transcribed.
    declared_iso : str
        The ISO 639-1 code the input-language flag claims.

    Returns
    -------
    str or None
        The detected ISO code, if it should override ``declared_iso``.
    """
    if declared_iso not in _SKIP_PREFIXES or len(text.split()) < _MIN_WORDS_FOR_MISMATCH_CHECK:
        return None
    try:
        candidates = detect_langs(text)
    except LangDetectException:
        return None
    if not candidates:
        return None
    top = candidates[0]
    detected = top.lang.split("-")[0]  # langdetect uses "zh-cn"/"zh-tw" for Mandarin
    if top.prob >= _MIN_MISMATCH_CONFIDENCE and detected in LANG_NAMES:
        return detected
    return None


class MarianTranslationService(TranslationService):
    """TranslationService backed by Helsinki-NLP/opus-mt-mul-en via HuggingFace."""

    MODEL_NAME = "Helsinki-NLP/opus-mt-mul-en"

    def __init__(self) -> None:
        self._tokenizer: MarianTokenizer | None = None
        self._model: MarianMTModel | None = None

    def _load(self) -> None:
        """Lazily load the tokenizer and model on first non-EN/ML request."""
        if self._model is None:
            log.info("Loading translation model %s (first non-EN/ML query)", self.MODEL_NAME)
            self._tokenizer = MarianTokenizer.from_pretrained(self.MODEL_NAME)
            self._model = MarianMTModel.from_pretrained(self.MODEL_NAME)
            log.info("Translation model ready")

    def translate(self, text: str, source_lang: str = "") -> TranslationResult:
        """Translate ``text`` into English using the Marian MT model.

        Parameters
        ----------
        text : str
            Input text to translate.
        source_lang : str, optional
            BCP-47 or ISO 639-1 source language code (e.g. ``"fr-FR"`` or
            ``"fr"``).  English (``"en-*"``) and Malayalam (``"ml-*"``) are
            returned unchanged without loading the model, unless the text is
            confidently detected as a different supported language (see
            ``_detect_mismatch``).

        Returns
        -------
        TranslationResult
            Translated text with ``was_translated=True``, or the original text
            with ``was_translated=False`` when no translation is needed.
        """
        # Normalise BCP-47 (e.g. "fr-FR") to ISO 639-1 prefix (e.g. "fr")
        iso = source_lang.split("-")[0].lower() if source_lang else "en"

        mismatch = _detect_mismatch(text, iso)
        if mismatch:
            log.info(
                "Input-language flag said %r but %r was detected with high confidence "
                "— translating as %r instead",
                iso,
                mismatch,
                mismatch,
            )
            iso = mismatch

        if iso in _SKIP_PREFIXES or iso not in LANG_NAMES:
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
            source_lang_name=LANG_NAMES[iso],
        )

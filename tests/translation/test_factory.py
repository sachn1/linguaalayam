"""Tests for translation/__init__.py's factory and the noop backend."""

import pytest

from linguaalayam.translation import build_translation_service
from linguaalayam.translation.marian import MarianTranslationService
from linguaalayam.translation.noop import NoOpTranslationService


class TestBuildTranslationService:
    """build_translation_service backend selection."""

    def test_default_backend_is_noop(self):
        """Default should be noop — Marian is disabled until a better model
        is evaluated (see docs/roadmap.md's backlog)."""
        assert isinstance(build_translation_service(), NoOpTranslationService)

    def test_noop_backend_explicit(self):
        assert isinstance(build_translation_service("noop"), NoOpTranslationService)

    def test_marian_backend_still_available(self):
        """Marian must stay instantiable — re-enabling is a one-line env var
        change (TRANSLATION_BACKEND=marian), not a revert."""
        assert isinstance(build_translation_service("marian"), MarianTranslationService)

    def test_unknown_backend_raises(self):
        with pytest.raises(ValueError):
            build_translation_service("deepl")


class TestNoOpTranslationService:
    """NoOpTranslationService never translates, regardless of declared language."""

    def test_passes_text_through_unchanged(self):
        svc = NoOpTranslationService()
        result = svc.translate("कुत्ता तेज़ दौड़ता है", source_lang="hi-IN")
        assert result.text == "कुत्ता तेज़ दौड़ता है"
        assert result.was_translated is False

    def test_normalizes_bcp47_to_iso_639_1(self):
        svc = NoOpTranslationService()
        result = svc.translate("hello", source_lang="de-DE")
        assert result.source_lang == "de"

    def test_defaults_to_en_with_no_source_lang(self):
        svc = NoOpTranslationService()
        result = svc.translate("hello")
        assert result.source_lang == "en"

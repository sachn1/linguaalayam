"""Tests for translation/marian.py — the input-language mismatch guard."""

from linguaalayam.translation.marian import _detect_mismatch


class TestDetectMismatch:
    """_detect_mismatch only overrides a stale/wrong en or ml flag, confidently."""

    def test_catches_foreign_language_typed_under_ml_flag(self):
        """A German sentence typed while the flag is still on "ml" is caught."""
        assert _detect_mismatch("Wie geht es dir heute", "ml") == "de"

    def test_catches_foreign_language_typed_under_en_flag(self):
        """Same mismatch, but against the "en" flag."""
        assert _detect_mismatch("Guten Morgen mein Freund", "en") == "de"

    def test_no_override_when_text_matches_declared_language(self):
        """English text under the "en" flag is not a mismatch."""
        assert _detect_mismatch("how are you doing today", "ml") is None

    def test_no_override_for_single_word(self):
        """Below the word-count floor, detection is skipped — this is the
        dictionary's primary single-word headword lookup use case, where
        language detection is unreliable and shouldn't second-guess the flag."""
        assert _detect_mismatch("Hallo", "ml") is None

    def test_no_override_for_real_malayalam_text(self):
        """Malayalam script isn't a supported *translation target* (LANG_NAMES
        holds only languages Marian translates from), so it's never used as
        an override — the caller's own script check handles Malayalam directly."""
        assert _detect_mismatch("ഞാൻ നാളെ വരും", "en") is None

    def test_no_override_for_explicit_real_language_choice(self):
        """An explicit choice of a real target language (not en/ml) is trusted
        as-is and never second-guessed, even if the text doesn't match it."""
        assert _detect_mismatch("bonjour mon ami comment allez vous", "de") is None

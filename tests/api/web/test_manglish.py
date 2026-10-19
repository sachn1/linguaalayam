"""Unit tests for linguaalayam.api.web.manglish."""

from unittest.mock import MagicMock, patch

from linguaalayam.api.web.manglish import resolve_manglish
from linguaalayam.translation.base import TranslationResult


def _result(headword: str, source: str = "olam_enml", match_type: str = "exact") -> dict:
    return {
        "headword": headword,
        "source": source,
        "entry_type": "OlamEntry",
        "embed_text": "",
        "data": {},
        "match_type": match_type,
        "score": 1.0,
    }


def test_skips_entirely_for_non_latin_headword():
    tools = MagicMock()
    resolution = resolve_manglish(
        "ഓടുക", [], translation=None, request=MagicMock(), tools=tools, src=None
    )
    assert resolution.headword == "ഓടുക"
    tools.exact_lookup.assert_not_called()


def test_skips_when_translation_already_ran():
    """A translated query is real English by construction, not a Manglish guess."""
    tools = MagicMock()
    translation = TranslationResult(text="run", source_lang="de", was_translated=True)
    resolution = resolve_manglish(
        "run", [], translation=translation, request=MagicMock(), tools=tools, src=None
    )
    assert resolution.headword == "run"
    tools.exact_lookup.assert_not_called()


def test_lowercases_before_varnam_to_avoid_capitalization_doubling():
    """A capitalized word must be lowercased before Varnam, which treats a capital as doubling."""
    tools = MagicMock()
    tools.exact_lookup.return_value = []
    tools.lemma_lookup.return_value = []
    with patch(
        "linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]
    ) as mock_varnam:
        resolve_manglish("Kali", [], translation=None, request=MagicMock(), tools=tools, src=None)
    mock_varnam.assert_called_once_with("kali")


def test_already_confident_result_offers_manglish_as_secondary_suggestion():
    """A word valid in both languages keeps its confident result, Manglish becomes a suggestion."""
    tools = MagicMock()
    tools.exact_lookup.return_value = [_result("കലി", source="datuk")]
    english_results = [_result("kali", match_type="exact")]
    with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=["കലി"]):
        resolution = resolve_manglish(
            "kali", english_results, translation=None, request=MagicMock(), tools=tools, src=None
        )
    assert resolution.headword == "kali"
    assert resolution.results == english_results
    assert resolution.varnam_used is False
    assert resolution.manglish_suggestions == ["കലി"]


def test_not_already_confident_becomes_the_primary_result():
    tools = MagicMock()
    tools.exact_lookup.return_value = [_result("ഓടുക", source="datuk")]
    with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=["ഓടുക"]):
        resolution = resolve_manglish(
            "oduka", [], translation=None, request=MagicMock(), tools=tools, src=None
        )
    assert resolution.headword == "ഓടുക"
    assert resolution.varnam_used is True
    assert resolution.results == [_result("ഓടുക", source="datuk")]


def test_candidates_validated_via_exact_or_lemma_not_fuzzy():
    """A candidate is validated via exact/lemma lookup, never fuzzy_lookup."""
    tools = MagicMock()
    tools.exact_lookup.return_value = []
    tools.lemma_lookup.return_value = []
    with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=["ഓടുക"]):
        resolve_manglish("oduka", [], translation=None, request=MagicMock(), tools=tools, src=None)
    tools.fuzzy_lookup.assert_not_called()


def test_no_candidates_leaves_input_unchanged():
    tools = MagicMock()
    tools.exact_lookup.return_value = []
    tools.lemma_lookup.return_value = []
    with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]):
        resolution = resolve_manglish(
            "xyzzy", [], translation=None, request=MagicMock(), tools=tools, src=None
        )
    assert resolution.headword == "xyzzy"
    assert resolution.varnam_used is False
    assert resolution.manglish_suggestions == []

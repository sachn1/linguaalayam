"""Unit tests for transliteration helpers."""

from linguaalayam.transliteration import (
    is_latin_script,
    malayalam_to_roman,
    normalize_roman,
    roman_to_malayalam_candidates,
)


def test_malayalam_to_roman_basic():
    result = malayalam_to_roman("ഓടുക")
    assert isinstance(result, str)
    assert len(result) > 0
    # Result is Roman script — no Malayalam Unicode block characters
    assert not any("ഀ" <= c <= "ൿ" for c in result)


def test_normalize_roman_strips_diacritics():
    assert normalize_roman("ōṭuka") == "otuka"
    assert normalize_roman("ĀB") == "ab"


def test_normalize_roman_plain_passthrough():
    assert normalize_roman("run") == "run"


def test_is_latin_script_latin():
    assert is_latin_script("run") is True
    assert is_latin_script("oduka") is True
    assert is_latin_script("hello world") is True


def test_is_latin_script_malayalam():
    assert is_latin_script("ഓടുക") is False
    assert is_latin_script("ഒരു ജലസ്ഥലം") is False


def test_is_latin_script_empty():
    assert is_latin_script("") is False


def test_is_latin_script_mixed():
    assert is_latin_script("run ഓടുക") is False


def test_roman_to_malayalam_candidates_returns_list():
    result = roman_to_malayalam_candidates("oduka")
    assert isinstance(result, list)


def test_roman_to_malayalam_candidates_unique():
    result = roman_to_malayalam_candidates("ka")
    assert len(result) == len(set(result))


def test_roman_to_malayalam_candidates_all_different_from_input():
    result = roman_to_malayalam_candidates("vellam")
    for candidate in result:
        assert candidate != "vellam"

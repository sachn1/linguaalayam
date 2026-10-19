"""Static locale bundle tests — unrelated to the search pipeline itself."""

import json
from pathlib import Path

_LOCALES = Path(__file__).resolve().parents[3] / "linguaalayam/static/locales"


def test_locale_files_exist():
    assert (_LOCALES / "en.json").exists()
    assert (_LOCALES / "ml.json").exists()


def test_locale_key_parity():
    en = json.loads((_LOCALES / "en.json").read_text())
    ml = json.loads((_LOCALES / "ml.json").read_text())
    diff = set(en.keys()) ^ set(ml.keys())
    assert not diff, f"locale key mismatch: {diff}"


def test_locale_no_empty_values():
    for name in ("en.json", "ml.json"):
        data = json.loads((_LOCALES / name).read_text())
        empty = [k for k, v in data.items() if not str(v).strip()]
        assert not empty, f"{name} has empty values: {empty}"


def test_locale_json_valid():
    for name in ("en.json", "ml.json"):
        content = (_LOCALES / name).read_text()
        json.loads(content)  # raises if invalid

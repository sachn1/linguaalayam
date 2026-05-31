"""Tests for HTMX web routes and static locale bundles."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from linguaalayam.api.app import app

_LOCALES = Path(__file__).resolve().parents[2] / "linguaalayam/static/locales"


@pytest.fixture()
def mock_tools():
    t = MagicMock()
    t.exact_lookup.return_value = []
    t.fuzzy_lookup.return_value = []
    t.semantic_lookup.return_value = []
    return t


@pytest.fixture()
def client(mock_tools):
    with patch("linguaalayam.api.web.get_tools", return_value=mock_tools):
        yield TestClient(app, raise_server_exceptions=True)


# ── route smoke tests ──────────────────────────────────────────────────────────

def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "Lingu" in r.text


def test_search_empty_query(client):
    r = client.get("/search")
    assert r.status_code == 200


def test_search_fuzzy(client, mock_tools):
    r = client.get("/search?query=run&mode=fuzzy")
    assert r.status_code == 200
    mock_tools.fuzzy_lookup.assert_called_once()


def test_search_exact(client, mock_tools):
    r = client.get("/search?query=run&mode=exact")
    assert r.status_code == 200
    mock_tools.exact_lookup.assert_called_once()


def test_search_semantic(client, mock_tools):
    r = client.get("/search?query=run&mode=semantic")
    assert r.status_code == 200
    mock_tools.semantic_lookup.assert_called_once()


def test_search_with_source_filter(client, mock_tools):
    r = client.get("/search?query=run&mode=fuzzy&source=olam_enml")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") == "olam_enml"


def test_search_no_results_shows_empty_state(client):
    r = client.get("/search?query=xyzzy_nonexistent")
    assert r.status_code == 200
    assert "No results" in r.text


# ── locale bundle tests ────────────────────────────────────────────────────────

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

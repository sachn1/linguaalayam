"""Shared fixtures for linguaalayam.api.web's test package."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from linguaalayam.api.app import app
from linguaalayam.api.web.decomposition import GroundedAnswer
from linguaalayam.rag.query_understanding import QueryUnderstanding
from linguaalayam.translation.base import TranslationResult


def passthrough_translation(text: str, source_lang: str = "en-US") -> TranslationResult:
    """Stub translator that returns the input unchanged (no translation needed)."""
    iso = source_lang.split("-")[0].lower()
    return TranslationResult(text=text, source_lang=iso, was_translated=False)


def extract_structured_side_effect(headword: str, grounded_answer: GroundedAnswer):
    """Dispatch a mocked ``extract_structured`` by schema — QueryUnderstanding or GroundedAnswer."""

    def side_effect(schema, _prompt):
        if schema is QueryUnderstanding:
            return QueryUnderstanding(headword=headword, intent="unknown")
        return grounded_answer

    return side_effect


@pytest.fixture()
def mock_tools():
    t = MagicMock()
    t.exact_lookup.return_value = []
    t.fuzzy_lookup.return_value = []
    t.lemma_lookup.return_value = []
    t.semantic_lookup.return_value = []
    t.ml_headword_set.return_value = frozenset()
    return t


@pytest.fixture()
def mock_translator():
    t = MagicMock()
    t.translate.side_effect = passthrough_translation
    t.supports_translation = False  # matches the real default backend ("noop")
    return t


@pytest.fixture()
def client(mock_tools, mock_translator):
    with (
        patch("linguaalayam.api.web.routes.get_tools", return_value=mock_tools),
        patch("linguaalayam.api.web.routes.get_translator", return_value=mock_translator),
    ):
        yield TestClient(app, raise_server_exceptions=True)

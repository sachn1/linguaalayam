"""Tests for HTMX web routes and static locale bundles."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from linguaalayam.api.app import app
from linguaalayam.api.web import _decompose_and_lookup, _format_word_entries
from linguaalayam.rag.query_understanding import QueryUnderstanding
from linguaalayam.translation.base import TranslationResult

_LOCALES = Path(__file__).resolve().parents[2] / "linguaalayam/static/locales"


def _passthrough_translation(text: str, source_lang: str = "en-US") -> TranslationResult:
    """Stub translator that returns the input unchanged (no translation needed)."""
    iso = source_lang.split("-")[0].lower()
    return TranslationResult(text=text, source_lang=iso, was_translated=False)


def _result(headword: str = "run", source: str = "olam_enml", match_type: str = "fuzzy") -> dict:
    """Build a minimal result dict shaped like DictionaryTools' _to_result output."""
    return {
        "headword": headword,
        "source": source,
        "entry_type": "OlamEntry",
        "embed_text": "",
        "data": {"definitions": [("v", "ഓടുക")]},
        "match_type": match_type,
        "score": 1.0,
    }


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
    t.translate.side_effect = _passthrough_translation
    t.supports_translation = False  # matches the real default backend ("noop")
    return t


@pytest.fixture()
def client(mock_tools, mock_translator):
    with (
        patch("linguaalayam.api.web.get_tools", return_value=mock_tools),
        patch("linguaalayam.api.web.get_translator", return_value=mock_translator),
    ):
        yield TestClient(app, raise_server_exceptions=True)


# ── route smoke tests ──────────────────────────────────────────────────────────


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "lingu" in r.text


def test_index_hides_non_en_ml_langs_when_translation_disabled(client, mock_translator):
    """With a noop translator (the default), the input-language picker should
    only offer EN/ML — any other language has no honest path to a result
    since nothing actually translates it before search."""
    mock_translator.supports_translation = False
    r = client.get("/")
    assert r.status_code == 200
    assert "'de-DE'" not in r.text
    assert "'ta-IN'" not in r.text


def test_index_shows_full_lang_list_when_translation_enabled(client, mock_translator):
    """With a real translation backend, the full language list should render."""
    mock_translator.supports_translation = True
    r = client.get("/")
    assert r.status_code == 200
    assert "'de-DE'" in r.text
    assert "'ta-IN'" in r.text


def test_search_empty_query(client, mock_tools):
    """Regression: an empty query used to raise UnboundLocalError on `tools`
    (only assigned inside `if q:`, but used unconditionally for ml_headword_set())."""
    r = client.get("/search")
    assert r.status_code == 200
    mock_tools.ml_headword_set.assert_called_once()


def test_search_single_word_uses_fuzzy(client, mock_tools):
    mock_tools.fuzzy_lookup.return_value = [_result()]  # results found — no fallback
    r = client.get("/search?query=run")
    assert r.status_code == 200
    mock_tools.fuzzy_lookup.assert_called_once()
    mock_tools.semantic_lookup.assert_not_called()


def test_search_no_results_shows_empty_state(client):
    r = client.get("/search?query=xyzzy_nonexistent")
    assert r.status_code == 200
    assert "No results" in r.text


# ── lemma-match suppression of coincidental spelling matches ───────────────────
#
# This used to be web.py's own post-processing step (merging a separate
# tools.lemma_lookup() call with tools.fuzzy_lookup() and filtering the
# result). It's now built into DictionaryTools.fuzzy_lookup() itself, so
# every caller gets it for free — see
# tests/rag/test_tools.py::test_fuzzy_lookup_prefers_lemma_over_edit_distance_for_same_headword
# and ::test_fuzzy_lookup_drops_unrelated_edit_distance_hits_once_lemma_found for
# the real coverage. web.py now just passes fuzzy_lookup's result through
# unchanged, which is exactly what test_search_no_lemma_signal_keeps_all_fuzzy_matches
# below already confirms.


def test_search_no_lemma_signal_keeps_all_fuzzy_matches(client, mock_tools):
    """With no lemma match anywhere (the common case — most queries are already
    base forms or aren't Malayalam at all), plain-fuzzy results are unaffected."""
    mock_tools.fuzzy_lookup.return_value = [
        _result(headword="run", match_type="fuzzy"),
        _result(headword="ran", source="datuk", match_type="fuzzy"),
    ]
    r = client.get("/search?query=run")
    assert r.status_code == 200
    assert "run" in r.text
    assert "ran" in r.text


# ── routing: edit distance only, semantic retired from the web path ───────────
#
# semantic_lookup used to be web.py's multi-word router and its single-word
# fallback. Both were removed: the multi-word rule routed on word count alone,
# which meant a literal, confidently-matchable multi-word headword (e.g. a
# Marian-translated phrase like "Sit down.") never got a chance at fuzzy_lookup
# at all. And semantic's own display-confidence threshold (0.80) was only ever
# calibrated for edit distance, never independently validated for cosine
# similarity — see memory/fuzzy_matching_threshold_research.md. semantic_lookup
# is still live for MCP's own tool (linguaalayam/mcp/server.py), untouched here.


def test_search_multiword_uses_fuzzy_not_semantic(client, mock_tools):
    """Multi-word queries now go through fuzzy_lookup like any other query —
    word count alone no longer routes straight to semantic."""
    mock_tools.fuzzy_lookup.return_value = [_result(headword="ഒരു ജലസ്ഥലം")]
    r = client.get("/search?query=ഒരു+ജലസ്ഥലം")
    assert r.status_code == 200
    mock_tools.fuzzy_lookup.assert_called_once()
    mock_tools.semantic_lookup.assert_not_called()


def test_search_no_fuzzy_results_stays_empty_not_semantic(client, mock_tools):
    """A query with no fuzzy results should show the empty state, not fall
    back to semantic_lookup — that fallback no longer exists on the web path."""
    r = client.get("/search?query=xyzzy")
    assert r.status_code == 200
    assert "No results" in r.text
    mock_tools.semantic_lookup.assert_not_called()


# ── manglish / varnam fallback ────────────────────────────────────────────────


def test_search_latin_no_results_tries_varnam(client, mock_tools):
    """A Latin-script query with no fuzzy/semantic hits should try Varnam candidates."""
    with patch(
        "linguaalayam.transliteration.varnam.manglish_to_malayalam",
        return_value=["ഓടുക"],
    ) as mock_varnam:
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    mock_varnam.assert_called_once_with("oduka")


def test_search_varnam_success_sets_headword(client, mock_tools):
    """When Varnam returns a candidate that exists (exact/lemma), headword should update to it."""
    mock_tools.exact_lookup.return_value = [
        _result(headword="ഓടുക", source="datuk", match_type="exact")
    ]
    with patch(
        "linguaalayam.transliteration.varnam.manglish_to_malayalam",
        return_value=["ഓടുക"],
    ):
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    assert "ഓടുക" in r.text


def test_search_varnam_unavailable_falls_back_to_local_schemes(client, mock_tools):
    """If Varnam returns no candidates, fall back to local roman_to_malayalam_candidates."""
    with (
        patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]),
        patch(
            "linguaalayam.api.web.roman_to_malayalam_candidates",
            return_value=["ഓടുക"],
        ) as mock_local,
    ):
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    mock_local.assert_called_once_with("oduka")


def test_search_manglish_fallback_skipped_when_translated(client, mock_tools, mock_translator):
    """A translated query should skip the Manglish fallback — it's real English, not Manglish."""
    mock_translator.translate.side_effect = lambda text, source_lang="en-US": TranslationResult(
        text="run", source_lang="de", was_translated=True
    )
    with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam") as mock_varnam:
        r = client.get("/search?query=laufen&lang=de-DE")
    assert r.status_code == 200
    mock_varnam.assert_not_called()


# ── source mapping ────────────────────────────────────────────────────────────


def test_search_ml_ml_source_maps_to_list(client, mock_tools):
    """source=ml_ml in the UI should query both datuk and sayahna corpora."""
    mock_tools.fuzzy_lookup.return_value = [_result(source="datuk")]
    r = client.get("/search?query=run&source=ml_ml")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") == ["datuk", "sayahna"]


def test_search_olam_source_passes_string(client, mock_tools):
    """Non-ml_ml source values should be forwarded as a plain string."""
    mock_tools.fuzzy_lookup.return_value = [_result()]
    r = client.get("/search?query=run&source=olam_enml")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") == "olam_enml"


def test_search_empty_source_passes_none(client, mock_tools):
    """An empty source param should forward None (search all corpora)."""
    mock_tools.fuzzy_lookup.return_value = [_result()]
    r = client.get("/search?query=run&source=")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") is None


# ── language parameter ─────────────────────────────────────────────────────────


def test_search_lang_param_accepted(client, mock_translator):
    """lang parameter should be accepted and forwarded to the translator."""
    r = client.get("/search?query=laufen&lang=de-DE")
    assert r.status_code == 200
    mock_translator.translate.assert_called_once_with("laufen", source_lang="de-DE")


def test_search_default_lang_is_en(client, mock_translator):
    """Omitting lang should default to en-US and pass it to the translator."""
    r = client.get("/search?query=run")
    assert r.status_code == 200
    _, kwargs = mock_translator.translate.call_args
    assert kwargs.get("source_lang") == "en-US"


# ── AI Answer hint ────────────────────────────────────────────────────────────


def test_search_shows_ai_hint_for_long_query_without_ai(client, mock_tools):
    """A long/sentence-like query with AI off and a confident result should surface
    the 'turn on AI Answer' hint instead of a synthesized answer — the softer 'weak'
    variant, since a real (if possibly not-what-they-meant) answer is already shown."""
    mock_tools.fuzzy_lookup.return_value = [_result(match_type="exact")]
    r = client.get("/search?query=ജലജന്തു+എന്ന+വാക്ക്+വിഗ്രഹിക്കുക")
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' in r.text
    assert "Not quite what you meant?" in r.text
    assert '<p class="answer-label">' not in r.text


def test_search_no_ai_hint_for_short_query(client, mock_tools):
    """A short (< 3 word) query shouldn't trigger the AI hint even without AI enabled —
    single-headword lookups are exactly what raw entries already answer well."""
    mock_tools.fuzzy_lookup.return_value = [_result(match_type="exact")]
    r = client.get("/search?query=run")
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' not in r.text


def test_search_no_ai_hint_when_ai_already_enabled(client, mock_tools):
    """No hint should show once AI Answer is already on — the answer card takes its place."""
    mock_tools.fuzzy_lookup.return_value = [_result(match_type="exact")]
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "synthesized answer"
    # This query is multi-word Malayalam text that no regex pattern in
    # query_understanding.py matches, so understand_query() falls through to
    # llm.extract_structured(). Without a configured return value that call
    # yields a bare MagicMock instead of a QueryUnderstanding, so `headword`
    # downstream is a MagicMock too — it then sails past every truthy/bool
    # check in search()'s Manglish-detection branch (MagicMock.__iter__
    # defaults to an empty iterator, so `is_latin_script` and friends don't
    # even raise) and reaches the real Varnam transliteration call with
    # garbage input, which spins for minutes. Give the mock a real return
    # value so it behaves like the actual LLM adapter would.
    mock_llm.extract_structured.return_value = QueryUnderstanding(
        headword="ജലജന്തു എന്ന വാക്ക് വിഗ്രഹിക്കുക", intent="define"
    )
    with patch("linguaalayam.api.web._get_server_llm", return_value=mock_llm):
        r = client.get(
            "/search?query=ജലജന്തു+എന്ന+വാക്ക്+വിഗ്രഹിക്കുക",
            headers={"X-LLM-Enabled": "1"},
        )
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' not in r.text
    assert "synthesized answer" in r.text


def test_search_shows_ai_hint_even_without_confident_result(client, mock_tools):
    """A weak-only fuzzy match (below the display threshold) should still trigger the
    hint — a poor raw match is exactly when AI Answer would help most, so the nudge
    isn't gated on how confident the underlying dictionary lookup was. This is the
    "empty" variant, since nothing confident is actually displayed."""
    mock_tools.fuzzy_lookup.return_value = [{**_result(match_type="fuzzy"), "score": 0.2}]
    r = client.get("/search?query=ജലജന്തു+എന്ന+വാക്ക്+വിഗ്രഹിക്കുക")
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' in r.text
    assert "Nothing confident found" in r.text


# ── AI Answer synthesis gating ──────────────────────────────────────────────────


def test_search_skips_ai_for_short_confident_query(client, mock_tools):
    """AI Answer should not fire for a short query with an already-confident match —
    raw entries already answer it as well as a paraphrase would."""
    mock_tools.lemma_lookup.return_value = []
    mock_tools.fuzzy_lookup.return_value = [_result(headword="നീന്തുക", match_type="exact")]
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "should not be called"
    with patch("linguaalayam.api.web._get_server_llm", return_value=mock_llm):
        r = client.get("/search?query=നീന്തുക", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert '<p class="answer-label">' not in r.text
    mock_llm.complete.assert_not_called()


def test_search_still_synthesizes_short_query_without_confident_result(client, mock_tools):
    """A short query without a confident match should still get AI Answer — there's
    real ambiguity here for synthesis to resolve, unlike a clean exact hit."""
    mock_tools.fuzzy_lookup.return_value = [{**_result(match_type="fuzzy"), "score": 0.3}]
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "synthesized answer"
    with patch("linguaalayam.api.web._get_server_llm", return_value=mock_llm):
        r = client.get("/search?query=run", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert "synthesized answer" in r.text


# ── phrase decomposition for AI Answer ──────────────────────────────────────────
#
# When the whole-phrase lookup finds nothing confident, _decompose_and_lookup()
# splits the query into words and looks each up individually — real headword
# first (fuzzy_lookup), Manglish/Varnam fallback for a Latin-script word that
# isn't one — so AI Answer can stitch a compositional meaning instead of
# answering from nothing. Never touches the raw/no-AI results list.


def _entry(headword: str, embed_text: str, source: str = "datuk") -> dict:
    """A per-word lookup result, shaped like DictionaryTools' _to_result output."""
    return {
        "headword": headword,
        "source": source,
        "entry_type": "DatukEntry",
        "embed_text": embed_text,
        "data": {},
        "match_type": "exact",
        "score": 1.0,
    }


class TestDecomposeAndLookup:
    """_decompose_and_lookup's per-word resolution logic, unit-tested directly."""

    def test_uses_fuzzy_first_per_word(self):
        """A word that's already a real headword resolves via fuzzy_lookup,
        no Varnam fallback needed."""
        tools = MagicMock()
        tools.fuzzy_lookup.side_effect = lambda word, **_: (
            [_entry("run", "to move quickly")] if word == "run" else []
        )
        with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]):
            found, _trace = _decompose_and_lookup("run fast", tools, None)
        assert found == [("run", [_entry("run", "to move quickly")])]

    def test_falls_back_to_varnam_for_latin_word(self):
        """A Latin-script word with no real-headword match tries Manglish —
        same precedence search() already uses for the whole phrase."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = []
        tools.exact_lookup.side_effect = lambda candidate, **_: (
            [_entry("ഇരിക്കുക", "to sit")] if candidate == "ഇരിക്കുക" else []
        )
        tools.lemma_lookup.return_value = []
        with patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            return_value=["ഇരിക്കുക"],
        ):
            found, trace = _decompose_and_lookup("irikkoo", tools, None)
        assert found == [("irikkoo", [_entry("ഇരിക്കുക", "to sit")])]
        assert trace == [
            {
                "word": "irikkoo",
                "fuzzy_senses": [],
                "varnam_candidates": ["ഇരിക്കുക"],
                "chosen_candidate": "ഇരിക്കുക",
                "final_senses": [_entry("ഇരിക്കുക", "to sit")],
            }
        ]

    def test_carries_multiple_senses_per_word_not_just_the_first(self):
        """A polysemous word (e.g. ഇരിക്കുക has both a "to sit" sense and a
        grammatical-auxiliary sense) should surface more than one sense, so
        the LLM can pick the one that actually fits — not be stuck with
        whichever one a DB query happened to return first."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = [
            _entry("ഇരിക്കുക", "an auxiliary verb usage"),
            _entry("ഇരിക്കുക", "to sit"),
        ]
        found, _trace = _decompose_and_lookup("irikkoo", tools, None)
        assert found == [
            ("irikkoo", [_entry("ഇരിക്കുക", "an auxiliary verb usage"), _entry("ഇരിക്കുക", "to sit")])
        ]

    def test_caps_senses_per_word_at_max(self):
        """fuzzy_lookup's own top_k is capped at _MAX_SENSES_PER_WORD, not
        left unbounded."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = []
        _decompose_and_lookup("irikkoo", tools, None)
        _, kwargs = tools.fuzzy_lookup.call_args
        assert kwargs["top_k"] == 3

    def test_skips_words_with_no_match_anywhere(self):
        """A word that resolves nowhere (not a real headword, not valid
        Manglish) is simply omitted, not included as an error/placeholder."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = []
        tools.exact_lookup.return_value = []
        tools.lemma_lookup.return_value = []
        with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]):
            found, trace = _decompose_and_lookup("xyzzy run", tools, None)
        assert found == []
        # The trace still records both words were tried and found nothing —
        # the debug view shows this, rather than silently omitting them.
        assert [t["word"] for t in trace] == ["xyzzy", "run"]
        assert all(t["final_senses"] == [] for t in trace)

    def test_caps_at_max_decomposition_words(self):
        """A pathologically long input only looks up the first 8 words."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = []
        words = " ".join(f"word{i}" for i in range(20))
        _decompose_and_lookup(words, tools, None)
        assert tools.fuzzy_lookup.call_count == 8


class TestFormatWordEntries:
    def test_tags_each_entry_with_its_source_word(self):
        text = _format_word_entries(
            [
                ("dayavayi", [_entry("ദയ", "mercy, kindness")]),
                ("sahodara", [_entry("സഹോദരൻ", "brother")]),
            ]
        )
        assert '"dayavayi":' in text
        assert "-> ദയ" in text
        assert "mercy, kindness" in text
        assert '"sahodara":' in text
        assert "-> സഹോദരൻ" in text
        assert "brother" in text

    def test_lists_every_sense_for_a_polysemous_word(self):
        text = _format_word_entries(
            [("irikkoo", [_entry("ഇരിക്കുക", "an auxiliary verb usage"), _entry("ഇരിക്കുക", "to sit")])]
        )
        assert "an auxiliary verb usage" in text
        assert "to sit" in text


def test_search_decomposes_manglish_phrase_for_ai_answer(client, mock_tools):
    """The motivating case: a Manglish phrase with no whole-phrase match at
    all should still get a stitched AI Answer from per-word lookups, while
    the raw results list stays genuinely empty."""
    mock_tools.fuzzy_lookup.return_value = []  # no match for the whole phrase or any word
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: {
        "ദയ": [_entry("ദയ", "mercy, kindness")],
        "ഇരിക്കുക": [
            _entry("ഇരിക്കുക", "an auxiliary verb usage"),
            _entry("ഇരിക്കുക", "to sit"),
        ],
        "സഹോദരൻ": [_entry("സഹോദരൻ", "brother")],
    }.get(candidate, [])
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "please sit, brother"
    mock_llm.extract_structured.return_value = QueryUnderstanding(
        headword="Dayavayi Irikkoo sahodara", intent="unknown"
    )

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"], "sahodara": ["സഹോദരൻ"]}.get(word, [])

    with (
        patch("linguaalayam.api.web._get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=varnam_side_effect,
        ),
    ):
        r = client.get("/search?query=Dayavayi+Irikkoo+sahodara", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert "please sit, brother" in r.text
    assert "No results" in r.text  # raw results list untouched, still empty

    # The LLM should have been given the looser, know-your-own-knowledge system
    # prompt (not the strict dictionary-only one used for a real phrase match),
    # and both senses of the polysemous word, not just the first.
    system_prompt, content = mock_llm.complete.call_args[0]
    assert "trust that recognition over the dictionary text" in system_prompt
    assert "an auxiliary verb usage" in content
    assert "to sit" in content

    content = mock_llm.complete.call_args[0][1]
    assert "ദയ" in content
    assert "ഇരിക്കുക" in content
    assert "സഹോദരൻ" in content


def test_search_skips_decomposition_when_ai_disabled(client, mock_tools):
    """No per-word lookups should fire at all when AI Answer is off — would
    be wasted work with nothing to show it to."""
    mock_tools.fuzzy_lookup.return_value = []
    r = client.get("/search?query=Dayavayi+Irikkoo+sahodara")
    assert r.status_code == 200
    assert "No results" in r.text
    # Only the one whole-phrase fuzzy_lookup call — no per-word follow-up calls.
    assert mock_tools.fuzzy_lookup.call_count == 1


# ── debug panel (?debug=1) ──────────────────────────────────────────────────


def _setup_decomposition_mocks(mock_tools, mock_translator, with_missing_word=False):
    """Shared setup for the "Dayavayi Irikkoo sahodara" decomposition case,
    optionally dropping the dictionary entry for "sahodara" to exercise the
    no-match trace path."""
    senses = {
        "ദയ": [_entry("ദയ", "mercy, kindness")],
        "ഇരിക്കുക": [_entry("ഇരിക്കുക", "to sit")],
    }
    if not with_missing_word:
        senses["സഹോദരൻ"] = [_entry("സഹോദരൻ", "brother")]
    mock_tools.fuzzy_lookup.return_value = []
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: senses.get(candidate, [])
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "please sit, brother"
    mock_llm.extract_structured.return_value = QueryUnderstanding(
        headword="Dayavayi Irikkoo sahodara", intent="unknown"
    )
    return mock_llm


def test_search_debug_panel_shows_trace_and_prompt(client, mock_tools):
    """?debug=1 should render the per-word Varnam/dictionary trace and the
    exact prompt sent to the LLM."""
    mock_llm = _setup_decomposition_mocks(mock_tools, None)

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"], "sahodara": ["സഹോദരൻ"]}.get(word, [])

    with (
        patch("linguaalayam.api.web._get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=varnam_side_effect,
        ),
    ):
        r = client.get(
            "/search?query=Dayavayi+Irikkoo+sahodara&debug=1",
            headers={"X-LLM-Enabled": "1"},
        )
    assert r.status_code == 200
    assert "Debug: phrase decomposition trace" in r.text
    # Varnam candidate + chosen candidate shown per word.
    assert "ദയ" in r.text and "ഇരിക്കുക" in r.text
    # The exact prompt is rendered, not just a summary.
    assert "please sit, brother" not in r.text or "Dictionary entries:" in r.text
    assert "Question: Dayavayi Irikkoo sahodara" in r.text


def test_search_debug_panel_shows_unmatched_word(client, mock_tools):
    """A word with no match anywhere should show in the trace as such, not be
    silently dropped from the debug view the way it's dropped from synthesis."""
    mock_llm = _setup_decomposition_mocks(mock_tools, None, with_missing_word=True)

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"]}.get(word, [])

    with (
        patch("linguaalayam.api.web._get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=varnam_side_effect,
        ),
    ):
        r = client.get(
            "/search?query=Dayavayi+Irikkoo+sahodara&debug=1",
            headers={"X-LLM-Enabled": "1"},
        )
    assert r.status_code == 200
    assert "no match anywhere" in r.text


def test_search_no_debug_panel_without_debug_param(client, mock_tools):
    """The trace panel should not render at all unless ?debug=1 is explicitly
    passed — not a default-on feature."""
    mock_llm = _setup_decomposition_mocks(mock_tools, None)

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"], "sahodara": ["സഹോദരൻ"]}.get(word, [])

    with (
        patch("linguaalayam.api.web._get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=varnam_side_effect,
        ),
    ):
        r = client.get("/search?query=Dayavayi+Irikkoo+sahodara", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert "Debug: phrase decomposition trace" not in r.text


def test_search_no_debug_panel_when_decomposition_not_used(client, mock_tools):
    """?debug=1 on an ordinary confident single-word query should have no
    effect — there's no decomposition trace to show."""
    mock_tools.fuzzy_lookup.return_value = [_result(match_type="exact")]
    r = client.get("/search?query=run&debug=1")
    assert r.status_code == 200
    assert "Debug: phrase decomposition trace" not in r.text


# ── feature tip ──────────────────────────────────────────────────────────────


class TestFeatureTip:
    """_feature_tip's mlmorph/jayasree selection and edge-case guards."""

    def test_none_for_latin_headword(self):
        from linguaalayam.api.web import _feature_tip

        assert _feature_tip("configure") is None

    def test_none_for_multiword_headword(self):
        """An unresolved question falls back to the whole sentence as "headword" —
        neither mlmorph nor the trace button applies to a full sentence."""
        from linguaalayam.api.web import _feature_tip

        assert _feature_tip("നീന്തുക എന്നതിനർത്ഥം എന്താണ്") is None

    def test_skip_mlmorph_forces_jayasree(self):
        from linguaalayam.api.web import _feature_tip

        tip = _feature_tip("നീന്തുക", skip_mlmorph=True)
        assert tip is not None
        assert "trace icon" in tip

    def test_falls_back_to_jayasree_when_mlmorph_cant_analyse(self):
        from linguaalayam.api.web import _feature_tip

        with patch("linguaalayam.api.web.analyse_word", return_value=None):
            tip = _feature_tip("നീന്തുക")
        assert tip is not None
        assert "trace icon" in tip


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

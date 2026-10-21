"""Integration tests for the /search and related routes, exercised end-to-end via TestClient."""

from unittest.mock import MagicMock, patch

from linguaalayam.api.web.decomposition import GroundedAnswer, WordGloss
from linguaalayam.rag.query_understanding import QueryUnderstanding
from linguaalayam.translation.base import TranslationResult

from .conftest import extract_structured_side_effect


def _entry(headword: str, embed_text: str, source: str = "datuk") -> dict:
    return {
        "headword": headword,
        "source": source,
        "entry_type": "DatukEntry",
        "embed_text": embed_text,
        "data": {},
        "match_type": "exact",
        "score": 1.0,
    }


# ── route smoke tests ──────────────────────────────────────────────────────────


def test_index_returns_200(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "lingu" in r.text


def test_index_hides_non_en_ml_langs_when_translation_disabled(client, mock_translator):
    """With a noop translator (the default), the picker should only offer EN/ML."""
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
    """Regression: an empty query used to raise UnboundLocalError on `tools`."""
    r = client.get("/search")
    assert r.status_code == 200
    mock_tools.ml_headword_set.assert_called_once()


def test_search_single_word_uses_fuzzy(client, mock_tools, dict_result_factory):
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory()]  # found — no fallback
    r = client.get("/search?query=run")
    assert r.status_code == 200
    mock_tools.fuzzy_lookup.assert_called_once()
    mock_tools.semantic_lookup.assert_not_called()


def test_search_no_results_shows_empty_state(client):
    r = client.get("/search?query=xyzzy_nonexistent")
    assert r.status_code == 200
    assert "No results" in r.text


def test_search_no_lemma_signal_keeps_all_fuzzy_matches(client, mock_tools, dict_result_factory):
    """Lemma-first resolution lives inside DictionaryTools.fuzzy_lookup() now, not the route."""
    mock_tools.fuzzy_lookup.return_value = [
        dict_result_factory(headword="run", match_type="fuzzy"),
        dict_result_factory(headword="ran", source="datuk", match_type="fuzzy"),
    ]
    r = client.get("/search?query=run")
    assert r.status_code == 200
    assert "run" in r.text
    assert "ran" in r.text


def test_search_multiword_uses_fuzzy_not_semantic(client, mock_tools, dict_result_factory):
    """Multi-word queries go through fuzzy_lookup like any other query."""
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory(headword="ഒരു ജലസ്ഥലം")]
    r = client.get("/search?query=ഒരു+ജലസ്ഥലം")
    assert r.status_code == 200
    mock_tools.fuzzy_lookup.assert_called_once()
    mock_tools.semantic_lookup.assert_not_called()


def test_search_no_fuzzy_results_stays_empty_not_semantic(client, mock_tools):
    r = client.get("/search?query=xyzzy")
    assert r.status_code == 200
    assert "No results" in r.text
    mock_tools.semantic_lookup.assert_not_called()


# ── manglish / varnam fallback (integration — see test_manglish.py for unit tests) ──


def test_search_latin_no_results_tries_varnam(client, mock_tools):
    with patch(
        "linguaalayam.transliteration.varnam.manglish_to_malayalam",
        return_value=["ഓടുക"],
    ) as mock_varnam:
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    mock_varnam.assert_called_once_with("oduka")


def test_search_varnam_success_sets_headword(client, mock_tools, dict_result_factory):
    mock_tools.exact_lookup.return_value = [
        dict_result_factory(headword="ഓടുക", source="datuk", match_type="exact")
    ]
    with patch(
        "linguaalayam.transliteration.varnam.manglish_to_malayalam",
        return_value=["ഓടുക"],
    ):
        r = client.get("/search?query=oduka")
    assert r.status_code == 200
    assert "ഓടുക" in r.text


def test_search_varnam_unavailable_falls_back_to_local_schemes(client, mock_tools):
    with (
        patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]),
        patch(
            "linguaalayam.api.web.manglish.roman_to_malayalam_candidates",
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


def test_search_ml_ml_source_maps_to_list(client, mock_tools, dict_result_factory):
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory(source="datuk")]
    r = client.get("/search?query=run&source=ml_ml")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") == ["datuk", "sayahna"]


def test_search_olam_source_passes_string(client, mock_tools, dict_result_factory):
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory()]
    r = client.get("/search?query=run&source=olam_enml")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") == "olam_enml"


def test_search_empty_source_passes_none(client, mock_tools, dict_result_factory):
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory()]
    r = client.get("/search?query=run&source=")
    assert r.status_code == 200
    _, kwargs = mock_tools.fuzzy_lookup.call_args
    assert kwargs.get("source") is None


# ── language parameter ─────────────────────────────────────────────────────────


def test_search_lang_param_accepted(client, mock_translator):
    r = client.get("/search?query=laufen&lang=de-DE")
    assert r.status_code == 200
    mock_translator.translate.assert_called_once_with("laufen", source_lang="de-DE")


def test_search_default_lang_is_en(client, mock_translator):
    r = client.get("/search?query=run")
    assert r.status_code == 200
    _, kwargs = mock_translator.translate.call_args
    assert kwargs.get("source_lang") == "en-US"


# ── AI Answer hint ────────────────────────────────────────────────────────────


def test_search_shows_ai_hint_for_long_query_without_ai(client, mock_tools, dict_result_factory):
    """A sentence-like query with AI off and a confident result surfaces the softer 'weak' hint."""
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory(match_type="exact")]
    r = client.get("/search?query=ജലജന്തു+എന്ന+വാക്ക്+വിഗ്രഹിക്കുക")
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' in r.text
    assert "Not quite what you meant?" in r.text
    assert '<p class="answer-label">' not in r.text


def test_search_no_ai_hint_for_short_query(client, mock_tools, dict_result_factory):
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory(match_type="exact")]
    r = client.get("/search?query=run")
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' not in r.text


def test_search_shows_ai_hint_for_a_two_word_confident_query(
    client, mock_tools, dict_result_factory
):
    """A confident 2-word match still invites AI to break it down, not just a 3+ word sentence."""
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory(match_type="exact")]
    r = client.get("/search?query=two+words")
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' in r.text


def test_search_decomposes_a_two_word_confident_query_once_ai_is_enabled(client, mock_tools):
    """Clicking that hint (turning AI on) must actually trigger decomposition at 2 words."""
    mock_tools.fuzzy_lookup.side_effect = lambda word, **_: (
        [_entry("run", "to move quickly")] if word == "run" else []
    )
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: {
        "fast": [_entry("fast", "quickly")],
    }.get(candidate, [])
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(
        answer="run fast",
        words=[
            WordGloss(
                word="run",
                meaning="run",
                grounded=True,
                headword="run",
                source="olam_enml",
                quote="to move quickly",
            ),
        ],
    )

    def extract_side_effect(schema, _prompt):
        if schema is QueryUnderstanding:
            return QueryUnderstanding(headword="run fast", intent="unknown")
        return grounded_answer

    mock_llm.extract_structured.side_effect = extract_side_effect

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=lambda word: [word],
        ),
    ):
        r = client.get("/search?query=run+fast", headers={"X-LLM-Enabled": "1"})

    assert r.status_code == 200
    assert "run fast" in r.text
    assert any(
        call.args[0] is GroundedAnswer for call in mock_llm.extract_structured.call_args_list
    )


def test_search_no_ai_hint_when_ai_already_enabled(client, mock_tools, dict_result_factory):
    """No hint should show once AI Answer is already on — the answer card takes its place."""
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory(match_type="exact")]
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(answer="synthesized answer", words=[])
    mock_llm.extract_structured.side_effect = extract_structured_side_effect(
        "ജലജന്തു എന്ന വാക്ക് വിഗ്രഹിക്കുക", grounded_answer
    )
    with patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm):
        r = client.get(
            "/search?query=ജലജന്തു+എന്ന+വാക്ക്+വിഗ്രഹിക്കുക",
            headers={"X-LLM-Enabled": "1"},
        )
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' not in r.text
    assert "synthesized answer" in r.text


def test_search_shows_ai_hint_even_without_confident_result(
    client, mock_tools, dict_result_factory
):
    """A weak-only fuzzy match still triggers the "empty" hint variant."""
    mock_tools.fuzzy_lookup.return_value = [
        {**dict_result_factory(match_type="fuzzy"), "score": 0.2}
    ]
    r = client.get("/search?query=ജലജന്തു+എന്ന+വാക്ക്+വിഗ്രഹിക്കുക")
    assert r.status_code == 200
    assert 'onclick="enableAiHint(event)"' in r.text
    assert "Nothing confident found" in r.text


# ── AI Answer synthesis gating ──────────────────────────────────────────────────


def test_search_skips_ai_for_short_confident_query(client, mock_tools, dict_result_factory):
    """AI Answer should not fire for a short query with an already-confident match."""
    mock_tools.fuzzy_lookup.return_value = [
        dict_result_factory(headword="നീന്തുക", match_type="exact")
    ]
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "should not be called"
    with patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm):
        r = client.get("/search?query=നീന്തുക", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert '<p class="answer-label">' not in r.text
    mock_llm.complete.assert_not_called()


def test_search_still_synthesizes_short_query_without_confident_result(
    client, mock_tools, dict_result_factory
):
    mock_tools.fuzzy_lookup.return_value = [
        {**dict_result_factory(match_type="fuzzy"), "score": 0.3}
    ]
    mock_llm = MagicMock()
    mock_llm.complete.return_value = "synthesized answer"
    with patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm):
        r = client.get("/search?query=run", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert "synthesized answer" in r.text


# ── phrase decomposition for AI Answer (integration) ────────────────────────────


def test_search_decomposes_manglish_phrase_for_ai_answer(client, mock_tools):
    """A Manglish phrase with no whole-phrase match still gets a stitched AI Answer."""
    mock_tools.fuzzy_lookup.return_value = []
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: {
        "ദയ": [_entry("ദയ", "mercy, kindness")],
        "ഇരിക്കുക": [
            _entry("ഇരിക്കുക", "an auxiliary verb usage"),
            _entry("ഇരിക്കുക", "to sit"),
        ],
        "സഹോദരൻ": [_entry("സഹോദരൻ", "brother")],
    }.get(candidate, [])
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(
        answer="please sit, brother",
        words=[
            WordGloss(
                word="Dayavayi",
                meaning="please",
                grounded=True,
                headword="ദയ",
                source="datuk",
                quote="mercy, kindness",
            ),
            WordGloss(
                word="Irikkoo",
                meaning="to sit",
                grounded=True,
                headword="ഇരിക്കുക",
                source="datuk",
                quote="to sit",
            ),
            WordGloss(
                word="sahodara",
                meaning="brother",
                grounded=True,
                headword="സഹോദരൻ",
                source="datuk",
                quote="brother",
            ),
        ],
    )
    mock_llm.extract_structured.side_effect = extract_structured_side_effect(
        "Dayavayi Irikkoo sahodara", grounded_answer
    )

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"], "sahodara": ["സഹോദരൻ"]}.get(word, [])

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=varnam_side_effect,
        ),
    ):
        r = client.get("/search?query=Dayavayi+Irikkoo+sahodara", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert "please sit, brother" in r.text
    assert "No results" in r.text  # raw results list untouched, still empty

    assert "Dictionary sources (3)" in r.text
    assert "to sit" in r.text
    assert "brother" in r.text

    _, content = next(
        call.args
        for call in mock_llm.extract_structured.call_args_list
        if call.args[0] is GroundedAnswer
    )
    assert "rather than parsing the raw dictionary text literally" in content
    assert "an auxiliary verb usage" in content
    assert "to sit" in content
    assert "ദയ" in content
    assert "ഇരിക്കുക" in content
    assert "സഹോദരൻ" in content


def test_search_decomposes_a_declarative_sentence_understand_query_collapsed_to_one_word(
    client, mock_tools
):
    """Decomposition falls back to the original query if understand_query collapses it."""
    mock_tools.fuzzy_lookup.return_value = []
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: {
        "parks": [_entry("പാർക്കുകൾ", "parks")],
        "protected": [_entry("സംരക്ഷിത", "protected")],
    }.get(candidate, [])
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(
        answer="national parks are protected areas",
        words=[
            WordGloss(
                word="parks",
                meaning="parks",
                grounded=True,
                headword="പാർക്കുകൾ",
                source="datuk",
                quote="parks",
            ),
        ],
    )

    def extract_side_effect(schema, _prompt):
        if schema is QueryUnderstanding:
            # Collapses the full sentence down to a single extracted keyword,
            # with no space and no dictionary entry of its own — the condition
            # that used to defeat decomposition entirely.
            return QueryUnderstanding(headword="destinations", intent="define")
        return grounded_answer

    mock_llm.extract_structured.side_effect = extract_side_effect

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=lambda word: [word],
        ),
    ):
        r = client.get(
            "/search?query=Taiwan%27s+national+parks+are+protected+areas",
            headers={"X-LLM-Enabled": "1"},
        )
    assert r.status_code == 200
    assert "national parks are protected areas" in r.text


def test_search_decomposes_a_sentence_even_when_one_word_resolves_confidently(client, mock_tools):
    """A sentence-length query decomposes even if one word inside it is a confident match."""
    mock_tools.fuzzy_lookup.side_effect = lambda word, **_: (
        [_entry("fox", "a quick fox")] if word == "fox" else []
    )
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: {
        "the": [_entry("the", "definite article")],
        "quick": [_entry("quick", "fast")],
    }.get(candidate, [])
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(
        answer="a fast fox",
        words=[
            WordGloss(
                word="fox",
                meaning="fox",
                grounded=True,
                headword="fox",
                source="olam_enml",
                quote="a quick fox",
            ),
        ],
    )

    def extract_side_effect(schema, _prompt):
        if schema is QueryUnderstanding:
            return QueryUnderstanding(headword="fox", intent="define")
        return grounded_answer

    mock_llm.extract_structured.side_effect = extract_side_effect

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=lambda word: [word],
        ),
    ):
        r = client.get("/search?query=the+quick+fox", headers={"X-LLM-Enabled": "1"})

    assert r.status_code == 200
    assert "a fast fox" in r.text
    # Decomposition (structured output), not the strict whole-phrase prompt, won out.
    assert any(
        call.args[0] is GroundedAnswer for call in mock_llm.extract_structured.call_args_list
    )
    mock_llm.complete.assert_not_called()


def test_search_decomposition_shows_ungrounded_marker_for_unsupported_word(client, mock_tools):
    """An ungrounded word renders with the honesty marker, not a fabricated source."""
    mock_tools.fuzzy_lookup.return_value = []
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: {
        "asura": [_entry("അസുര", "devoid of breath/life")],
        "king": [_entry("രാജാവ്", "one who rules a kingdom")],
    }.get(candidate, [])
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(
        answer="an asura king is a demon king",
        words=[
            WordGloss(word="asura", meaning="demon", grounded=False),
            WordGloss(
                word="king",
                meaning="king",
                grounded=True,
                headword="രാജാവ്",
                source="datuk",
                quote="one who rules a kingdom",
            ),
        ],
    )
    mock_llm.extract_structured.side_effect = extract_structured_side_effect(
        "asura king", grounded_answer
    )

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=lambda word: [word],
        ),
    ):
        r = client.get("/search?query=asura+king", headers={"X-LLM-Enabled": "1"})

    assert r.status_code == 200
    assert "Dictionary sources (1)" in r.text
    assert "one who rules a kingdom" in r.text
    assert "ungrounded-mark" in r.text
    assert "devoid of breath/life" not in r.text


def test_search_decomposition_shows_no_sources_fallback_when_nothing_grounds(client, mock_tools):
    mock_tools.fuzzy_lookup.return_value = []
    mock_tools.exact_lookup.side_effect = lambda candidate, **_: {
        "asura": [_entry("അസുര", "devoid of breath/life")],
    }.get(candidate, [])
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(
        answer="an asura is a demon",
        words=[WordGloss(word="asura", meaning="demon", grounded=False)],
    )
    mock_llm.extract_structured.side_effect = extract_structured_side_effect(
        "asura thing", grounded_answer
    )

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=lambda word: [word],
        ),
    ):
        r = client.get("/search?query=asura+thing", headers={"X-LLM-Enabled": "1"})

    assert r.status_code == 200
    assert "No dictionary entries directly supported this answer" in r.text
    assert "Dictionary sources" not in r.text


def test_search_skips_decomposition_when_ai_disabled(client, mock_tools):
    """No per-word lookups should fire at all when AI Answer is off."""
    mock_tools.fuzzy_lookup.return_value = []
    r = client.get("/search?query=Dayavayi+Irikkoo+sahodara")
    assert r.status_code == 200
    assert "No results" in r.text
    assert mock_tools.fuzzy_lookup.call_count == 1


def test_search_still_answers_an_unmatched_single_word(client, mock_tools):
    """A single word with zero dictionary coverage still gets an answer, not silence."""
    mock_tools.fuzzy_lookup.return_value = []  # no whole-phrase match
    mock_tools.exact_lookup.return_value = []
    mock_llm = MagicMock()
    grounded_answer = GroundedAnswer(
        answer="a word meaning industrial use, not in this dictionary",
        words=[],
    )

    def extract_side_effect(schema, _prompt):
        if schema is QueryUnderstanding:
            return QueryUnderstanding(headword="വ്യാവസായികോപയോഗത്തിന്", intent="define")
        return grounded_answer

    mock_llm.extract_structured.side_effect = extract_side_effect

    with patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm):
        r = client.get("/search?query=വ്യാവസായികോപയോഗത്തിന്", headers={"X-LLM-Enabled": "1"})

    assert r.status_code == 200
    assert "a word meaning industrial use, not in this dictionary" in r.text
    assert "No dictionary entries directly supported this answer" in r.text


# ── debug panel (?debug=1) ──────────────────────────────────────────────────


def _setup_decomposition_mocks(mock_tools, with_missing_word=False):
    """Build a mocked LLM for the "Dayavayi Irikkoo sahodara" decomposition case."""
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
    words = [
        WordGloss(
            word="Dayavayi",
            meaning="please",
            grounded=True,
            headword="ദയ",
            source="datuk",
            quote="mercy, kindness",
        ),
        WordGloss(
            word="Irikkoo",
            meaning="to sit",
            grounded=True,
            headword="ഇരിക്കുക",
            source="datuk",
            quote="to sit",
        ),
    ]
    if with_missing_word:
        words.append(WordGloss(word="sahodara", meaning="brother", grounded=False))
    else:
        words.append(
            WordGloss(
                word="sahodara",
                meaning="brother",
                grounded=True,
                headword="സഹോദരൻ",
                source="datuk",
                quote="brother",
            )
        )
    grounded_answer = GroundedAnswer(answer="please sit, brother", words=words)
    mock_llm.extract_structured.side_effect = extract_structured_side_effect(
        "Dayavayi Irikkoo sahodara", grounded_answer
    )
    return mock_llm


def test_search_debug_panel_shows_trace_and_prompt(client, mock_tools):
    mock_llm = _setup_decomposition_mocks(mock_tools)

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"], "sahodara": ["സഹോദരൻ"]}.get(word, [])

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
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
    assert "ദയ" in r.text and "ഇരിക്കുക" in r.text
    assert "please sit, brother" not in r.text or "Dictionary entries:" in r.text
    assert "Question: Dayavayi Irikkoo sahodara" in r.text


def test_search_debug_panel_shows_unmatched_word(client, mock_tools):
    mock_llm = _setup_decomposition_mocks(mock_tools, with_missing_word=True)

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"]}.get(word, [])

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
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
    mock_llm = _setup_decomposition_mocks(mock_tools)

    def varnam_side_effect(word: str) -> list[str]:
        return {"dayavayi": ["ദയ"], "irikkoo": ["ഇരിക്കുക"], "sahodara": ["സഹോദരൻ"]}.get(word, [])

    with (
        patch("linguaalayam.api.web.llm.get_server_llm", return_value=mock_llm),
        patch(
            "linguaalayam.transliteration.varnam.manglish_to_malayalam",
            side_effect=varnam_side_effect,
        ),
    ):
        r = client.get("/search?query=Dayavayi+Irikkoo+sahodara", headers={"X-LLM-Enabled": "1"})
    assert r.status_code == 200
    assert "Debug: phrase decomposition trace" not in r.text


def test_search_no_debug_panel_when_decomposition_not_used(client, mock_tools, dict_result_factory):
    mock_tools.fuzzy_lookup.return_value = [dict_result_factory(match_type="exact")]
    r = client.get("/search?query=run&debug=1")
    assert r.status_code == 200
    assert "Debug: phrase decomposition trace" not in r.text

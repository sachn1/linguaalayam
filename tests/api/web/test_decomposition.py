"""Unit tests for linguaalayam.api.web.decomposition."""

from unittest.mock import MagicMock, patch

from linguaalayam.api.web.decomposition import (
    WordGloss,
    decompose_and_lookup,
    format_word_entries,
    verify_citations,
)


def _entry(headword: str, embed_text: str, source: str = "datuk") -> dict:
    """Build a per-word lookup result, shaped like DictionaryTools' _to_result output."""
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
    """decompose_and_lookup's per-word resolution logic, unit-tested directly."""

    def test_uses_fuzzy_first_per_word(self):
        """A word that's already a real headword resolves via fuzzy_lookup, no Varnam needed."""
        tools = MagicMock()
        tools.fuzzy_lookup.side_effect = lambda word, **_: (
            [_entry("run", "to move quickly")] if word == "run" else []
        )
        with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]):
            found, _trace = decompose_and_lookup("run fast", tools, None)
        assert found == [("run", [_entry("run", "to move quickly")])]

    def test_falls_back_to_varnam_for_latin_word(self):
        """A Latin-script word with no real-headword match tries Manglish next."""
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
            found, trace = decompose_and_lookup("irikkoo", tools, None)
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
        """A polysemous word surfaces more than one sense, not just whichever came back first."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = [
            _entry("ഇരിക്കുക", "an auxiliary verb usage"),
            _entry("ഇരിക്കുക", "to sit"),
        ]
        found, _trace = decompose_and_lookup("irikkoo", tools, None)
        assert found == [
            ("irikkoo", [_entry("ഇരിക്കുക", "an auxiliary verb usage"), _entry("ഇരിക്കുക", "to sit")])
        ]

    def test_caps_senses_per_word_at_max(self):
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = []
        decompose_and_lookup("irikkoo", tools, None)
        _, kwargs = tools.fuzzy_lookup.call_args
        assert kwargs["top_k"] == 3

    def test_skips_words_with_no_match_anywhere(self):
        """A word that resolves nowhere is omitted from the result but kept in the trace."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = []
        tools.exact_lookup.return_value = []
        tools.lemma_lookup.return_value = []
        with patch("linguaalayam.transliteration.varnam.manglish_to_malayalam", return_value=[]):
            found, trace = decompose_and_lookup("xyzzy run", tools, None)
        assert found == []
        assert [t["word"] for t in trace] == ["xyzzy", "run"]
        assert all(t["final_senses"] == [] for t in trace)

    def test_caps_at_max_decomposition_words(self):
        """A pathologically long input only looks up the first 8 words."""
        tools = MagicMock()
        tools.fuzzy_lookup.return_value = []
        words = " ".join(f"word{i}" for i in range(20))
        decompose_and_lookup(words, tools, None)
        assert tools.fuzzy_lookup.call_count == 8


class TestFormatWordEntries:
    """format_word_entries's numbered, per-word block output."""

    def test_tags_each_entry_with_its_source_word(self):
        text = format_word_entries(
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
        text = format_word_entries(
            [("irikkoo", [_entry("ഇരിക്കുക", "an auxiliary verb usage"), _entry("ഇരിക്കുക", "to sit")])]
        )
        assert "an auxiliary verb usage" in text
        assert "to sit" in text


class TestVerifyCitations:
    """verify_citations' quote verification and input-order guarantee."""

    def test_valid_quote_is_grounded(self):
        word_entries = [("Irikkoo", [_entry("ഇരിക്കുക", "to sit; to live")])]
        glosses = [
            WordGloss(
                word="Irikkoo",
                meaning="to sit",
                grounded=True,
                headword="ഇരിക്കുക",
                source="datuk",
                quote="to sit",
            )
        ]
        result = verify_citations(glosses, word_entries)
        assert result == [
            {
                "word": "Irikkoo",
                "meaning": "to sit",
                "grounded": True,
                "headword": "ഇരിക്കുക",
                "source": "Datuk",
                "quote": "to sit",
            }
        ]

    def test_hallucinated_quote_is_downgraded(self):
        """A quote not actually in the raw entry text must never be shown as grounded."""
        word_entries = [("Irikkoo", [_entry("ഇരിക്കുക", "to sit; to live")])]
        glosses = [
            WordGloss(
                word="Irikkoo",
                meaning="to behave",
                grounded=True,
                headword="ഇരിക്കുക",
                source="datuk",
                quote="this text does not appear in the raw entry",
            )
        ]
        result = verify_citations(glosses, word_entries)
        assert result[0]["grounded"] is False
        assert result[0]["quote"] is None
        assert result[0]["headword"] is None

    def test_quote_matching_a_different_headword_is_downgraded(self):
        """A real substring attributed to the wrong headword is not trusted."""
        word_entries = [("Irikkoo", [_entry("ഇരിക്കുക", "to sit")])]
        glosses = [
            WordGloss(
                word="Irikkoo",
                meaning="to sit",
                grounded=True,
                headword="മറ്റൊരുവാക്ക്",  # not one of this word's own entries
                source="datuk",
                quote="to sit",
            )
        ]
        result = verify_citations(glosses, word_entries)
        assert result[0]["grounded"] is False

    def test_model_said_ungrounded_stays_ungrounded(self):
        word_entries = [("asura", [_entry("അസുര", "devoid of breath/life")])]
        glosses = [WordGloss(word="asura", meaning="demon", grounded=False)]
        result = verify_citations(glosses, word_entries)
        assert result == [
            {
                "word": "asura",
                "meaning": "demon",
                "grounded": False,
                "headword": None,
                "source": None,
                "quote": None,
            }
        ]

    def test_output_order_always_matches_input_order(self):
        """Citations read left-to-right as typed, regardless of the model's own gloss order."""
        word_entries = [
            ("Dayavayi", [_entry("ദയ", "mercy, kindness")]),
            ("Irikkoo", [_entry("ഇരിക്കുക", "to sit")]),
            ("sahodara", [_entry("സഹോദരൻ", "brother")]),
        ]
        glosses = [
            WordGloss(
                word="sahodara",
                meaning="brother",
                grounded=True,
                headword="സഹോദരൻ",
                source="datuk",
                quote="brother",
            ),
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
        result = verify_citations(glosses, word_entries)
        assert [c["word"] for c in result] == ["Dayavayi", "Irikkoo", "sahodara"]

    def test_missing_gloss_for_a_word_falls_back_to_the_word_itself(self):
        """A word the model's output omits entirely still gets an ungrounded row, not a drop."""
        word_entries = [("Irikkoo", [_entry("ഇരിക്കുക", "to sit")])]
        result = verify_citations([], word_entries)
        assert result == [
            {
                "word": "Irikkoo",
                "meaning": "Irikkoo",
                "grounded": False,
                "headword": None,
                "source": None,
                "quote": None,
            }
        ]

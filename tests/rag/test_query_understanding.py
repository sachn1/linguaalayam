"""Tests for rag/query_understanding.py — regex patterns and LLM fallback."""

from unittest.mock import MagicMock

from linguaalayam.llm.adapters.nollm import NoLLMAdapter
from linguaalayam.rag.query_understanding import QueryUnderstanding, understand_query


class TestRegexPatterns:
    """understand_query regex pattern matching for various query phrasings."""

    def test_what_does_mean(self):
        """'what does X mean' should yield intent=define."""
        r = understand_query("what does 'ephemeral' mean")
        assert r.headword == "ephemeral"
        assert r.intent == "define"

    def test_what_is_meaning_of(self):
        """'what is the meaning of X' should yield intent=define."""
        r = understand_query("what is the meaning of pastoral")
        assert r.headword == "pastoral"
        assert r.intent == "define"

    def test_define(self):
        """'define X' should yield intent=define."""
        r = understand_query("define serendipity")
        assert r.headword == "serendipity"
        assert r.intent == "define"

    def test_define_the_word(self):
        """'define the word X' should yield intent=define."""
        r = understand_query("define the word ephemeral")
        assert r.headword == "ephemeral"
        assert r.intent == "define"

    def test_meaning_of(self):
        """'meaning of X' should yield intent=define."""
        r = understand_query("meaning of nostalgia")
        assert r.headword == "nostalgia"
        assert r.intent == "define"

    def test_what_is(self):
        """'what is X?' should yield intent=define."""
        r = understand_query("what is melancholy?")
        assert r.headword == "melancholy"
        assert r.intent == "define"

    def test_how_do_you_say_in_malayalam(self):
        """'how do you say X in malayalam' should yield intent=translate."""
        r = understand_query("how do you say 'water' in malayalam")
        assert r.headword == "water"
        assert r.intent == "translate"

    def test_in_malayalam(self):
        """'X in malayalam' should yield intent=translate."""
        r = understand_query("river in malayalam")
        assert r.headword == "river"
        assert r.intent == "translate"

    def test_translate(self):
        """'translate X to malayalam' should yield intent=translate."""
        r = understand_query("translate silence to malayalam")
        assert r.headword == "silence"
        assert r.intent == "translate"

    def test_compare(self):
        """'compare X and Y' should yield intent=compare."""
        r = understand_query("compare love and hope")
        assert r.headword == "love"
        assert r.intent == "compare"

    def test_usage_of(self):
        """'usage of X' should yield intent=usage."""
        r = understand_query("usage of heart")
        assert r.headword == "heart"
        assert r.intent == "usage"

    def test_single_word_latin(self):
        """A single Latin-script word should yield intent=define."""
        r = understand_query("run")
        assert r.headword == "run"
        assert r.intent == "define"

    def test_single_word_malayalam(self):
        """A single Malayalam-script word should yield intent=define."""
        r = understand_query("ഓടുക")
        assert r.headword == "ഓടുക"
        assert r.intent == "define"


class TestLlmFallback:
    """understand_query LLM fallback and error handling."""

    def test_no_llm_returns_unknown(self):
        """Unrecognised query with llm=None should yield intent=unknown."""
        r = understand_query("some totally unrecognised query format xyz", llm=None)
        assert r.intent == "unknown"
        assert r.headword

    def test_nollm_adapter_returns_unknown(self):
        """Unrecognised query with NoLLMAdapter should yield intent=unknown."""
        r = understand_query("some totally unrecognised query format xyz", llm=NoLLMAdapter())
        assert r.intent == "unknown"

    def test_llm_called_when_no_pattern(self):
        """extract_structured should be called when no regex matches."""
        mock_llm = MagicMock()
        mock_llm.has_llm = True
        mock_llm.extract_structured.return_value = QueryUnderstanding(
            headword="nostalgia", intent="define"
        )

        r = understand_query("some totally unrecognised query format xyz", llm=mock_llm)
        assert r.headword == "nostalgia"
        mock_llm.extract_structured.assert_called_once()

    def test_llm_exception_falls_back(self):
        """LLM exception should fall back to intent=unknown."""
        mock_llm = MagicMock()
        mock_llm.has_llm = True
        mock_llm.extract_structured.side_effect = RuntimeError("API error")

        r = understand_query("some totally unrecognised query format xyz", llm=mock_llm)
        assert r.intent == "unknown"

    def test_returns_query_understanding_instance(self):
        """understand_query should always return a QueryUnderstanding instance."""
        r = understand_query("run")
        assert isinstance(r, QueryUnderstanding)

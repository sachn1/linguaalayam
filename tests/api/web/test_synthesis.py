"""Unit tests for linguaalayam.api.web.synthesis."""

from unittest.mock import MagicMock

from linguaalayam.api.web.decomposition import GroundedAnswer, WordGloss
from linguaalayam.api.web.synthesis import DecompositionSynthesis, WholePhraseSynthesis


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


class TestWholePhraseSynthesis:
    def test_answers_from_complete_with_dictionary_only_prompt(self):
        llm = MagicMock()
        llm.complete.return_value = "a running motion"
        strategy = WholePhraseSynthesis(results=[_entry("run", "to move quickly")], top_k=5)
        result = strategy.synthesize(llm, query="run", answer_lang="English", debug=False)
        assert result.answer == "a running motion"
        assert result.citations == []
        assert result.debug_prompt is None
        llm.extract_structured.assert_not_called()


class TestDecompositionSynthesis:
    def test_uses_structured_output_and_verifies_citations(self):
        llm = MagicMock()
        llm.extract_structured.return_value = GroundedAnswer(
            answer="please sit, brother",
            words=[
                WordGloss(
                    word="Irikkoo",
                    meaning="to sit",
                    grounded=True,
                    headword="ഇരിക്കുക",
                    source="datuk",
                    quote="to sit",
                ),
            ],
        )
        word_entries = [("Irikkoo", [_entry("ഇരിക്കുക", "to sit")])]
        result = DecompositionSynthesis(word_entries).synthesize(
            llm, query="Irikkoo", answer_lang="English", debug=False
        )
        assert result.answer == "please sit, brother"
        assert result.citations == [
            {
                "word": "Irikkoo",
                "meaning": "to sit",
                "grounded": True,
                "headword": "ഇരിക്കുക",
                "source": "Datuk",
                "quote": "to sit",
            }
        ]
        llm.complete.assert_not_called()

    def test_debug_prompt_only_populated_when_requested(self):
        llm = MagicMock()
        llm.extract_structured.return_value = GroundedAnswer(answer="x", words=[])
        word_entries: list[tuple[str, list[dict]]] = []

        not_debugging = DecompositionSynthesis(word_entries).synthesize(
            llm, query="q", answer_lang="English", debug=False
        )
        assert not_debugging.debug_prompt is None

        debugging = DecompositionSynthesis(word_entries).synthesize(
            llm, query="q", answer_lang="English", debug=True
        )
        assert debugging.debug_prompt is not None
        assert "system" in debugging.debug_prompt and "content" in debugging.debug_prompt

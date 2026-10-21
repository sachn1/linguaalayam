"""Unit tests for linguaalayam.api.web.presentation."""

from unittest.mock import patch

from linguaalayam.api.web.presentation import compute_ai_hint, feature_tip


class TestFeatureTip:
    """feature_tip's mlmorph/jayasree selection and edge-case guards."""

    def test_none_for_latin_headword(self):
        assert feature_tip("configure") is None

    def test_none_for_multiword_headword(self):
        """An unresolved question falls back to the whole sentence as "headword"."""
        assert feature_tip("നീന്തുക എന്നതിനർത്ഥം എന്താണ്") is None

    def test_skip_mlmorph_forces_jayasree(self):
        tip = feature_tip("നീന്തുക", skip_mlmorph=True)
        assert tip is not None
        assert "trace icon" in tip

    def test_falls_back_to_jayasree_when_mlmorph_cant_analyse(self):
        with patch("linguaalayam.api.web.presentation.analyse_word", return_value=None):
            tip = feature_tip("നീന്തുക")
        assert tip is not None
        assert "trace icon" in tip

    def test_skip_jayasree_suppresses_trace_tip_when_no_entry_rendered(self):
        """No confident result means no trace button exists on the page at all."""
        tip = feature_tip("നീന്തുക", skip_jayasree=True)
        assert tip is not None
        assert "trace icon" not in tip

    def test_none_when_both_tips_skipped(self):
        assert feature_tip("നീന്തുക", skip_mlmorph=True, skip_jayasree=True) is None


class TestComputeAiHint:
    """compute_ai_hint's gating: AI off, question-shaped query, no answer rendered yet."""

    def test_none_when_answer_already_rendered(self):
        assert (
            compute_ai_hint(
                answer="already have one",
                llm_key="",
                llm_enabled=False,
                query="a long enough query here",
                results=[],
            )
            is None
        )

    def test_none_when_ai_already_enabled(self):
        assert (
            compute_ai_hint(
                answer=None,
                llm_key="",
                llm_enabled=True,
                query="a long enough query here",
                results=[],
            )
            is None
        )

    def test_none_for_short_query(self):
        hint = compute_ai_hint(answer=None, llm_key="", llm_enabled=False, query="run", results=[])
        assert hint is None

    def test_empty_variant_when_nothing_confident(self):
        hint = compute_ai_hint(
            answer=None,
            llm_key="",
            llm_enabled=False,
            query="a long enough query here",
            results=[],
        )
        assert hint == "empty"

    def test_weak_variant_when_something_confident_is_shown(self):
        hint = compute_ai_hint(
            answer=None,
            llm_key="",
            llm_enabled=False,
            query="a long enough query here",
            results=[{"match_type": "exact", "score": 1.0}],
        )
        assert hint == "weak"

    def test_weak_variant_shows_for_a_two_word_confident_query(self):
        """A confident literal match still invites AI help at just 2 words."""
        hint = compute_ai_hint(
            answer=None,
            llm_key="",
            llm_enabled=False,
            query="two words",
            results=[{"match_type": "exact", "score": 1.0}],
        )
        assert hint == "weak"

    def test_none_for_a_single_word_confident_query(self):
        hint = compute_ai_hint(
            answer=None,
            llm_key="",
            llm_enabled=False,
            query="run",
            results=[{"match_type": "exact", "score": 1.0}],
        )
        assert hint is None

    def test_empty_variant_still_requires_three_words(self):
        """A 2-word *unconfident* query gets no hint — "empty" keeps its own, higher bar."""
        hint = compute_ai_hint(
            answer=None, llm_key="", llm_enabled=False, query="two words", results=[]
        )
        assert hint is None

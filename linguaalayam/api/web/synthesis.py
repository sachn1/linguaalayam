"""Turning retrieved dictionary entries into an AI Answer."""

import html
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from linguaalayam.api.web.decomposition import GroundedAnswer, format_word_entries, verify_citations
from linguaalayam.api.web.prompts import DECOMPOSITION_SYNTHESIS_SYSTEM
from linguaalayam.llm.adapters.base import LLMAdapter
from linguaalayam.rag.pipeline import _SYNTHESIS_SYSTEM, _SYNTHESIS_TEMPLATE, _format_entries


@dataclass
class SynthesisResult:
    """The LLM's answer, its citation trail, and the debug prompt (if requested)."""

    answer: str
    citations: list[dict] = field(default_factory=list)
    debug_prompt: dict[str, str] | None = None


class SynthesisStrategy(ABC):
    """Turns retrieved dictionary entries into an AI Answer."""

    @abstractmethod
    def synthesize(
        self, llm: LLMAdapter, query: str, answer_lang: str, debug: bool
    ) -> SynthesisResult:
        """Produce a ``SynthesisResult`` from this strategy's retrieved entries.

        Parameters
        ----------
        llm : LLMAdapter
            The LLM to call.
        query : str
            The original user query.
        answer_lang : str
            Language name (e.g. ``"English"``) the answer should be written in.
        debug : bool
            When true, populate ``SynthesisResult.debug_prompt`` with the
            exact prompt sent to the LLM.

        Returns
        -------
        SynthesisResult
            The answer, its citations (if any), and the debug prompt (if requested).
        """
        ...


class WholePhraseSynthesis(SynthesisStrategy):
    """Answers from a confirmed whole-phrase match, using the dictionary-only system prompt."""

    def __init__(self, results: list[dict], top_k: int):
        """Store the whole-phrase match results to synthesize from."""
        self._results = results
        self._top_k = top_k

    def synthesize(
        self, llm: LLMAdapter, query: str, answer_lang: str, debug: bool
    ) -> SynthesisResult:
        """See ``SynthesisStrategy.synthesize``."""
        entries_text = _format_entries(self._results[: self._top_k])
        content = _SYNTHESIS_TEMPLATE.format(query=query, entries=entries_text)
        content += f"\n\nRespond in {answer_lang}."
        answer = html.escape(llm.complete(_SYNTHESIS_SYSTEM, content))
        return SynthesisResult(answer=answer)


class DecompositionSynthesis(SynthesisStrategy):
    """Reconstructs an answer from per-word lookups, grounded against their raw dictionary text."""

    def __init__(self, word_entries: list[tuple[str, list[dict]]]):
        """Store the per-word lookups to synthesize from."""
        self._word_entries = word_entries

    def synthesize(
        self, llm: LLMAdapter, query: str, answer_lang: str, debug: bool
    ) -> SynthesisResult:
        """See ``SynthesisStrategy.synthesize``.

        Uses structured output (not ``llm.complete()``) so each word's gloss
        and its grounding quote come back as real fields, verified against
        the real dictionary text via ``decomposition.verify_citations``
        rather than trusted at face value.
        """
        entries_text = format_word_entries(self._word_entries)
        content = _SYNTHESIS_TEMPLATE.format(query=query, entries=entries_text)
        content += f"\n\nRespond in {answer_lang}."
        debug_prompt = (
            {"system": DECOMPOSITION_SYNTHESIS_SYSTEM, "content": content} if debug else None
        )
        structured = llm.extract_structured(
            GroundedAnswer, f"{DECOMPOSITION_SYNTHESIS_SYSTEM}\n\n{content}"
        )
        answer = html.escape(structured.answer)
        citations = verify_citations(structured.words, self._word_entries)
        return SynthesisResult(answer=answer, citations=citations, debug_prompt=debug_prompt)

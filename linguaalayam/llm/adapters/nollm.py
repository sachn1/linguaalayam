"""No-op LLM adapter — no API key needed; disables synthesis and structured extraction."""

from typing import Type, TypeVar

from .base import LLMAdapter

T = TypeVar("T")


class NoLLMAdapter(LLMAdapter):
    """Adapter for running the pipeline without an LLM.

    When this adapter is active:

    - Synthesis falls back to formatted reranker output (top-k candidates as text).
    - Query understanding uses regex patterns only; unrecognised queries return
      ``intent='unknown'``.

    No API key or network access is required.
    """

    @property
    def has_llm(self) -> bool:
        """Always ``False`` — this adapter has no language model."""
        return False

    def complete(self, _system: str, _user: str) -> str:
        """Raise ``NotImplementedError`` — no LLM is configured.

        Raises
        ------
        NotImplementedError
            Always; callers must check :attr:`has_llm` before calling this.
        """
        raise NotImplementedError("NoLLMAdapter has no language model configured.")

    def extract_structured(self, _schema: Type[T], _prompt: str) -> T:
        """Raise ``NotImplementedError`` — no LLM is configured.

        Raises
        ------
        NotImplementedError
            Always; callers must check :attr:`has_llm` before calling this.
        """
        raise NotImplementedError("NoLLMAdapter has no language model configured.")

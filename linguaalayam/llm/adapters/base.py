"""Abstract base class for LLM provider adapters."""

from abc import ABC, abstractmethod
from typing import TypeVar, Type

T = TypeVar("T")


class LLMAdapter(ABC):
    """Uniform interface for LLM providers used by the RAG pipeline.

    Implement this class to add a new provider. Two capabilities are required:
      - complete()           — free-form text generation (synthesis node)
      - extract_structured() — structured Pydantic output (query understanding)

    Override `has_llm` to return False for no-op adapters that skip synthesis.
    """

    @property
    def has_llm(self) -> bool:
        """True if this adapter can perform LLM calls."""
        return True

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send a system + user message pair; return the model's text response."""
        ...

    @abstractmethod
    def extract_structured(self, schema: Type[T], prompt: str) -> T:
        """Parse a prompt into an instance of a Pydantic model."""
        ...

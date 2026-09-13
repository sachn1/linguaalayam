"""Abstract base class for LLM provider adapters."""

from abc import ABC, abstractmethod
from typing import Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage

T = TypeVar("T")


class LLMAdapter(ABC):
    """Uniform interface for LLM providers used by the RAG pipeline.

    Implement this class to add a new provider. Two capabilities are required:
      - complete()           — free-form text generation (synthesis node)
      - extract_structured() — structured Pydantic output (query understanding)

    If the provider is LangChain-backed (has a chat model exposing ``.invoke()``
    and ``.with_structured_output()`` — every current provider does), subclass
    ``LangChainAdapter`` instead: it implements both methods against
    ``self._llm`` so providers only need to set that up in ``__init__``.

    Override `has_llm` to return False for no-op adapters that skip synthesis.
    """

    @property
    def has_llm(self) -> bool:
        """True if this adapter can perform LLM calls."""
        return True

    @abstractmethod
    def complete(self, system: str, user: str) -> str:
        """Send a system + user message pair and return the model's text response.

        Parameters
        ----------
        system : str
            System-level instruction that sets the model's behaviour.
        user : str
            User message to respond to.

        Returns
        -------
        str
            The model's generated text response.
        """
        ...

    @abstractmethod
    def extract_structured(self, schema: Type[T], prompt: str) -> T:
        """Parse a prompt into an instance of a Pydantic model.

        Parameters
        ----------
        schema : Type[T]
            Pydantic model class to parse the response into.
        prompt : str
            Prompt describing what structured data to extract.

        Returns
        -------
        T
            A validated instance of ``schema``.
        """
        ...


class LangChainAdapter(LLMAdapter):
    """Concrete ``complete``/``extract_structured`` for any LangChain-backed provider.

    Subclasses set ``self._llm`` in ``__init__`` to a LangChain chat model
    (anything exposing ``.invoke()`` and ``.with_structured_output()``) and
    get both methods for free — this is what ``AnthropicAdapter``,
    ``OpenAIAdapter``, and ``TogetherAIAdapter`` all do; only their
    provider-specific ``__init__`` differs.
    """

    def complete(self, system: str, user: str) -> str:
        """Send a system + user message pair and return the model's text response.

        Parameters
        ----------
        system : str
            System prompt (instructions / persona).
        user : str
            User message content.

        Returns
        -------
        str
            The model's response as a plain string.
        """
        response = self._llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return response.content

    def extract_structured(self, schema: Type[T], prompt: str) -> T:
        """Parse a prompt into an instance of a Pydantic model using structured output.

        Parameters
        ----------
        schema : Type[T]
            A Pydantic ``BaseModel`` subclass describing the expected output.
        prompt : str
            The prompt to send to the model.

        Returns
        -------
        T
            A validated instance of ``schema``.
        """
        return self._llm.with_structured_output(schema).invoke(prompt)

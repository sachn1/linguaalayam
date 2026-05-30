"""OpenAI adapter — wraps ChatOpenAI via LangChain."""

import os
from typing import Type, TypeVar

from langchain_core.messages import HumanMessage, SystemMessage

from .base import LLMAdapter

T = TypeVar("T")


class OpenAIAdapter(LLMAdapter):
    """LLM adapter backed by the OpenAI API via LangChain's ChatOpenAI.

    ``langchain-openai`` is an optional dependency; a helpful ``ImportError``
    is raised if it is not installed.

    Parameters
    ----------
    model : str
        OpenAI model identifier (e.g. ``"gpt-4o-mini"``).
    temperature : float, optional
        Sampling temperature; defaults to ``0.0`` for deterministic output.
    max_tokens : int, optional
        Maximum tokens in the model response; defaults to ``1024``.

    Raises
    ------
    RuntimeError
        If ``OPENAI_API_KEY`` is not set in the environment.
    ImportError
        If ``langchain-openai`` is not installed.
    """

    def __init__(self, model: str, temperature: float = 0.0, max_tokens: int = 1024):
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. " "Add it to your .env file: OPENAI_API_KEY=sk-..."
            )
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required for the OpenAI provider. "
                "Run: poetry add langchain-openai"
            ) from exc
        self._llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)

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

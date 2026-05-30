"""Anthropic adapter — wraps ChatAnthropic via LangChain."""

import os
from typing import Type, TypeVar

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .base import LLMAdapter

T = TypeVar("T")


class AnthropicAdapter(LLMAdapter):
    """LLM adapter backed by the Anthropic API via LangChain's ChatAnthropic.

    Parameters
    ----------
    model : str
        Anthropic model identifier (e.g. ``"claude-sonnet-4-6"``).
    temperature : float, optional
        Sampling temperature; defaults to ``0.0`` for deterministic output.
    max_tokens : int, optional
        Maximum tokens in the model response; defaults to ``1024``.

    Raises
    ------
    RuntimeError
        If ``ANTHROPIC_API_KEY`` is not set in the environment.
    """

    def __init__(self, model: str, temperature: float = 0.0, max_tokens: int = 1024):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
            )
        self._llm = ChatAnthropic(model=model, temperature=temperature, max_tokens=max_tokens)

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

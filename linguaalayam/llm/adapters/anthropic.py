"""Anthropic adapter — wraps ChatAnthropic via LangChain."""

import os

from langchain_anthropic import ChatAnthropic

from .base import LangChainAdapter


class AnthropicAdapter(LangChainAdapter):
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

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        api_key: str | None = None,
    ):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
            )
        self._llm = ChatAnthropic(
            model=model, temperature=temperature, max_tokens=max_tokens, api_key=key
        )

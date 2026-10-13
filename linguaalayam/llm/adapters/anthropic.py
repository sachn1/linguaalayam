"""Anthropic adapter — wraps ChatAnthropic via LangChain."""

import os

from .base import LangChainAdapter


class AnthropicAdapter(LangChainAdapter):
    """LLM adapter backed by the Anthropic API via LangChain's ChatAnthropic.

    ``langchain-anthropic`` is imported lazily in ``__init__`` rather than at
    module level — this module is imported unconditionally at app startup
    (``api/web.py``), so a module-level import here would pay its load cost
    on every cold start regardless of whether Anthropic is ever actually
    used (the web app is bring-your-own-key for Anthropic; most requests
    never touch this adapter at all).

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
    ImportError
        If ``langchain-anthropic`` is not installed.
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
        try:
            from langchain_anthropic import ChatAnthropic
        except ImportError as exc:
            raise ImportError(
                "langchain-anthropic is required for the Anthropic provider. "
                "Run: poetry add langchain-anthropic"
            ) from exc
        self._llm = ChatAnthropic(
            model=model, temperature=temperature, max_tokens=max_tokens, api_key=key
        )

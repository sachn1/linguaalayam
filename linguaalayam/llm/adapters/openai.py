"""OpenAI adapter — wraps ChatOpenAI via LangChain."""

import os

from .base import LangChainAdapter


class OpenAIAdapter(LangChainAdapter):
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

    def __init__(
        self,
        model: str,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        api_key: str | None = None,
    ):
        key = api_key or os.environ.get("OPENAI_API_KEY")
        if not key:
            raise RuntimeError(
                "OPENAI_API_KEY is not set. Add it to your .env file: OPENAI_API_KEY=sk-..."
            )
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required for the OpenAI provider. "
                "Run: poetry add langchain-openai"
            ) from exc
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=key,
        )

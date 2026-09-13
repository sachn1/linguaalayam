"""TogetherAI adapter — OpenAI-compatible endpoint wrapping Qwen models."""

import os

from .base import LangChainAdapter

_TOGETHER_BASE_URL = "https://api.together.xyz/v1"


class TogetherAIAdapter(LangChainAdapter):
    """LLM adapter backed by TogetherAI's OpenAI-compatible API.

    Uses ``langchain_openai.ChatOpenAI`` pointed at TogetherAI's endpoint
    (``https://api.together.xyz/v1``), so no extra dependency is needed beyond
    ``langchain-openai``.

    Parameters
    ----------
    model : str
        TogetherAI model identifier (e.g. ``"Qwen/Qwen3.5-9B"``).
    temperature : float, optional
        Sampling temperature; defaults to ``0.0`` for deterministic output.
    max_tokens : int, optional
        Maximum tokens in the model response; defaults to ``1024``.
    api_key : str or None, optional
        TogetherAI API key. If not provided, falls back to ``TOGETHER_API_KEY``
        environment variable.

    Raises
    ------
    RuntimeError
        If ``api_key`` is not provided and ``TOGETHER_API_KEY`` is not set.
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
        key = api_key or os.environ.get("TOGETHER_API_KEY")
        if not key:
            raise RuntimeError(
                "TOGETHER_API_KEY is not set. "
                "Add it to your .env file: TOGETHER_API_KEY=your-key..."
            )
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required for the TogetherAI provider. "
                "Run: poetry add langchain-openai"
            ) from exc
        self._llm = ChatOpenAI(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=key,
            openai_api_base=_TOGETHER_BASE_URL,
            # Qwen models on TogetherAI default to "thinking" mode, which burns the
            # entire max_tokens budget on hidden reasoning and returns empty content.
            extra_body={"chat_template_kwargs": {"enable_thinking": False}},
        )

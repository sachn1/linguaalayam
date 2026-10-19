"""LLM adapter construction for the web UI: bring-your-own-key or the free server-side default."""

from linguaalayam.llm.adapters.anthropic import AnthropicAdapter
from linguaalayam.llm.adapters.base import LLMAdapter
from linguaalayam.llm.adapters.nollm import NoLLMAdapter
from linguaalayam.llm.adapters.openai import OpenAIAdapter
from linguaalayam.llm.adapters.togetherai import TogetherAIAdapter

NO_LLM = NoLLMAdapter()

_SERVER_LLM: LLMAdapter | None = None


def make_llm(provider: str, key: str) -> LLMAdapter:
    """Instantiate an LLM adapter from a user-supplied key.

    Parameters
    ----------
    provider : str
        One of ``"openai"``, ``"anthropic"``, or anything else (defaults to TogetherAI).
    key : str
        The user's own API key for that provider.

    Returns
    -------
    LLMAdapter
        An adapter constructed with the given key, never a server-side key.
    """
    if provider == "openai":
        return OpenAIAdapter(model="gpt-4o-mini", max_tokens=512, api_key=key)
    if provider == "anthropic":
        return AnthropicAdapter(model="claude-haiku-4-5-20251001", max_tokens=512, api_key=key)
    return TogetherAIAdapter(model="Qwen/Qwen3.5-9B", max_tokens=512, api_key=key)


def get_server_llm() -> LLMAdapter:
    """Return the free server-side LLM (TogetherAI Qwen) for users without their own key.

    Lazy-loaded and cached at module scope.

    Returns
    -------
    LLMAdapter
        The shared server-side TogetherAI adapter.

    Raises
    ------
    RuntimeError
        If ``TOGETHER_API_KEY`` is not set.
    """
    global _SERVER_LLM
    if _SERVER_LLM is None:
        _SERVER_LLM = TogetherAIAdapter(model="Qwen/Qwen3.5-9B", max_tokens=512)
    return _SERVER_LLM

"""Unit tests for linguaalayam.api.web.llm."""

from linguaalayam.api.web.llm import make_llm
from linguaalayam.llm.adapters.anthropic import AnthropicAdapter
from linguaalayam.llm.adapters.openai import OpenAIAdapter
from linguaalayam.llm.adapters.togetherai import TogetherAIAdapter


def test_make_llm_openai():
    assert isinstance(make_llm("openai", "key"), OpenAIAdapter)


def test_make_llm_anthropic():
    assert isinstance(make_llm("anthropic", "key"), AnthropicAdapter)


def test_make_llm_defaults_to_togetherai():
    assert isinstance(make_llm("togetherai", "key"), TogetherAIAdapter)
    assert isinstance(make_llm("anything-unrecognised", "key"), TogetherAIAdapter)

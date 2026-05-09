"""Tests for llm/adapters — AnthropicAdapter, OpenAIAdapter, NoLLMAdapter."""

import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from linguaalayam.llm.adapters import AnthropicAdapter, LLMAdapter, NoLLMAdapter
from linguaalayam.llm.adapters.base import LLMAdapter as LLMAdapterBase


class TestLLMAdapterInterface:
    def test_all_adapters_subclass_base(self):
        assert issubclass(AnthropicAdapter, LLMAdapterBase)
        assert issubclass(NoLLMAdapter, LLMAdapterBase)

    def test_base_is_abstract(self):
        with pytest.raises(TypeError):
            LLMAdapter()  # cannot instantiate ABC directly


class TestAnthropicAdapter:
    def _make(self, model: str = "claude-3-5-sonnet-20241022") -> AnthropicAdapter:
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.adapters.anthropic.ChatAnthropic"),
        ):
            return AnthropicAdapter(model=model)

    def test_has_llm_true(self):
        adapter = self._make()
        assert adapter.has_llm

    def test_complete_returns_string(self):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = AIMessage(content="ഓടുക")
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.adapters.anthropic.ChatAnthropic", return_value=mock_llm),
        ):
            adapter = AnthropicAdapter(model="claude-3-5-sonnet-20241022")
        result = adapter.complete("system prompt", "user prompt")
        assert result == "ഓടുക"

    def test_extract_structured_delegates_to_langchain(self):
        from pydantic import BaseModel

        class Schema(BaseModel):
            word: str

        mock_llm = MagicMock()
        structured = MagicMock()
        structured.invoke.return_value = Schema(word="run")
        mock_llm.with_structured_output.return_value = structured

        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.adapters.anthropic.ChatAnthropic", return_value=mock_llm),
        ):
            adapter = AnthropicAdapter(model="claude-3-5-sonnet-20241022")

        result = adapter.extract_structured(Schema, "some prompt")
        assert result.word == "run"
        mock_llm.with_structured_output.assert_called_once_with(Schema)

    def test_raises_without_api_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                AnthropicAdapter(model="claude-3-5-sonnet-20241022")


class TestOpenAIAdapter:
    def _make(self, model: str = "gpt-4o-mini") -> "OpenAIAdapter":
        from linguaalayam.llm.adapters.openai import OpenAIAdapter

        mock_chat_openai = MagicMock()
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict("sys.modules", {"langchain_openai": MagicMock(ChatOpenAI=mock_chat_openai)}),
        ):
            adapter = OpenAIAdapter(model=model)
        adapter._llm = MagicMock()
        return adapter

    def test_has_llm_true(self):
        adapter = self._make()
        assert adapter.has_llm

    def test_complete_returns_string(self):
        from langchain_core.messages import AIMessage

        adapter = self._make()
        adapter._llm.invoke.return_value = AIMessage(content="test response")
        result = adapter.complete("system", "user")
        assert result == "test response"

    def test_extract_structured_delegates_to_langchain(self):
        from pydantic import BaseModel

        class Schema(BaseModel):
            word: str

        adapter = self._make()
        structured = MagicMock()
        structured.invoke.return_value = Schema(word="run")
        adapter._llm.with_structured_output.return_value = structured

        result = adapter.extract_structured(Schema, "prompt")
        assert result.word == "run"

    def test_raises_without_api_key(self):
        from linguaalayam.llm.adapters.openai import OpenAIAdapter

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                OpenAIAdapter(model="gpt-4o-mini")

    def test_raises_import_error_when_package_missing(self):
        from linguaalayam.llm.adapters.openai import OpenAIAdapter

        # Setting a module to None in sys.modules causes ImportError on import
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict("sys.modules", {"langchain_openai": None}),
        ):
            with pytest.raises(ImportError, match="langchain-openai"):
                OpenAIAdapter(model="gpt-4o-mini")


class TestNoLLMAdapter:
    def test_has_llm_false(self):
        assert not NoLLMAdapter().has_llm

    def test_complete_raises(self):
        with pytest.raises(NotImplementedError):
            NoLLMAdapter().complete("s", "u")

    def test_extract_structured_raises(self):
        with pytest.raises(NotImplementedError):
            NoLLMAdapter().extract_structured(object, "prompt")

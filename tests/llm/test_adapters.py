"""Tests for llm/adapters — AnthropicAdapter, OpenAIAdapter, NoLLMAdapter."""

import os
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage

from linguaalayam.llm.adapters import AnthropicAdapter, LLMAdapter, NoLLMAdapter
from linguaalayam.llm.adapters.base import LLMAdapter as LLMAdapterBase
from linguaalayam.llm.adapters.openai import OpenAIAdapter


class TestLLMAdapterInterface:
    """LLMAdapter ABC subclass and instantiation checks."""

    def test_all_adapters_subclass_base(self):
        """AnthropicAdapter and NoLLMAdapter should both subclass LLMAdapterBase."""
        assert issubclass(AnthropicAdapter, LLMAdapterBase)
        assert issubclass(NoLLMAdapter, LLMAdapterBase)

    def test_base_is_abstract(self):
        """LLMAdapter should not be directly instantiable."""
        with pytest.raises(TypeError):
            LLMAdapter()  # cannot instantiate ABC directly


class TestAnthropicAdapter:
    """AnthropicAdapter construction, complete, and extract_structured."""

    def _make(self, model: str = "claude-3-5-sonnet-20241022") -> AnthropicAdapter:
        """Build an AnthropicAdapter with a mocked ChatAnthropic."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.adapters.anthropic.ChatAnthropic"),
        ):
            return AnthropicAdapter(model=model)

    def test_has_llm_true(self):
        """has_llm should return True for AnthropicAdapter."""
        adapter = self._make()
        assert adapter.has_llm

    def test_complete_returns_string(self):
        """complete should return the model response as a plain string."""
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
        """extract_structured should use with_structured_output under the hood."""
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
        """Should raise RuntimeError when ANTHROPIC_API_KEY is unset."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                AnthropicAdapter(model="claude-3-5-sonnet-20241022")


class TestOpenAIAdapter:
    """OpenAIAdapter construction, complete, and error handling."""

    def _make(self, model: str = "gpt-4o-mini") -> OpenAIAdapter:
        """Build an OpenAIAdapter with a mocked ChatOpenAI."""
        mock_chat_openai = MagicMock()
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict("sys.modules", {"langchain_openai": MagicMock(ChatOpenAI=mock_chat_openai)}),
        ):
            adapter = OpenAIAdapter(model=model)
        adapter._llm = MagicMock()
        return adapter

    def test_has_llm_true(self):
        """has_llm should return True for OpenAIAdapter."""
        adapter = self._make()
        assert adapter.has_llm

    def test_complete_returns_string(self):
        """complete should return the AIMessage content as a string."""
        from langchain_core.messages import AIMessage

        adapter = self._make()
        adapter._llm.invoke.return_value = AIMessage(content="test response")
        result = adapter.complete("system", "user")
        assert result == "test response"

    def test_extract_structured_delegates_to_langchain(self):
        """extract_structured should return a validated Pydantic instance."""
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
        """Should raise RuntimeError when OPENAI_API_KEY is unset."""
        from linguaalayam.llm.adapters.openai import OpenAIAdapter

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
                OpenAIAdapter(model="gpt-4o-mini")

    def test_raises_import_error_when_package_missing(self):
        """Should raise ImportError with install hint when langchain-openai is absent."""
        from linguaalayam.llm.adapters.openai import OpenAIAdapter

        # Setting a module to None in sys.modules causes ImportError on import
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict("sys.modules", {"langchain_openai": None}),
        ):
            with pytest.raises(ImportError, match="langchain-openai"):
                OpenAIAdapter(model="gpt-4o-mini")


class TestNoLLMAdapter:
    """NoLLMAdapter no-op behaviour."""

    def test_has_llm_false(self):
        """has_llm should return False for NoLLMAdapter."""
        assert not NoLLMAdapter().has_llm

    def test_complete_raises(self):
        """complete should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            NoLLMAdapter().complete("s", "u")

    def test_extract_structured_raises(self):
        """extract_structured should raise NotImplementedError."""
        with pytest.raises(NotImplementedError):
            NoLLMAdapter().extract_structured(object, "prompt")

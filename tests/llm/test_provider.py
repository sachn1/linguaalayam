"""Tests for LLM instantiation via Hydra — verifies configs produce the right adapters."""

import os
from unittest.mock import MagicMock, patch

from hydra.utils import instantiate
from omegaconf import OmegaConf

from linguaalayam.llm.adapters import AnthropicAdapter, NoLLMAdapter, OpenAIAdapter


def _cfg(target: str, **kwargs):
    """Build a minimal Hydra-compatible OmegaConf config with _target_."""
    return OmegaConf.create({"_target_": target, **kwargs})


class TestInstantiateAnthropic:
    """Hydra instantiation of AnthropicAdapter."""

    _TARGET = "linguaalayam.llm.adapters.anthropic.AnthropicAdapter"

    def test_returns_anthropic_adapter(self):
        """instantiate should produce an AnthropicAdapter instance."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.adapters.anthropic.ChatAnthropic"),
        ):
            result = instantiate(_cfg(self._TARGET, model="claude-3-5-sonnet-20241022"))
        assert isinstance(result, AnthropicAdapter)

    def test_passes_temperature(self):
        """Temperature kwarg should be forwarded to ChatAnthropic."""
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.adapters.anthropic.ChatAnthropic") as mock_ca,
        ):
            mock_ca.return_value = MagicMock()
            instantiate(_cfg(self._TARGET, model="claude-3-5-sonnet-20241022", temperature=0.5))
        _, kwargs = mock_ca.call_args
        assert kwargs.get("temperature") == 0.5


class TestInstantiateOpenAI:
    """Hydra instantiation of OpenAIAdapter."""

    _TARGET = "linguaalayam.llm.adapters.openai.OpenAIAdapter"

    def test_returns_openai_adapter(self):
        """instantiate should produce an OpenAIAdapter instance."""
        mock_openai = MagicMock()
        with (
            patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}),
            patch.dict("sys.modules", {"langchain_openai": MagicMock(ChatOpenAI=mock_openai)}),
        ):
            result = instantiate(_cfg(self._TARGET, model="gpt-4o-mini"))
        assert isinstance(result, OpenAIAdapter)


class TestInstantiateNoLLM:
    """Hydra instantiation of NoLLMAdapter."""

    _TARGET = "linguaalayam.llm.adapters.nollm.NoLLMAdapter"

    def test_returns_nollm_adapter(self):
        """instantiate should produce a NoLLMAdapter instance."""
        result = instantiate(_cfg(self._TARGET))
        assert isinstance(result, NoLLMAdapter)

    def test_has_llm_false(self):
        """Instantiated NoLLMAdapter should report has_llm=False."""
        result = instantiate(_cfg(self._TARGET))
        assert not result.has_llm

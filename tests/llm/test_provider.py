"""Tests for llm/provider.py — get_llm factory."""

import os
from unittest.mock import MagicMock, patch

import pytest
from omegaconf import OmegaConf

from linguaalayam.llm import get_llm


def _cfg(provider: str, model: str = "test-model", **extra) -> object:
    return OmegaConf.create({"provider": provider, "model": model, **extra})


class TestGetLlmAnthropic:
    def test_returns_anthropic_model(self):
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.provider.ChatAnthropic") as mock_ca,
        ):
            mock_ca.return_value = MagicMock()
            result = get_llm(_cfg("anthropic", model="claude-3-5-sonnet-20241022"))
        mock_ca.assert_called_once()
        assert result is not None

    def test_raises_when_key_missing(self):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            os.environ.pop("ANTHROPIC_API_KEY", None)
            with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
                get_llm(_cfg("anthropic"))

    def test_passes_temperature(self):
        with (
            patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}),
            patch("linguaalayam.llm.provider.ChatAnthropic") as mock_ca,
        ):
            mock_ca.return_value = MagicMock()
            get_llm(_cfg("anthropic", temperature=0.5))
        _, kwargs = mock_ca.call_args
        assert kwargs.get("temperature") == 0.5


class TestGetLlmHuggingFace:
    def test_returns_chat_huggingface(self):
        mock_pipeline = MagicMock()
        mock_chat = MagicMock()
        with (
            patch("linguaalayam.llm.provider.HuggingFacePipeline") as mock_hfp,
            patch("linguaalayam.llm.provider.ChatHuggingFace") as mock_chf,
        ):
            mock_hfp.from_model_id.return_value = mock_pipeline
            mock_chf.return_value = mock_chat
            result = get_llm(_cfg("huggingface", model="gpt2", temperature=0.0))
        mock_hfp.from_model_id.assert_called_once()
        mock_chf.assert_called_once()
        assert result is mock_chat

    def test_do_sample_false_when_temperature_zero(self):
        mock_pipeline = MagicMock()
        with (
            patch("linguaalayam.llm.provider.HuggingFacePipeline") as mock_hfp,
            patch("linguaalayam.llm.provider.ChatHuggingFace"),
        ):
            mock_hfp.from_model_id.return_value = mock_pipeline
            get_llm(_cfg("huggingface", model="gpt2", temperature=0.0))
        kwargs = mock_hfp.from_model_id.call_args[1]
        assert not kwargs["pipeline_kwargs"]["do_sample"]


class TestGetLlmUnknown:
    def test_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm(_cfg("openai"))

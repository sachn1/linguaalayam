"""LLM provider factory — returns a LangChain BaseChatModel for the configured provider."""

import os

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models import BaseChatModel
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from omegaconf import DictConfig


def get_llm(cfg: DictConfig) -> BaseChatModel:
    """Instantiate a chat model from the llm config group.

    Supported providers:
      - anthropic: ChatAnthropic (requires ANTHROPIC_API_KEY env var)
      - huggingface: ChatHuggingFace wrapping HuggingFacePipeline (runs locally)
                     Install the optional group: poetry install --with huggingface
    """
    provider = cfg.provider

    if provider == "anthropic":
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
            )
        return ChatAnthropic(
            model=cfg.model,
            temperature=cfg.get("temperature", 0.0),
            max_tokens=cfg.get("max_tokens", 1024),
        )

    if provider == "huggingface":
        pipeline = HuggingFacePipeline.from_model_id(
            model_id=cfg.model,
            task="text-generation",
            pipeline_kwargs={
                "max_new_tokens": cfg.get("max_new_tokens", 512),
                "do_sample": cfg.get("temperature", 0.0) > 0,
                "temperature": cfg.get("temperature", 0.0) or None,
            },
        )
        return ChatHuggingFace(llm=pipeline)

    raise ValueError(f"Unknown LLM provider: {provider!r}. Expected 'anthropic' or 'huggingface'.")

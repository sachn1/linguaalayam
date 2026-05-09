"""Anthropic adapter — wraps ChatAnthropic via LangChain."""

import os
from typing import TypeVar, Type

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from .base import LLMAdapter

T = TypeVar("T")


class AnthropicAdapter(LLMAdapter):
    def __init__(self, model: str, temperature: float = 0.0, max_tokens: int = 1024):
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. "
                "Add it to your .env file: ANTHROPIC_API_KEY=sk-ant-..."
            )
        self._llm = ChatAnthropic(model=model, temperature=temperature, max_tokens=max_tokens)

    def complete(self, system: str, user: str) -> str:
        response = self._llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return response.content

    def extract_structured(self, schema: Type[T], prompt: str) -> T:
        return self._llm.with_structured_output(schema).invoke(prompt)

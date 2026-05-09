"""OpenAI adapter — wraps ChatOpenAI via LangChain."""

import os
from typing import TypeVar, Type

from langchain_core.messages import HumanMessage, SystemMessage

from .base import LLMAdapter

T = TypeVar("T")


class OpenAIAdapter(LLMAdapter):
    def __init__(self, model: str, temperature: float = 0.0, max_tokens: int = 1024):
        if not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError(
                "OPENAI_API_KEY is not set. "
                "Add it to your .env file: OPENAI_API_KEY=sk-..."
            )
        try:
            from langchain_openai import ChatOpenAI
        except ImportError as exc:
            raise ImportError(
                "langchain-openai is required for the OpenAI provider. "
                "Run: poetry add langchain-openai"
            ) from exc
        self._llm = ChatOpenAI(model=model, temperature=temperature, max_tokens=max_tokens)

    def complete(self, system: str, user: str) -> str:
        response = self._llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        return response.content

    def extract_structured(self, schema: Type[T], prompt: str) -> T:
        return self._llm.with_structured_output(schema).invoke(prompt)

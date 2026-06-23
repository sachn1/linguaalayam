"""Shared app state — singletons accessed by both API and web routers."""

from linguaalayam.rag.tools import DictionaryTools
from linguaalayam.translation.base import TranslationService

_tools: DictionaryTools | None = None
_translator: TranslationService | None = None


def set_tools(tools: DictionaryTools) -> None:
    global _tools
    _tools = tools


def get_tools() -> DictionaryTools:
    if _tools is None:
        raise RuntimeError("DictionaryTools not initialised — lifespan may not have run")
    return _tools


def set_translator(translator: TranslationService) -> None:
    global _translator
    _translator = translator


def get_translator() -> TranslationService:
    if _translator is None:
        raise RuntimeError("TranslationService not initialised — lifespan may not have run")
    return _translator

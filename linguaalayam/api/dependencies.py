"""Shared app state — DictionaryTools singleton accessed by both API and web routers."""

from linguaalayam.rag.tools import DictionaryTools

_tools: DictionaryTools | None = None


def set_tools(tools: DictionaryTools) -> None:
    global _tools
    _tools = tools


def get_tools() -> DictionaryTools:
    if _tools is None:
        raise RuntimeError("DictionaryTools not initialised — lifespan may not have run")
    return _tools

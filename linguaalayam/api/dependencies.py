"""Shared app state — singletons accessed by both API and web routers."""

from linguaalayam.rag.tools import DictionaryTools
from linguaalayam.translation.base import TranslationService

_tools: DictionaryTools | None = None
_translator: TranslationService | None = None


def set_tools(tools: DictionaryTools) -> None:
    """Store the shared DictionaryTools singleton.

    Parameters
    ----------
    tools : DictionaryTools
        Fully initialised retrieval tools to make available to request handlers.
    """
    global _tools
    _tools = tools


def get_tools() -> DictionaryTools:
    """Return the shared DictionaryTools singleton.

    Returns
    -------
    DictionaryTools
        The active retrieval tools.

    Raises
    ------
    RuntimeError
        If called before ``set_tools`` (i.e. before the lifespan context runs).
    """
    if _tools is None:
        raise RuntimeError("DictionaryTools not initialised — lifespan may not have run")
    return _tools


def set_translator(translator: TranslationService) -> None:
    """Store the shared TranslationService singleton.

    Parameters
    ----------
    translator : TranslationService
        Fully initialised translation service to make available to request handlers.
    """
    global _translator
    _translator = translator


def get_translator() -> TranslationService:
    """Return the shared TranslationService singleton.

    Returns
    -------
    TranslationService
        The active translation service.

    Raises
    ------
    RuntimeError
        If called before ``set_translator`` (i.e. before the lifespan context runs).
    """
    if _translator is None:
        raise RuntimeError("TranslationService not initialised — lifespan may not have run")
    return _translator

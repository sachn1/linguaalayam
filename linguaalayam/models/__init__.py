"""Models package — ORM, entry dataclasses, and the Embeddable protocol."""

from .entries import Embeddable
from .orm import DictionaryEntry

__all__ = ["DictionaryEntry", "Embeddable"]

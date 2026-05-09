"""Data models for dictionary entries from various sources."""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embeddable(Protocol):
    """Protocol for entries that can be embedded."""

    source: str
    headword: str

    def to_embed_text(self) -> str:
        """Convert the entry to a text representation suitable for embedding.

        Returns
        -------
        str
            Text representation of the entry.
        """
        ...


@dataclass
class EnMlEntry:
    """Data model for English-Malayalam dictionary entries from Olam."""

    headword: str
    definitions: list[tuple[str | None, str]]  # [(pos, definition), ...]
    source: str = "olam_enml"

    def to_embed_text(self) -> str:
        """Convert input to text representation specific for EnML.

        >>> EnMlEntry(headword="run", definitions=[("v", "ഓടുക"), ("v", "പായുക")]).to_embed_text()
        'word: run\\n  [v] ഓടുക; പായുക'
        >>> EnMlEntry(headword="light", definitions=[("n", "വെളിച്ചം"), ("adj", "ഭാരം കുറഞ്ഞ")]).to_embed_text()
        'word: light\\n  [n] വെളിച്ചം\\n  [adj] ഭാരം കുറഞ്ഞ'
        """
        by_pos: dict[str, list[str]] = {}
        for pos, defn in self.definitions:
            by_pos.setdefault(pos or "general", []).append(defn)

        lines = [f"word: {self.headword}"]
        for pos, defns in by_pos.items():
            lines.append(f"  [{pos}] {'; '.join(defns)}")
        return "\n".join(lines)


@dataclass
class MlMlEntry:
    """Data model for Malayalam-Malayalam dictionary entries from Datuk."""

    headword: str
    definitions: list[tuple[str | None, str]]  # [(pos, definition), ...]
    source: str = "datuk"

    def to_embed_text(self) -> str:
        """Convert input to text representation specific for MlMl."""
        by_pos: dict[str, list[str]] = {}
        for pos, defn in self.definitions:
            by_pos.setdefault(pos or "general", []).append(defn)

        lines = [f"word: {self.headword}"]
        for pos, defns in by_pos.items():
            lines.append(f"  [{pos}] {'; '.join(defns)}")
        return "\n".join(lines)


@dataclass
class CrossLingualEntry:
    """Data model for cross-lingual comparative entries from the Dravidian Comparative Dictionary."""

    headword: str
    sense_index: int | None
    ml_gloss: list[str]
    equivalents: dict[str, tuple[str, list[str]]]  # lang -> (word, glosses)
    source: str = "dravidian_comparative"

    def to_embed_text(self) -> str:
        """Convert input to text representation specific for cross-lingual entries.

        >>> e = CrossLingualEntry(headword="water", sense_index=None, ml_gloss=["വെള്ളം"], equivalents={"kn": ("ನೀರು", [])})
        >>> e.to_embed_text()
        'word: water\\n  [ml] വെള്ളം\\n  [kn] ನೀರು'
        >>> e2 = CrossLingualEntry(headword="hand", sense_index=1, ml_gloss=[], equivalents={})
        >>> e2.to_embed_text()
        'word: hand (sense 1)'
        """
        sense = f" (sense {self.sense_index})" if self.sense_index else ""
        lines = [f"word: {self.headword}{sense}"]

        if self.ml_gloss:
            lines.append(f"  [ml] {'; '.join(self.ml_gloss)}")

        for lang, (equiv_word, glosses) in self.equivalents.items():
            gloss_str = f" - {'; '.join(glosses)}" if glosses else ""
            lines.append(f"  [{lang}] {equiv_word}{gloss_str}")

        return "\n".join(lines)

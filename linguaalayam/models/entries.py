from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embeddable(Protocol):
    source: str
    headword: str

    def to_embed_text(self) -> str: ...


# ---------------------------------------------------------------------------
# EN -> ML  (olam_enml)
# ---------------------------------------------------------------------------

@dataclass
class EnMlEntry:
    headword: str
    definitions: list[tuple[str | None, str]]  # [(pos, definition), ...]
    source: str = "olam_enml"

    def to_embed_text(self) -> str:
        by_pos: dict[str, list[str]] = {}
        for pos, defn in self.definitions:
            by_pos.setdefault(pos or "general", []).append(defn)

        lines = [f"word: {self.headword}"]
        for pos, defns in by_pos.items():
            lines.append(f"  [{pos}] {'; '.join(defns)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# ML -> ML  (datuk)
# ---------------------------------------------------------------------------

@dataclass
class MlMlEntry:
    headword: str
    definitions: list[tuple[str | None, str]]  # [(pos, definition), ...]
    source: str = "datuk"

    def to_embed_text(self) -> str:
        by_pos: dict[str, list[str]] = {}
        for pos, defn in self.definitions:
            by_pos.setdefault(pos or "general", []).append(defn)

        lines = [f"word: {self.headword}"]
        for pos, defns in by_pos.items():
            lines.append(f"  [{pos}] {'; '.join(defns)}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Cross-lingual Dravidian comparative
# ---------------------------------------------------------------------------

@dataclass
class CrossLingualEntry:
    headword: str
    sense_index: int | None
    ml_gloss: list[str]
    equivalents: dict[str, tuple[str, list[str]]]  # lang -> (word, glosses)
    source: str = "dravidian_comparative"

    def to_embed_text(self) -> str:
        sense = f" (sense {self.sense_index})" if self.sense_index else ""
        lines = [f"word: {self.headword}{sense}"]

        if self.ml_gloss:
            lines.append(f"  [ml] {'; '.join(self.ml_gloss)}")

        for lang, (equiv_word, glosses) in self.equivalents.items():
            gloss_str = f" - {'; '.join(glosses)}" if glosses else ""
            lines.append(f"  [{lang}] {equiv_word}{gloss_str}")

        return "\n".join(lines)
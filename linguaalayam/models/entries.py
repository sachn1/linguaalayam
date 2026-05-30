"""Data models for dictionary entries from various sources."""

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@runtime_checkable
class Embeddable(Protocol):
    """Protocol for entries that can be embedded into a vector space.

    Any object satisfying this protocol can be passed to
    :class:`~linguaalayam.embeddings.service.EmbeddingService` and stored
    in the database via :func:`~linguaalayam.database.queries.batch_insert`.

    Attributes
    ----------
    source : str
        Identifier for the originating corpus (e.g. ``"olam_enml"``).
    headword : str
        The primary lookup key for the entry.
    """

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


def _definition_embed_text(headword: str, definitions: list[tuple[str | None, str]]) -> str:
    """Shared embed-text format for definition-based entry types (EnMlEntry, MlMlEntry)."""
    by_pos: dict[str, list[str]] = {}
    for pos, defn in definitions:
        by_pos.setdefault(pos or "general", []).append(defn)
    lines = [f"word: {headword}"]
    for pos, defns in by_pos.items():
        lines.append(f"  [{pos}] {'; '.join(defns)}")
    return "\n".join(lines)


@dataclass
class EnMlEntry:
    """English–Malayalam dictionary entry from the Olam corpus.

    Attributes
    ----------
    headword : str
        The English word or phrase being defined.
    definitions : list[tuple[str | None, str]]
        Ordered list of ``(part-of-speech, Malayalam definition)`` pairs.
        POS is ``None`` when the source does not specify one.
    source : str
        Corpus identifier; defaults to ``"olam_enml"``.
    """

    headword: str
    definitions: list[tuple[str | None, str]]  # [(pos, definition), ...]
    source: str = "olam_enml"

    def to_embed_text(self) -> str:
        """Convert to embed-text format grouping definitions by part of speech."""
        return _definition_embed_text(self.headword, self.definitions)


@dataclass
class MlMlEntry:
    """Malayalam–Malayalam dictionary entry from the Datuk corpus.

    Attributes
    ----------
    headword : str
        The Malayalam word being defined.
    definitions : list[tuple[str | None, str]]
        Ordered list of ``(part-of-speech, Malayalam definition)`` pairs.
        POS is ``None`` when the source does not specify one.
    source : str
        Corpus identifier; defaults to ``"datuk"``.
    """

    headword: str
    definitions: list[tuple[str | None, str]]  # [(pos, definition), ...]
    source: str = "datuk"

    def to_embed_text(self) -> str:
        """Convert to embed-text format grouping definitions by part of speech."""
        return _definition_embed_text(self.headword, self.definitions)


@dataclass
class EkkurupSense:
    """One sense (POS cluster) within an Ekkurup thesaurus entry.

    Attributes
    ----------
    pos : str or None
        Part-of-speech label (e.g. ``"verb"``, ``"noun"``, ``"idiom"``).
        ``None`` when the source omits a POS tag.
    en : list[list[str]]
        Grouped English synonym clusters. Each inner list is a set of
        near-synonymous English words for this sense.
    ml : list[list[str]]
        Grouped Malayalam translation clusters. Each inner list corresponds
        to the matching ``en`` cluster.
    """

    pos: str | None
    en: list[list[str]] = field(default_factory=list)  # grouped English synonym clusters
    ml: list[list[str]] = field(default_factory=list)  # grouped Malayalam translation clusters


@dataclass
class EkkurupEntry:
    """English–Malayalam thesaurus entry from the Ekkurup corpus.

    Attributes
    ----------
    headword : str
        The English word or phrase.
    senses : list[EkkurupSense]
        All sense clusters for this headword, each with its own POS,
        English synonyms, and Malayalam translations.
    source : str
        Corpus identifier; defaults to ``"ekkurup"``.
    """

    headword: str
    senses: list[EkkurupSense]
    source: str = "ekkurup"

    def to_embed_text(self) -> str:
        """Convert input to text representation specific for Ekkurup."""
        lines = [f"word: {self.headword}"]
        for sense in self.senses:
            pos_tag = f"[{sense.pos}]" if sense.pos else "[general]"
            en_flat = "; ".join(", ".join(g) for g in sense.en if g)
            ml_flat = "; ".join(", ".join(g) for g in sense.ml if g)
            if en_flat:
                lines.append(f"  {pos_tag} en: {en_flat}")
            if ml_flat:
                lines.append(f"  {pos_tag} ml: {ml_flat}")
        return "\n".join(lines)

"""Shared corpus-parser infrastructure — TSV helper."""

from collections import defaultdict
from pathlib import Path
from typing import TypeVar

T = TypeVar("T")

_EMPTY_POS: frozenset[str] = frozenset({"", "-"})


def parse_definition_tsv(filepath: Path, entry_cls: type[T]) -> list[T]:
    """Parse a three-column definition TSV (headword, POS, definition).

    Shared by the Olam EN→ML and Datuk ML→ML parsers. Entries with the
    same headword are merged into a single object.

    Parameters
    ----------
    filepath : Path
        Path to the tab-separated corpus file (UTF-8).
    entry_cls : type[T]
        Dataclass constructor called as ``entry_cls(headword=..., definitions=...)``.

    Returns
    -------
    list[T]
        One instance per unique headword.
    """
    raw: dict[str, list[tuple[str | None, str]]] = defaultdict(list)

    with filepath.open(encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue

            headword, pos_raw, definition = parts
            pos: str | None = pos_raw.strip("{}") or None
            if pos in _EMPTY_POS:
                pos = None

            raw[headword].append((pos, definition))

    return [entry_cls(headword=hw, definitions=defns) for hw, defns in raw.items()]

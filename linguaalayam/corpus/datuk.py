from collections import defaultdict
from pathlib import Path

from linguaalayam.models.entries import MlMlEntry

_EMPTY_POS = {"", "-"}


def parse(filepath: Path) -> list[MlMlEntry]:
    raw: dict[str, list[tuple[str | None, str]]] = defaultdict(list)

    with filepath.open(encoding="utf-8") as f:
        for line in f:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 3:
                continue

            headword, pos_raw, definition = parts
            pos = pos_raw.strip("{}") or None
            if pos in _EMPTY_POS:
                pos = None

            raw[headword].append((pos, definition))

    return [MlMlEntry(headword=hw, definitions=defns) for hw, defns in raw.items()]

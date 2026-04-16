import re
from pathlib import Path

from linguaalayam.models.entries import CrossLingualEntry

_SENSE_RE = re.compile(r"^(.+?)\s*\((\d+)\)\s*(?:-\s*(.+))?$")
_PLAIN_RE = re.compile(r"^(.+?)\s*-\s*(.+)$")
_LANG_COLS = {"kn": 1, "ta": 2, "te": 3}


def _split_gloss(cell: str) -> tuple[str, list[str]]:
    m = _PLAIN_RE.match(cell.strip())
    if m:
        word = m.group(1).strip()
        glosses = [g.strip() for g in m.group(2).split(",") if g.strip()]
        return word, glosses
    return cell.strip(), []


def parse(filepath: Path) -> list[CrossLingualEntry]:
    entries: list[CrossLingualEntry] = []

    with filepath.open(encoding="utf-8") as f:
        f.readline()  # skip header

        for line in f:
            cols = line.rstrip("\n").split("\t")
            if len(cols) < 4:
                continue

            ml_col = cols[0].strip()

            if m := _SENSE_RE.match(ml_col):
                headword = m.group(1).strip()
                sense_index = int(m.group(2))
                ml_gloss = [g.strip() for g in m.group(3).split(",")] if m.group(3) else []
            elif m := _PLAIN_RE.match(ml_col):
                headword = m.group(1).strip()
                sense_index = None
                ml_gloss = [g.strip() for g in m.group(2).split(",") if g.strip()]
            else:
                headword = ml_col
                sense_index = None
                ml_gloss = []

            equivalents = {}
            for lang, col_idx in _LANG_COLS.items():
                cell = cols[col_idx].strip() if col_idx < len(cols) else ""
                if cell:
                    equivalents[lang] = _split_gloss(cell)

            entries.append(
                CrossLingualEntry(
                    headword=headword,
                    sense_index=sense_index,
                    ml_gloss=ml_gloss,
                    equivalents=equivalents,
                )
            )

    return entries

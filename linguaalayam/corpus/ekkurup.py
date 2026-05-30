"""Parser for the Ekkurup English–Malayalam thesaurus corpus (YAML format)."""

from pathlib import Path

import yaml

from linguaalayam.models.entries import EkkurupEntry, EkkurupSense


def parse(filepath: Path) -> list[EkkurupEntry]:
    """Parse the Ekkurup YAML thesaurus file into a list of entries.

    Each document entry has a ``head`` (English headword) and a ``senses``
    list. Each sense carries a part-of-speech label, grouped English synonym
    clusters (``en``), and grouped Malayalam translation clusters (``ml``).
    Entries with no senses are skipped.

    Parameters
    ----------
    filepath : Path
        Path to the Ekkurup YAML corpus file (UTF-8).

    Returns
    -------
    list[EkkurupEntry]
        One entry per headword; entries with empty sense lists are omitted.
    """
    with filepath.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    entries: list[EkkurupEntry] = []
    for item in data:
        headword = item.get("head", "").strip()
        if not headword:
            continue

        senses: list[EkkurupSense] = []
        for sense_data in item.get("senses", []):
            pos = sense_data.get("pos") or None
            en = sense_data.get("en") or []
            ml = sense_data.get("ml") or []
            senses.append(EkkurupSense(pos=pos, en=en, ml=ml))

        if senses:
            entries.append(EkkurupEntry(headword=headword, senses=senses))

    return entries

"""Parser for the Datuk Malayalam–Malayalam (ML→ML) corpus."""

from pathlib import Path

from linguaalayam.corpus.base import parse_definition_tsv
from linguaalayam.models.entries import DatukEntry


def parse(filepath: Path) -> list[DatukEntry]:
    """Parse the Datuk ML→ML TSV file into a list of entries.

    Each line has three tab-separated columns: Malayalam headword,
    part-of-speech tag (wrapped in ``{}``), and a Malayalam definition.
    Lines with a different column count are silently skipped. Entries
    sharing the same headword are merged into a single :class:`DatukEntry`.

    Parameters
    ----------
    filepath : Path
        Path to the Datuk corpus file (tab-separated, UTF-8).

    Returns
    -------
    list[DatukEntry]
        One entry per unique headword, with all POS/definition pairs collected.
    """
    return parse_definition_tsv(filepath, DatukEntry)

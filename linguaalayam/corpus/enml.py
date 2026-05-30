"""Parser for the Olam English–Malayalam (EN→ML) corpus."""

from pathlib import Path

from linguaalayam.corpus.base import parse_definition_tsv
from linguaalayam.models.entries import EnMlEntry


def parse(filepath: Path) -> list[EnMlEntry]:
    """Parse the Olam EN→ML TSV file into a list of entries.

    Each line has three tab-separated columns: headword, part-of-speech tag
    (wrapped in ``{}``), and a Malayalam definition. Lines with a different
    column count are silently skipped. Entries sharing the same headword are
    merged into a single :class:`EnMlEntry` with multiple definitions.

    Parameters
    ----------
    filepath : Path
        Path to the Olam EN→ML corpus file (tab-separated, UTF-8).

    Returns
    -------
    list[EnMlEntry]
        One entry per unique headword, with all POS/definition pairs collected.
    """
    return parse_definition_tsv(filepath, EnMlEntry)

"""Parser for the Sayahna Shabdataaravali ML→ML corpus (XDXF XML format)."""

from pathlib import Path
from xml.etree import ElementTree

from linguaalayam.models.entries import SayahnaEntry


def _parse_file(filepath: Path) -> list[SayahnaEntry]:
    """Parse a single XDXF XML file into entries."""
    tree = ElementTree.parse(filepath)  # noqa: S314
    entries: list[SayahnaEntry] = []

    for ar in tree.iter("ar"):
        k_el = ar.find("k")
        if k_el is None or not (k_el.text or "").strip():
            continue
        headword = k_el.text.strip()

        definitions: list[tuple[str | None, str]] = []
        explanations: list[str] = []

        outer_def = ar.find("def")
        if outer_def is None:
            continue

        gr_el = outer_def.find("gr")
        pos: str | None = gr_el.text.strip() if gr_el is not None and gr_el.text else None

        for inner_def in outer_def.findall("def"):
            deftext = inner_def.find("deftext")
            if deftext is not None and deftext.text:
                definitions.append((pos, deftext.text.strip()))

            expl = inner_def.find("expl")
            if expl is not None and expl.text:
                explanations.append(expl.text.strip())

        if definitions:
            entries.append(
                SayahnaEntry(
                    headword=headword,
                    definitions=definitions,
                    explanations=explanations,
                )
            )

    return entries


def parse(filepath: Path) -> list[SayahnaEntry]:
    """Parse all XDXF XML files in the Sayahna corpus directory.

    Parameters
    ----------
    filepath : Path
        Path to the directory containing ``*.xml`` files.

    Returns
    -------
    list[SayahnaEntry]
        Combined entries from all XML files, sorted by filename.
    """
    entries: list[SayahnaEntry] = []
    for xml_file in sorted(filepath.glob("*.xml")):
        entries.extend(_parse_file(xml_file))
    return entries

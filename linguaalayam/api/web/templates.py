"""Jinja2 template environment shared by every route in this package."""

import importlib.metadata
from pathlib import Path

from fastapi.templating import Jinja2Templates

from linguaalayam.transliteration import malayalam_to_roman

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).resolve().parents[2] / "templates"))
TEMPLATES.env.filters["romanise_ml"] = malayalam_to_roman
TEMPLATES.env.globals["app_version"] = importlib.metadata.version("linguaalayam")


def group_definitions(
    definitions: list[tuple[str | None, str]],
) -> list[tuple[str | None, list[str]]]:
    """Group a flat list of ``(pos, text)`` pairs into ``(pos, [text, ...])`` groups.

    Preserves the first-seen order of POS tags while merging all definitions
    that share the same POS into a single list.

    Parameters
    ----------
    definitions : list[tuple[str | None, str]]
        Flat list of ``(part-of-speech, definition-text)`` pairs as stored in the DB.

    Returns
    -------
    list[tuple[str | None, list[str]]]
        Ordered list of ``(pos, [definitions])`` groups, one per unique POS.
    """
    seen: dict[str | None, list[str]] = {}
    order: list[str | None] = []
    for pos, text in definitions:
        if pos not in seen:
            seen[pos] = []
            order.append(pos)
        seen[pos].append(text)
    return [(pos, seen[pos]) for pos in order]


TEMPLATES.env.filters["group_definitions"] = group_definitions

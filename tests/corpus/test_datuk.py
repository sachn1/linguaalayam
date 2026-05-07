import textwrap
from pathlib import Path

from linguaalayam.corpus import datuk
from linguaalayam.models.entries import MlMlEntry

_DATUK = """\
ഓടുക\t{v}\tto run fast
ഓടുക\t{v}\tto race
ആകാശം\t{n}\tthe sky
"""


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "datuk.tsv"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


def test_groups_by_headword(tmp_path):
    entries = datuk.parse(_write(tmp_path, _DATUK))
    assert len(entries) == 2


def test_merges_definitions(tmp_path):
    entries = datuk.parse(_write(tmp_path, _DATUK))
    oduka = next(e for e in entries if e.headword == "ഓടുക")
    assert len(oduka.definitions) == 2


def test_pos_normalised(tmp_path):
    entries = datuk.parse(_write(tmp_path, _DATUK))
    oduka = next(e for e in entries if e.headword == "ഓടുക")
    assert all(pos == "v" for pos, _ in oduka.definitions)


def test_empty_pos_becomes_none(tmp_path):
    content = "headword\t{}\tdefinition\n"
    entries = datuk.parse(_write(tmp_path, content))
    assert entries[0].definitions[0][0] is None


def test_dash_pos_becomes_none(tmp_path):
    content = "headword\t{-}\tdefinition\n"
    entries = datuk.parse(_write(tmp_path, content))
    assert entries[0].definitions[0][0] is None


def test_source(tmp_path):
    entries = datuk.parse(_write(tmp_path, _DATUK))
    assert all(e.source == "datuk" for e in entries)


def test_returns_correct_type(tmp_path):
    entries = datuk.parse(_write(tmp_path, _DATUK))
    assert all(isinstance(e, MlMlEntry) for e in entries)


def test_skips_malformed_lines(tmp_path):
    content = _DATUK + "bad line without tabs\n"
    entries = datuk.parse(_write(tmp_path, content))
    assert len(entries) == 2


def test_embed_text_contains_headword_and_definition(tmp_path):
    entries = datuk.parse(_write(tmp_path, _DATUK))
    oduka = next(e for e in entries if e.headword == "ഓടുക")
    text = oduka.to_embed_text()
    assert "ഓടുക" in text
    assert "to run fast" in text

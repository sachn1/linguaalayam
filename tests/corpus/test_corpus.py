"""Integration-style tests for the enml corpus parser."""

import textwrap
from pathlib import Path

from linguaalayam.corpus import enml
from linguaalayam.models.entries import OlamEntry


def _write(tmp_path: Path, name: str, content: str) -> Path:
    """Write dedented content to a named temp file and return its path."""
    path = tmp_path / name
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# EnML
# ---------------------------------------------------------------------------

ENML = """\
A\t{-}\tആപ്ലിറ്റ്യൂഡ്
A\t{n}\tആട്ടോമാറ്റിക്
A bed of roses\t{n}\tപൂമെത്ത
A bed of roses\t{idm}\tസുഖകരമായ അവസ്ഥ
"""


def test_enml_groups_by_headword(tmp_path):
    """Parse should produce one entry per unique headword."""
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    assert len(entries) == 2


def test_enml_merges_definitions(tmp_path):
    """Multiple rows for the same headword should be merged into one entry."""
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    a = next(e for e in entries if e.headword == "A")
    assert len(a.definitions) == 2


def test_enml_normalises_empty_pos_to_none(tmp_path):
    """POS fields like {-} should be normalised to None."""
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    a = next(e for e in entries if e.headword == "A")
    assert any(pos is None for pos, _ in a.definitions)


def test_enml_source(tmp_path):
    """All entries should carry source='olam_enml'."""
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    assert all(e.source == "olam_enml" for e in entries)


def test_enml_returns_correct_type(tmp_path):
    """Parser should return OlamEntry instances."""
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    assert all(isinstance(e, OlamEntry) for e in entries)


def test_enml_embed_text_contains_headword_and_definitions(tmp_path):
    """embed_text should include the headword and all definition strings."""
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    roses = next(e for e in entries if e.headword == "A bed of roses")
    text = roses.to_embed_text()
    assert "A bed of roses" in text
    assert "പൂമെത്ത" in text
    assert "സുഖകരമായ അവസ്ഥ" in text


def test_enml_skips_malformed_lines(tmp_path):
    """Lines without the expected tab structure should be silently skipped."""
    entries = enml.parse(_write(tmp_path, "enml", ENML + "bad line\n"))
    assert len(entries) == 2

"""Tests for the Ekkurup EN→ML thesaurus parser (YAML format)."""

import textwrap
from pathlib import Path

from linguaalayam.corpus import ekkurup
from linguaalayam.models.entries import EkkurupEntry, EkkurupSense


def _write(tmp_path: Path, content: str) -> Path:
    """Write content to a temporary ekkurup.yml file."""
    p = tmp_path / "ekkurup.yml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return p


_YAML = """\
- head: run
  senses:
    - pos: verb
      en: [[sprint, dash, race], [flee, escape]]
      ml: [[ഓടുക, പായുക], [രക്ഷപ്പെടുക]]
    - pos: noun
      en: [[jog, dash]]
      ml: [[ഓട്ടം]]
- head: take someone aback
  senses:
    - pos: idiom
      en: [[astonish, stun, surprise]]
      ml: [[അമ്പരപ്പിക്കുക, ആശ്ചര്യപ്പെടുത്തുക]]
- head: empty
  senses: []
"""


def test_parse_returns_entries_with_senses(tmp_path):
    """Entries with empty sense lists should be omitted."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    # "empty" has no senses so it is skipped
    assert len(entries) == 2


def test_headwords_correct(tmp_path):
    """Parser should preserve headwords including multi-word phrases."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    headwords = {e.headword for e in entries}
    assert "run" in headwords
    assert "take someone aback" in headwords


def test_source(tmp_path):
    """All entries should carry source='ekkurup'."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    assert all(e.source == "ekkurup" for e in entries)


def test_returns_correct_type(tmp_path):
    """Parser should return EkkurupEntry instances."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    assert all(isinstance(e, EkkurupEntry) for e in entries)


def test_senses_preserved(tmp_path):
    """All senses and their POS labels should be preserved."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    run = next(e for e in entries if e.headword == "run")
    assert len(run.senses) == 2
    assert run.senses[0].pos == "verb"
    assert run.senses[1].pos == "noun"


def test_en_synonyms_preserved(tmp_path):
    """Grouped English synonym clusters should be kept as nested lists."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    run = next(e for e in entries if e.headword == "run")
    verb_sense = run.senses[0]
    assert ["sprint", "dash", "race"] in verb_sense.en
    assert ["flee", "escape"] in verb_sense.en


def test_ml_translations_preserved(tmp_path):
    """Grouped Malayalam translation clusters should be kept as nested lists."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    run = next(e for e in entries if e.headword == "run")
    verb_sense = run.senses[0]
    assert ["ഓടുക", "പായുക"] in verb_sense.ml


def test_embed_text_contains_headword(tmp_path):
    """embed_text should start with 'word: <headword>'."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    run = next(e for e in entries if e.headword == "run")
    text = run.to_embed_text()
    assert "word: run" in text


def test_embed_text_contains_en_synonyms(tmp_path):
    """embed_text should include English synonyms from all senses."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    run = next(e for e in entries if e.headword == "run")
    text = run.to_embed_text()
    assert "sprint" in text
    assert "flee" in text


def test_embed_text_contains_ml_translations(tmp_path):
    """embed_text should include Malayalam translations from all senses."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    run = next(e for e in entries if e.headword == "run")
    text = run.to_embed_text()
    assert "ഓടുക" in text
    assert "ഓട്ടം" in text


def test_embed_text_has_pos_tag(tmp_path):
    """embed_text should include bracketed POS tags for each sense."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    run = next(e for e in entries if e.headword == "run")
    text = run.to_embed_text()
    assert "[verb]" in text
    assert "[noun]" in text


def test_skips_entry_with_no_senses(tmp_path):
    """Entries with an empty senses list should be excluded from output."""
    entries = ekkurup.parse(_write(tmp_path, _YAML))
    assert not any(e.headword == "empty" for e in entries)


def test_sense_with_no_pos_uses_none(tmp_path):
    """A sense without a pos key should have pos=None."""
    yaml_content = """\
- head: word
  senses:
    - en: [[example]]
      ml: [[ഉദാഹരണം]]
"""
    entries = ekkurup.parse(_write(tmp_path, yaml_content))
    assert entries[0].senses[0].pos is None


def test_embed_text_no_pos_uses_general_tag(tmp_path):
    """A sense with pos=None should appear under [general] in embed_text."""
    yaml_content = """\
- head: word
  senses:
    - en: [[example]]
      ml: [[ഉദാഹരണം]]
"""
    entries = ekkurup.parse(_write(tmp_path, yaml_content))
    text = entries[0].to_embed_text()
    assert "[general]" in text


def test_ekkurup_sense_is_dataclass():
    """EkkurupSense should store pos, en, and ml fields as-is."""
    sense = EkkurupSense(pos="verb", en=[["run"]], ml=[["ഓടുക"]])
    assert sense.pos == "verb"
    assert sense.en == [["run"]]
    assert sense.ml == [["ഓടുക"]]

"""Tests for the Sayahna Shabdataaravali ML→ML parser (XDXF XML format)."""

from pathlib import Path

from linguaalayam.corpus import sayahna
from linguaalayam.models.entries import SayahnaEntry


def _write_xml(tmp_path: Path, filename: str, articles: str) -> Path:
    """Write a minimal XDXF XML file with the given <ar> blocks."""
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<xdxf lang_from="MAL" lang_to="MAL" format="logical">\n'
        "  <meta_info><title>test</title></meta_info>\n"
        f"  <lexicon>{articles}</lexicon>\n"
        "</xdxf>"
    )
    p = tmp_path / filename
    p.write_text(xml, encoding="utf-8")
    return tmp_path


_ARTICLE_BASIC = """
<ar>
  <k>അംശം</k>
  <def>
    <def><deftext>ഒരു പംക്</deftext></def>
    <def><deftext>ഓഹരി</deftext></def>
    <def><deftext>ഭാഗം</deftext></def>
  </def>
</ar>
"""

_ARTICLE_WITH_POS = """
<ar>
  <k>അംശജ</k>
  <def>
    <gr>adj.</gr>
    <def><deftext>അംശം കൊണ്ടു ജനിച്ച</deftext></def>
  </def>
</ar>
"""

_ARTICLE_WITH_EXPL = """
<ar>
  <k>അഋണി</k>
  <def>
    <def><deftext>കടമില്ലാത്തവൻ</deftext></def>
    <def><expl>സ്ത്രീ: അനൃണിനി.</expl></def>
  </def>
</ar>
"""

_ARTICLE_NO_DEFTEXT = """
<ar>
  <k>ശൂന്യം</k>
  <def>
    <def><expl>only an explanation, no definition</expl></def>
  </def>
</ar>
"""


def test_parse_basic_entry(tmp_path):
    """Parser extracts headword and multiple definitions."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_BASIC)
    entries = sayahna.parse(tmp_path)
    assert len(entries) == 1
    entry = entries[0]
    assert entry.headword == "അംശം"
    assert len(entry.definitions) == 3
    assert entry.definitions[0] == (None, "ഒരു പംക്")


def test_parse_with_pos(tmp_path):
    """POS from <gr> tag is captured in definitions."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_WITH_POS)
    entries = sayahna.parse(tmp_path)
    entry = entries[0]
    assert entry.definitions[0] == ("adj.", "അംശം കൊണ്ടു ജനിച്ച")


def test_parse_with_explanation(tmp_path):
    """Explanations from <expl> are stored separately."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_WITH_EXPL)
    entries = sayahna.parse(tmp_path)
    entry = entries[0]
    assert len(entry.definitions) == 1
    assert len(entry.explanations) == 1
    assert "അനൃണിനി" in entry.explanations[0]


def test_skip_entry_without_deftext(tmp_path):
    """Entries with only <expl> and no <deftext> are skipped."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_NO_DEFTEXT)
    entries = sayahna.parse(tmp_path)
    assert len(entries) == 0


def test_source_default(tmp_path):
    """All entries should carry source='sayahna'."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_BASIC)
    entries = sayahna.parse(tmp_path)
    assert all(e.source == "sayahna" for e in entries)


def test_returns_correct_type(tmp_path):
    """Parser should return SayahnaEntry instances."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_BASIC)
    entries = sayahna.parse(tmp_path)
    assert all(isinstance(e, SayahnaEntry) for e in entries)


def test_multiple_files_combined(tmp_path):
    """Parser reads all XML files in the directory, sorted by name."""
    _write_xml(tmp_path, "01.xml", _ARTICLE_BASIC)
    _write_xml(tmp_path, "02.xml", _ARTICLE_WITH_POS)
    entries = sayahna.parse(tmp_path)
    headwords = [e.headword for e in entries]
    assert "അംശം" in headwords
    assert "അംശജ" in headwords


def test_embed_text_contains_headword(tmp_path):
    """embed_text should start with 'word: <headword>'."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_BASIC)
    entries = sayahna.parse(tmp_path)
    text = entries[0].to_embed_text()
    assert "word: അംശം" in text


def test_embed_text_contains_definitions(tmp_path):
    """embed_text should include definition text."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_BASIC)
    entries = sayahna.parse(tmp_path)
    text = entries[0].to_embed_text()
    assert "ഓഹരി" in text
    assert "ഭാഗം" in text


def test_embed_text_contains_pos(tmp_path):
    """embed_text should include POS tags when present."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_WITH_POS)
    entries = sayahna.parse(tmp_path)
    text = entries[0].to_embed_text()
    assert "[adj.]" in text


def test_embed_text_contains_notes(tmp_path):
    """embed_text should include explanations as notes."""
    _write_xml(tmp_path, "test.xml", _ARTICLE_WITH_EXPL)
    entries = sayahna.parse(tmp_path)
    text = entries[0].to_embed_text()
    assert "notes:" in text
    assert "അനൃണിനി" in text


def test_embeddable_protocol(tmp_path):
    """SayahnaEntry should satisfy the Embeddable protocol."""
    from linguaalayam.models.entries import Embeddable

    _write_xml(tmp_path, "test.xml", _ARTICLE_BASIC)
    entries = sayahna.parse(tmp_path)
    assert isinstance(entries[0], Embeddable)

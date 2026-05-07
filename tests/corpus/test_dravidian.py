from pathlib import Path

from linguaalayam.corpus import dravidian
from linguaalayam.models.entries import CrossLingualEntry

_DRAVIDIAN = (
    "Malayalam\tKannada\tTamil\tTelugu\n"
    "അംഗം (1) - ഉടല്‍, ശരീരം\tഅംഗ - ദേഹ\tഅങ്കം - ഉടല്‍\tഅംഗം - ശരീരം\n"
    "അംഗം (2) - അവയവം\tഅംഗ - അവയവ\tഅങ്കം - ഉടലുറുപ്പു\tഅംഗം - അവയവം\n"
    "അംഗന - സ്ത്രീ, സുന്ദരി\tഅംഗനെ - ഹെംഗസു\tഅങ്കനൈ - പെണ്‍\tഅംഗന - സ്ത്രീ\n"
)

_PLAIN = "Malayalam\tKannada\tTamil\tTelugu\n" "word\tkanword\ttaword\tte word\n"


def _write(tmp_path: Path, content: str) -> Path:
    p = tmp_path / "dravidian.tsv"
    p.write_text(content, encoding="utf-8")
    return p


def test_sense_index_extracted(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _DRAVIDIAN))
    angam = sorted([e for e in entries if e.headword == "അംഗം"], key=lambda e: e.sense_index)
    assert angam[0].sense_index == 1
    assert angam[1].sense_index == 2


def test_no_sense_index_for_plain_entry(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _DRAVIDIAN))
    angana = next(e for e in entries if e.headword == "അംഗന")
    assert angana.sense_index is None


def test_ml_gloss_extracted(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _DRAVIDIAN))
    angam_1 = next(e for e in entries if e.headword == "അംഗം" and e.sense_index == 1)
    assert angam_1.ml_gloss  # non-empty
    assert any("ഉടല്‍" in g or "ശരീരം" in g for g in angam_1.ml_gloss)


def test_equivalents_present(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _DRAVIDIAN))
    angam_1 = next(e for e in entries if e.headword == "അംഗം" and e.sense_index == 1)
    assert {"kn", "ta", "te"} <= angam_1.equivalents.keys()


def test_source(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _DRAVIDIAN))
    assert all(e.source == "dravidian_comparative" for e in entries)


def test_returns_correct_type(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _DRAVIDIAN))
    assert all(isinstance(e, CrossLingualEntry) for e in entries)


def test_embed_text_has_language_tags(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _DRAVIDIAN))
    angam_1 = next(e for e in entries if e.headword == "അംഗം" and e.sense_index == 1)
    text = angam_1.to_embed_text()
    assert "[kn]" in text or "[ta]" in text or "[te]" in text


def test_skips_short_lines(tmp_path):
    content = "Malayalam\tKannada\n"
    entries = dravidian.parse(_write(tmp_path, content))
    assert entries == []


def test_plain_entry_without_gloss_separator(tmp_path):
    entries = dravidian.parse(_write(tmp_path, _PLAIN))
    assert len(entries) == 1
    assert entries[0].sense_index is None
    assert entries[0].ml_gloss == []


def test_entry_with_sense_but_no_gloss(tmp_path):
    content = "Malayalam\tKannada\tTamil\tTelugu\n" "word (1)\tkan\tta\tte\n"
    entries = dravidian.parse(_write(tmp_path, content))
    assert entries[0].sense_index == 1
    assert entries[0].ml_gloss == []

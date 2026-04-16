import textwrap
from pathlib import Path


from linguaalayam.corpus import enml
from linguaalayam.models.entries import EnMlEntry


def _write(tmp_path: Path, name: str, content: str) -> Path:
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
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    assert len(entries) == 2


def test_enml_merges_definitions(tmp_path):
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    a = next(e for e in entries if e.headword == "A")
    assert len(a.definitions) == 2


def test_enml_normalises_empty_pos_to_none(tmp_path):
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    a = next(e for e in entries if e.headword == "A")
    assert any(pos is None for pos, _ in a.definitions)


def test_enml_source(tmp_path):
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    assert all(e.source == "olam_enml" for e in entries)


def test_enml_returns_correct_type(tmp_path):
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    assert all(isinstance(e, EnMlEntry) for e in entries)


def test_enml_embed_text_contains_headword_and_definitions(tmp_path):
    entries = enml.parse(_write(tmp_path, "enml", ENML))
    roses = next(e for e in entries if e.headword == "A bed of roses")
    text = roses.to_embed_text()
    assert "A bed of roses" in text
    assert "പൂമെത്ത" in text
    assert "സുഖകരമായ അവസ്ഥ" in text


def test_enml_skips_malformed_lines(tmp_path):
    entries = enml.parse(_write(tmp_path, "enml", ENML + "bad line\n"))
    assert len(entries) == 2


# # ---------------------------------------------------------------------------
# # Datuk
# # ---------------------------------------------------------------------------

# DATUK = """\
# ഓടുക\t{v}\tനടക്കുകയേക്കാൾ വേഗത്തിൽ ചലിക്കുക
# ഓടുക\t{v}\tപായുക
# ആകാശം\t{n}\tഭൂമിക്കു മുകളിലുള്ള വിശാലമായ ഇടം
# """


# def test_datuk_groups_by_headword(tmp_path):
#     entries = datuk.parse(_write(tmp_path, "datuk", DATUK))
#     assert len(entries) == 2


# def test_datuk_source(tmp_path):
#     entries = datuk.parse(_write(tmp_path, "datuk", DATUK))
#     assert all(e.source == "datuk" for e in entries)


# def test_datuk_returns_correct_type(tmp_path):
#     entries = datuk.parse(_write(tmp_path, "datuk", DATUK))
#     assert all(isinstance(e, MlMlEntry) for e in entries)


# # ---------------------------------------------------------------------------
# # Dravidian
# # ---------------------------------------------------------------------------

# DRAVIDIAN = """\
# Malayalam\tKannada\tTamil\tTelugu
# അംഗം (1) - ഉടല്‍, ശരീരം\tഅംഗ - ദേഹ\tഅങ്കം - ഉടല്‍\tഅംഗം - ശരീരം
# അംഗം (2) - അവയവം\tഅംഗ - അവയവ\tഅങ്കം - ഉടലുറുപ്പു\tഅംഗം - അവയവം
# അംഗന - സ്ത്രീ, സുന്ദരി\tഅംഗനെ - ഹെംഗസു\tഅങ്കനൈ - പെണ്‍\tഅംഗന - സ്ത്രീ
# """


# def test_dravidian_sense_index(tmp_path):
#     entries = dravidian.parse(_write(tmp_path, "dravidian.tsv", DRAVIDIAN))
#     angam = [e for e in entries if e.headword == "അംഗം"]
#     assert len(angam) == 2
#     assert angam[0].sense_index == 1
#     assert angam[1].sense_index == 2


# def test_dravidian_no_sense_index_for_plain_entry(tmp_path):
#     entries = dravidian.parse(_write(tmp_path, "dravidian.tsv", DRAVIDIAN))
#     angana = next(e for e in entries if e.headword == "അംഗന")
#     assert angana.sense_index is None


# def test_dravidian_ml_gloss_parsed(tmp_path):
#     entries = dravidian.parse(_write(tmp_path, "dravidian.tsv", DRAVIDIAN))
#     angam_1 = next(e for e in entries if e.headword == "അംഗം" and e.sense_index == 1)
#     assert "ഉടല്‍" in angam_1.ml_gloss
#     assert "ശരീരം" in angam_1.ml_gloss


# def test_dravidian_equivalents_present(tmp_path):
#     entries = dravidian.parse(_write(tmp_path, "dravidian.tsv", DRAVIDIAN))
#     angam_1 = next(e for e in entries if e.headword == "അംഗം" and e.sense_index == 1)
#     assert {"kn", "ta", "te"} <= angam_1.equivalents.keys()


# def test_dravidian_source(tmp_path):
#     entries = dravidian.parse(_write(tmp_path, "dravidian.tsv", DRAVIDIAN))
#     assert all(e.source == "dravidian_comparative" for e in entries)


# def test_dravidian_returns_correct_type(tmp_path):
#     entries = dravidian.parse(_write(tmp_path, "dravidian.tsv", DRAVIDIAN))
#     assert all(isinstance(e, CrossLingualEntry) for e in entries)


# def test_dravidian_embed_text_has_all_language_tags(tmp_path):
#     entries = dravidian.parse(_write(tmp_path, "dravidian.tsv", DRAVIDIAN))
#     angam_1 = next(e for e in entries if e.headword == "അംഗം" and e.sense_index == 1)
#     text = angam_1.to_embed_text()
#     assert "[kn]" in text
#     assert "[ta]" in text
#     assert "[te]" in text

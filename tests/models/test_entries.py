from linguaalayam.models.entries import CrossLingualEntry, EnMlEntry, MlMlEntry


class TestEnMlEntry:
    def test_headword(self):
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert e.headword == "run"

    def test_default_source(self):
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert e.source == "olam_enml"

    def test_embed_text_contains_headword(self):
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert "run" in e.to_embed_text()

    def test_embed_text_contains_definition(self):
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert "ഓടുക" in e.to_embed_text()

    def test_embed_text_groups_by_pos(self):
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക"), ("v", "പായുക"), ("n", "ഓട്ടം")])
        text = e.to_embed_text()
        # Both verb definitions should appear under [v]
        assert "[v]" in text
        assert "[n]" in text

    def test_embed_text_none_pos_shown_as_general(self):
        e = EnMlEntry(headword="A", definitions=[(None, "ഒരു")])
        assert "[general]" in e.to_embed_text()

    def test_embed_text_returns_string(self):
        e = EnMlEntry(headword="run", definitions=[])
        assert isinstance(e.to_embed_text(), str)


class TestMlMlEntry:
    def test_default_source(self):
        e = MlMlEntry(headword="ഓടുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert e.source == "datuk"

    def test_embed_text_contains_headword(self):
        e = MlMlEntry(headword="ഓടുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert "ഓടുക" in e.to_embed_text()


class TestCrossLingualEntry:
    def test_default_source(self):
        e = CrossLingualEntry(
            headword="അംഗം", sense_index=1,
            ml_gloss=["ശരീരം"],
            equivalents={"kn": ("അംഗ", ["ദേഹ"])},
        )
        assert e.source == "dravidian_comparative"

    def test_embed_text_includes_sense(self):
        e = CrossLingualEntry(
            headword="അംഗം", sense_index=2,
            ml_gloss=["അവയവം"],
            equivalents={},
        )
        assert "sense 2" in e.to_embed_text()

    def test_embed_text_no_sense_when_none(self):
        e = CrossLingualEntry(
            headword="അംഗന", sense_index=None,
            ml_gloss=["സ്ത്രീ"],
            equivalents={},
        )
        assert "sense" not in e.to_embed_text()

    def test_embed_text_includes_equivalents(self):
        e = CrossLingualEntry(
            headword="അംഗം", sense_index=1,
            ml_gloss=["ശരീരം"],
            equivalents={"kn": ("അംഗ", ["ദേഹ"]), "ta": ("അங്கം", ["ഉടല്‍"])},
        )
        text = e.to_embed_text()
        assert "[kn]" in text
        assert "[ta]" in text

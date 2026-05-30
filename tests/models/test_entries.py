"""Tests for EnMlEntry and MlMlEntry dataclasses."""

from linguaalayam.models.entries import EnMlEntry, MlMlEntry


class TestEnMlEntry:
    """EnMlEntry construction and embed_text generation."""

    def test_headword(self):
        """headword field should be stored as-is."""
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert e.headword == "run"

    def test_default_source(self):
        """Default source should be 'olam_enml'."""
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert e.source == "olam_enml"

    def test_embed_text_contains_headword(self):
        """embed_text should include the headword string."""
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert "run" in e.to_embed_text()

    def test_embed_text_contains_definition(self):
        """embed_text should include the Malayalam definition."""
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])
        assert "ഓടുക" in e.to_embed_text()

    def test_embed_text_groups_by_pos(self):
        """Multiple definitions should be grouped under their POS tag."""
        e = EnMlEntry(headword="run", definitions=[("v", "ഓടുക"), ("v", "പായുക"), ("n", "ഓട്ടം")])
        text = e.to_embed_text()
        # Both verb definitions should appear under [v]
        assert "[v]" in text
        assert "[n]" in text

    def test_embed_text_none_pos_shown_as_general(self):
        """A None POS should render as [general] in embed_text."""
        e = EnMlEntry(headword="A", definitions=[(None, "ഒരു")])
        assert "[general]" in e.to_embed_text()

    def test_embed_text_returns_string(self):
        """to_embed_text should always return a str."""
        e = EnMlEntry(headword="run", definitions=[])
        assert isinstance(e.to_embed_text(), str)


class TestMlMlEntry:
    """MlMlEntry construction and embed_text."""

    def test_default_source(self):
        """Default source should be 'datuk'."""
        e = MlMlEntry(headword="ഓടുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert e.source == "datuk"

    def test_embed_text_contains_headword(self):
        """embed_text should include the Malayalam headword."""
        e = MlMlEntry(headword="ഓടുക", definitions=[("v", "വേഗത്തിൽ ചലിക്കുക")])
        assert "ഓടുക" in e.to_embed_text()

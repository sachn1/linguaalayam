"""Unit tests for linguaalayam.eval.prepare_eval_queries's pure (non-DB) functions."""

import json

from linguaalayam.eval.prepare_eval_queries import _load_hand_curated, gen_ml_from_inflected


class TestLoadHandCurated:
    """_load_hand_curated's file-merge behaviour."""

    def test_missing_file_returns_empty_list(self, tmp_path):
        assert _load_hand_curated(tmp_path / "does_not_exist.jsonl") == []

    def test_loads_records_from_a_real_file(self, tmp_path):
        path = tmp_path / "hand_curated.jsonl"
        records = [
            {"query": "a", "expected_headword": "b", "intent": "x_true_negative", "source": None},
            {
                "query": "c",
                "expected_headword": "d",
                "intent": "x_semantic_no_overlap",
                "source": "s",
            },
        ]
        path.write_text("\n".join(json.dumps(r) for r in records) + "\n", encoding="utf-8")
        assert _load_hand_curated(path) == records

    def test_skips_blank_lines(self, tmp_path):
        path = tmp_path / "hand_curated.jsonl"
        line = '{"query": "a", "expected_headword": "b", "intent": "x", "source": null}'
        path.write_text(f"{line}\n\n")
        assert len(_load_hand_curated(path)) == 1


class TestGenMlFromInflected:
    """gen_ml_from_inflected's real-verb filtering and <past>-only generation."""

    def test_generates_a_real_inflected_form_for_a_known_verb(self):
        entries = [{"headword": "ഓടുക", "embed_text": ""}]
        records = gen_ml_from_inflected(entries, n=5)
        assert records == [
            {
                "query": "ഓടി",
                "expected_headword": "ഓടുക",
                "intent": "ml_from_inflected",
                "source": None,
            }
        ]

    def test_skips_non_verb_headwords(self):
        entries = [{"headword": "സന്തോഷം", "embed_text": ""}]
        assert gen_ml_from_inflected(entries, n=5) == []

    def test_stops_at_n(self):
        entries = [{"headword": w, "embed_text": ""} for w in ["ഓടുക", "എഴുതുക", "ഇരിക്കുക"]]
        records = gen_ml_from_inflected(entries, n=1)
        assert len(records) == 1

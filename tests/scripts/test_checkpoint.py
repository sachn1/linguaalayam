"""Tests for VectorCheckpoint — append, load, remove, and delete operations."""

import pytest

from linguaalayam.scripts import VectorCheckpoint


@pytest.fixture()
def checkpoint(tmp_path):
    """VectorCheckpoint backed by a temp directory."""
    return VectorCheckpoint(tmp_path / "test.jsonl")


def test_load_returns_empty_when_no_file(checkpoint):
    """load should return {} when the checkpoint file does not exist."""
    assert checkpoint.load() == {}


def test_exists_false_when_no_file(checkpoint):
    """exists should return False before any data is appended."""
    assert not checkpoint.exists()


def test_append_and_load(checkpoint):
    """Appended vectors should be retrievable via load."""
    checkpoint.append_batch(["run", "walk"], [[1.0, 0.0], [0.0, 1.0]])
    loaded = checkpoint.load()
    assert loaded["run"] == [1.0, 0.0]
    assert loaded["walk"] == [0.0, 1.0]


def test_exists_true_after_append(checkpoint):
    """exists should return True after at least one batch is appended."""
    checkpoint.append_batch(["run"], [[1.0, 0.0]])
    assert checkpoint.exists()


def test_append_is_cumulative(checkpoint):
    """Multiple append_batch calls should accumulate entries."""
    checkpoint.append_batch(["run"], [[1.0, 0.0]])
    checkpoint.append_batch(["walk"], [[0.0, 1.0]])
    assert len(checkpoint.load()) == 2


def test_remove_inserted_keeps_remainder(checkpoint):
    """remove_inserted should delete only the specified headwords."""
    checkpoint.append_batch(["run", "walk", "fly"], [[1.0], [2.0], [3.0]])
    checkpoint.remove_inserted({"run", "walk"})
    loaded = checkpoint.load()
    assert "run" not in loaded
    assert "walk" not in loaded
    assert loaded["fly"] == [3.0]


def test_remove_inserted_deletes_file_when_empty(checkpoint):
    """Removing all entries should delete the checkpoint file."""
    checkpoint.append_batch(["run"], [[1.0]])
    checkpoint.remove_inserted({"run"})
    assert not checkpoint.exists()


def test_delete(checkpoint):
    """delete should remove the checkpoint file."""
    checkpoint.append_batch(["run"], [[1.0]])
    checkpoint.delete()
    assert not checkpoint.exists()


def test_load_skips_malformed_lines(tmp_path):
    """load should silently skip lines that are not valid JSON."""
    path = tmp_path / "bad.jsonl"
    path.write_text('{"headword": "run", "vector": [1.0]}\nbad json\n', encoding="utf-8")
    loaded = VectorCheckpoint(path).load()
    assert "run" in loaded
    assert len(loaded) == 1


def test_load_skips_blank_lines(tmp_path):
    """load should ignore blank lines in the checkpoint file."""
    path = tmp_path / "blanks.jsonl"
    path.write_text('{"headword": "run", "vector": [1.0]}\n\n', encoding="utf-8")
    loaded = VectorCheckpoint(path).load()
    assert "run" in loaded
    assert len(loaded) == 1


def test_remove_inserted_skips_malformed_lines(tmp_path):
    """remove_inserted should skip malformed lines without raising."""
    path = tmp_path / "mixed.jsonl"
    path.write_text(
        '{"headword": "run", "vector": [1.0]}\n'
        "bad json line\n"
        '{"headword": "walk", "vector": [2.0]}\n',
        encoding="utf-8",
    )
    cp = VectorCheckpoint(path)
    cp.remove_inserted({"run"})
    loaded = cp.load()
    assert "walk" in loaded
    assert "run" not in loaded


def test_remove_inserted_skips_blank_lines(tmp_path):
    """remove_inserted should handle blank lines in the checkpoint file."""
    path = tmp_path / "blanks.jsonl"
    path.write_text(
        '{"headword": "run", "vector": [1.0]}\n\n{"headword": "walk", "vector": [2.0]}\n',
        encoding="utf-8",
    )
    cp = VectorCheckpoint(path)
    cp.remove_inserted({"run"})
    assert cp.load() == {"walk": [2.0]}

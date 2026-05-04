from unittest.mock import MagicMock, patch


from linguaalayam.models.entries import EnMlEntry
from linguaalayam.scripts.ingest import (
    _get_pending,
    _embed_with_checkpoint,
    _insert_with_checkpoint,
)
from linguaalayam.scripts.vector_checkpoint import VectorCheckpoint


# ---------------------------------------------------------------------------
# _get_pending
# ---------------------------------------------------------------------------


def _make_entries(*headwords: str) -> list[EnMlEntry]:
    return [EnMlEntry(headword=hw, definitions=[("v", "test")]) for hw in headwords]


def test_get_pending_excludes_ingested():
    entries = _make_entries("run", "walk", "fly")
    pending = _get_pending("enml", entries, ingested_headwords={"run"}, limit=None)
    assert [e.headword for e in pending] == ["walk", "fly"]


def test_get_pending_returns_all_when_nothing_ingested():
    entries = _make_entries("run", "walk")
    pending = _get_pending("enml", entries, ingested_headwords=set(), limit=None)
    assert len(pending) == 2


def test_get_pending_applies_limit():
    entries = _make_entries("run", "walk", "fly", "jump")
    pending = _get_pending("enml", entries, ingested_headwords=set(), limit=2)
    assert len(pending) == 2


def test_get_pending_limit_applied_after_filter():
    entries = _make_entries("run", "walk", "fly", "jump")
    # "run" is already ingested, so 3 remain, limit=2 takes first 2
    pending = _get_pending("enml", entries, ingested_headwords={"run"}, limit=2)
    assert len(pending) == 2
    assert all(e.headword != "run" for e in pending)


def test_get_pending_returns_empty_when_all_ingested():
    entries = _make_entries("run", "walk")
    pending = _get_pending("enml", entries, ingested_headwords={"run", "walk"}, limit=None)
    assert pending == []


# ---------------------------------------------------------------------------
# _embed_with_checkpoint
# ---------------------------------------------------------------------------


def test_embed_with_checkpoint_skips_cached(tmp_path, dummy_service):
    checkpoint = VectorCheckpoint(tmp_path / "enml.jsonl")
    checkpoint.append_batch(["run"], [[1.0, 0.0, 0.0, 0.0]])

    entries = _make_entries("run", "walk")
    result = _embed_with_checkpoint("enml", entries, dummy_service, checkpoint)

    assert "run" in result
    assert "walk" in result


def test_embed_with_checkpoint_appends_new_vectors(tmp_path, dummy_service):
    checkpoint = VectorCheckpoint(tmp_path / "enml.jsonl")
    entries = _make_entries("run", "walk")

    _embed_with_checkpoint("enml", entries, dummy_service, checkpoint)

    loaded = checkpoint.load()
    assert "run" in loaded
    assert "walk" in loaded


def test_embed_with_checkpoint_returns_full_set(tmp_path, dummy_service):
    checkpoint = VectorCheckpoint(tmp_path / "enml.jsonl")
    checkpoint.append_batch(["run"], [[9.0, 0.0, 0.0, 0.0]])

    entries = _make_entries("run", "walk")
    result = _embed_with_checkpoint("enml", entries, dummy_service, checkpoint)

    # cached vector for "run" should be preserved
    assert result["run"] == [9.0, 0.0, 0.0, 0.0]
    assert "walk" in result


# ---------------------------------------------------------------------------
# _insert_with_checkpoint
# ---------------------------------------------------------------------------


def test_insert_clears_checkpoint_entries(tmp_path):
    checkpoint = VectorCheckpoint(tmp_path / "enml.jsonl")
    entries = _make_entries("run", "walk")
    vectors = {"run": [1.0, 0.0, 0.0, 0.0], "walk": [0.0, 1.0, 0.0, 0.0]}
    checkpoint.append_batch(["run", "walk"], [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0]])

    session = MagicMock()
    session_ctx = MagicMock()
    session_ctx.__enter__ = MagicMock(return_value=session)
    session_ctx.__exit__ = MagicMock(return_value=False)
    factory = MagicMock(return_value=session_ctx)

    with (
        patch("linguaalayam.scripts.ingest.get_session", return_value=session_ctx),
        patch("linguaalayam.scripts.ingest.batch_insert"),
    ):
        _insert_with_checkpoint("enml", entries, vectors, factory, checkpoint, db_batch_size=10)

    assert not checkpoint.exists()


def test_insert_calls_batch_insert(tmp_path):
    checkpoint = VectorCheckpoint(tmp_path / "enml.jsonl")
    entries = _make_entries("run", "walk")
    vectors = {"run": [1.0, 0.0, 0.0, 0.0], "walk": [0.0, 1.0, 0.0, 0.0]}

    session = MagicMock()
    session_ctx = MagicMock()
    session_ctx.__enter__ = MagicMock(return_value=session)
    session_ctx.__exit__ = MagicMock(return_value=False)

    with (
        patch("linguaalayam.scripts.ingest.get_session", return_value=session_ctx),
        patch("linguaalayam.scripts.ingest.batch_insert") as mock_insert,
    ):
        _insert_with_checkpoint("enml", entries, vectors, MagicMock(), checkpoint, db_batch_size=10)

    assert mock_insert.called

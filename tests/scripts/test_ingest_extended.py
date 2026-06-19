"""Tests for _batched, _ingest_corpus, and _process_source in ingest.py."""

from unittest.mock import MagicMock, patch


from linguaalayam.models.entries import OlamEntry
from linguaalayam.scripts.ingest import _batched, _ingest_corpus, _process_source
from linguaalayam.scripts.vector_checkpoint import VectorCheckpoint


def _entries(*headwords: str) -> list[OlamEntry]:
    """Build a list of stub OlamEntry objects from headwords."""
    return [OlamEntry(headword=hw, definitions=[("v", "test")]) for hw in headwords]


def _mock_session_ctx():
    """Build a mock context manager that yields a mock session."""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=MagicMock())
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


class TestBatched:
    """_batched batch slicing correctness."""

    def test_basic_batching(self):
        """Should split a list into batches of the given size."""
        result = list(_batched([1, 2, 3, 4, 5], 2))
        assert result == [[1, 2], [3, 4], [5]]

    def test_exact_multiple(self):
        """Even-divisible list should produce full batches only."""
        result = list(_batched([1, 2, 3, 4], 2))
        assert result == [[1, 2], [3, 4]]

    def test_empty_input(self):
        """Empty input should produce no batches."""
        assert list(_batched([], 2)) == []

    def test_batch_larger_than_list(self):
        """Batch size larger than list length should produce a single batch."""
        result = list(_batched([1, 2], 10))
        assert result == [[1, 2]]

    def test_batch_size_one(self):
        """Batch size of 1 should produce one batch per element."""
        result = list(_batched([1, 2, 3], 1))
        assert result == [[1], [2], [3]]


class TestIngestCorpus:
    """_ingest_corpus end-to-end embed + insert with checkpoint."""

    def test_calls_embed_and_insert(self, tmp_path, dummy_service):
        """Should complete without error for valid entries."""
        entries = _entries("run", "walk")
        checkpoint = VectorCheckpoint(tmp_path / "test.jsonl")
        mock_factory = MagicMock()
        session_ctx = _mock_session_ctx()

        with (
            patch("linguaalayam.scripts.ingest.get_session", return_value=session_ctx),
            patch("linguaalayam.scripts.ingest.batch_insert"),
        ):
            _ingest_corpus(
                "enml", entries, dummy_service, mock_factory, checkpoint, db_batch_size=10
            )

    def test_checkpoint_cleaned_up(self, tmp_path, dummy_service):
        """Checkpoint file should be deleted after successful ingestion."""
        entries = _entries("run")
        checkpoint = VectorCheckpoint(tmp_path / "test.jsonl")
        session_ctx = _mock_session_ctx()

        with (
            patch("linguaalayam.scripts.ingest.get_session", return_value=session_ctx),
            patch("linguaalayam.scripts.ingest.batch_insert"),
        ):
            _ingest_corpus(
                "enml", entries, dummy_service, MagicMock(), checkpoint, db_batch_size=10
            )

        assert not checkpoint.exists()


class TestProcessSource:
    """_process_source full source pipeline with early-exit conditions."""

    def _source_cfg(self, path: str, source_name: str = "olam_enml") -> MagicMock:
        """Build a mock source config with path and source_name attributes."""
        cfg = MagicMock()
        cfg.path = path
        cfg.source_name = source_name
        return cfg

    def test_skips_missing_file(self, tmp_path, dummy_service, caplog):
        """Should log and return early when the corpus file does not exist."""
        cfg = self._source_cfg("missing.tsv")
        _process_source("enml", cfg, dummy_service, MagicMock(), tmp_path, tmp_path, 10, None)
        # no exception — just logged

    def test_skips_empty_corpus(self, tmp_path, dummy_service):
        """Should not call _ingest_corpus when the parser returns no entries."""
        (tmp_path / "empty.tsv").touch()
        cfg = self._source_cfg("empty.tsv")

        with (
            patch("linguaalayam.scripts.ingest.instantiate", return_value=lambda p: []),
            patch("linguaalayam.scripts.ingest._ingest_corpus") as mock_ingest,
        ):
            _process_source("enml", cfg, dummy_service, MagicMock(), tmp_path, tmp_path, 10, None)

        mock_ingest.assert_not_called()

    def test_skips_when_all_ingested_and_no_checkpoint(self, tmp_path, dummy_service):
        """Should skip _ingest_corpus when all headwords are already in the DB."""
        (tmp_path / "test.tsv").touch()
        cfg = self._source_cfg("test.tsv")
        entries = _entries("run")
        session_ctx = _mock_session_ctx()

        with (
            patch("linguaalayam.scripts.ingest.instantiate", return_value=lambda p: entries),
            patch("linguaalayam.scripts.ingest.get_session", return_value=session_ctx),
            patch("linguaalayam.scripts.ingest.get_ingested_headwords", return_value={"run"}),
            patch("linguaalayam.scripts.ingest._ingest_corpus") as mock_ingest,
        ):
            _process_source("enml", cfg, dummy_service, MagicMock(), tmp_path, tmp_path, 10, None)

        mock_ingest.assert_not_called()

    def test_runs_ingest_for_pending_entries(self, tmp_path, dummy_service):
        """Should call _ingest_corpus when pending entries exist."""
        (tmp_path / "test.tsv").touch()
        cfg = self._source_cfg("test.tsv")
        entries = _entries("run", "walk")
        session_ctx = _mock_session_ctx()

        with (
            patch("linguaalayam.scripts.ingest.instantiate", return_value=lambda p: entries),
            patch("linguaalayam.scripts.ingest.get_session", return_value=session_ctx),
            patch("linguaalayam.scripts.ingest.get_ingested_headwords", return_value=set()),
            patch("linguaalayam.scripts.ingest._ingest_corpus") as mock_ingest,
        ):
            _process_source("enml", cfg, dummy_service, MagicMock(), tmp_path, tmp_path, 10, None)

        mock_ingest.assert_called_once()

    def test_runs_ingest_when_checkpoint_has_data(self, tmp_path, dummy_service):
        """Should resume ingestion when checkpoint contains un-inserted vectors."""
        (tmp_path / "test.tsv").touch()
        cfg = self._source_cfg("test.tsv")
        entries = _entries("run")
        session_ctx = _mock_session_ctx()

        # Pre-populate checkpoint so checkpointed_headwords is non-empty
        checkpoint = VectorCheckpoint(tmp_path / "enml.jsonl")
        checkpoint.append_batch(["run"], [[0.1, 0.0, 0.0, 0.0]])

        with (
            patch("linguaalayam.scripts.ingest.instantiate", return_value=lambda p: entries),
            patch("linguaalayam.scripts.ingest.get_session", return_value=session_ctx),
            patch("linguaalayam.scripts.ingest.get_ingested_headwords", return_value={"run"}),
            patch("linguaalayam.scripts.ingest._ingest_corpus") as mock_ingest,
        ):
            _process_source("enml", cfg, dummy_service, MagicMock(), tmp_path, tmp_path, 10, None)

        mock_ingest.assert_called_once()

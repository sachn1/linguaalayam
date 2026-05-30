"""Module for managing a checkpoint file that tracks embedding progress."""

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


class VectorCheckpoint:
    """Manages a checkpoint file for embedding progress.

    Vector checkpoint — persists (headword, embed_text, vector) to disk as
    embeddings are produced, so work is not lost on failure.

    Lifecycle:
    1. On embed: append each batch to the checkpoint file immediately
    2. On successful DB insert: remove those headwords from the checkpoint
    3. On completion: delete the checkpoint file entirely

    Format: newline-delimited JSON (one record per line) for streaming
    append/read without loading the whole file into memory.
    """

    def __init__(self, path: Path) -> None:
        self._path = path

    def exists(self) -> bool:
        """Check if the checkpoint file exists.

        Returns
        -------
        bool
            True if the checkpoint file exists, False otherwise.
        """
        return self._path.exists()

    def load(self) -> dict[str, list[float]]:
        """Load checkpoint as {headword: vector}.

        Returns
        -------
        dict[str, list[float]]
            Dictionary mapping headwords to their embedding vectors.
        """
        if not self._path.exists():
            return {}

        records: dict[str, list[float]] = {}
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    records[record["headword"]] = record["vector"]
                except (json.JSONDecodeError, KeyError):
                    log.warning("Skipping malformed checkpoint line: %s", line[:80])
        return records

    def append_batch(self, headwords: list[str], vectors: list[list[float]]) -> None:
        """Append a batch of headword→vector pairs to the checkpoint file.

        Parameters
        ----------
        headwords : list[str]
            List of headwords corresponding to the vectors.
        vectors : list[list[float]]
            List of embedding vectors corresponding to the headwords.
        """
        with self._path.open("a", encoding="utf-8") as f:
            for headword, vector in zip(headwords, vectors):
                f.write(json.dumps({"headword": headword, "vector": vector}) + "\n")

    def remove_inserted(self, headwords: set[str]) -> None:
        """Remove successfully inserted headwords from the checkpoint file.

        Parameters
        ----------
        headwords : set[str]
            Set of headwords that have been successfully inserted into the database.
        """
        if not self._path.exists():
            return

        remaining = []
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                    if record["headword"] not in headwords:
                        remaining.append(line)
                except (json.JSONDecodeError, KeyError):
                    continue

        if remaining:
            with self._path.open("w", encoding="utf-8") as f:
                f.write("\n".join(remaining) + "\n")
        else:
            self.delete()

    def delete(self) -> None:
        """Delete the checkpoint file."""
        if self._path.exists():
            self._path.unlink()
            log.info("Checkpoint deleted: %s", self._path)

"""Shared fixtures and test doubles for the LinguAalayam test suite."""

import numpy as np
import pytest
from omegaconf import OmegaConf

from linguaalayam.embeddings import service as embedding_service
from linguaalayam.embeddings.service import EmbeddingService
from linguaalayam.models.entries import OlamEntry


class DummyModel:
    """Minimal SentenceTransformer stand-in that returns deterministic numpy arrays."""

    DIM = 4

    def get_sentence_embedding_dimension(self) -> int:
        """Return the fixed embedding dimension."""
        return self.DIM

    def encode(self, texts, batch_size=1, show_progress_bar=False, normalize_embeddings=False):
        """Return a constant 4-d vector for each text."""
        if isinstance(texts, list):
            return np.array([[1.0, 0.0, 0.0, 0.0] for _ in texts])
        return np.array([1.0, 0.0, 0.0, 0.0])


@pytest.fixture()
def embedding_cfg():
    """OmegaConf embedding config wired to the DummyModel."""
    return OmegaConf.create(
        {
            "model": "dummy",
            "batch_size": 2,
            "normalize": False,
        }
    )


@pytest.fixture()
def dummy_service(monkeypatch, embedding_cfg):
    """EmbeddingService backed by DummyModel — no real model loaded."""
    monkeypatch.setattr(embedding_service, "SentenceTransformer", lambda *a, **kw: DummyModel())
    return EmbeddingService(embedding_cfg)


@pytest.fixture()
def enml_entry():
    """A minimal OlamEntry for 'run' with two verb definitions."""
    return OlamEntry(
        headword="run",
        definitions=[("v", "ഓടുക"), ("v", "പായുക")],
    )


@pytest.fixture()
def db_cfg():
    """SQLite in-memory config — no Supabase needed for unit tests."""
    return OmegaConf.create(
        {
            "url": "sqlite:///:memory:",
            "pool_size": 1,
            "max_overflow": 0,
        }
    )

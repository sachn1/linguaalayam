"""Tests for EmbeddingService encode/encode_query, and LazyEmbeddingService."""

import threading
import time

from linguaalayam.embeddings.service import LazyEmbeddingService
from linguaalayam.models.entries import OlamEntry


class TestEmbeddingService:
    """EmbeddingService encode / encode_query correctness."""

    def test_vector_size(self, dummy_service):
        """vector_size should match DummyModel.DIM."""
        assert dummy_service.vector_size == 4

    def test_encode_returns_correct_count(self, dummy_service):
        """encode should return one vector per input entry."""
        entries = [
            OlamEntry(headword="run", definitions=[("v", "ഓടുക")]),
            OlamEntry(headword="walk", definitions=[("v", "നടക്കുക")]),
        ]
        assert len(dummy_service.encode(entries)) == 2

    def test_encode_returns_correct_dimension(self, dummy_service):
        """Each encoded vector should have the model's embedding dimension."""
        entries = [OlamEntry(headword="run", definitions=[("v", "ഓടുക")])]
        assert len(dummy_service.encode(entries)[0]) == 4

    def test_encode_returns_list_of_lists(self, dummy_service):
        """encode should return a list of float lists, not numpy arrays."""
        entries = [OlamEntry(headword="run", definitions=[("v", "ഓടുക")])]
        vectors = dummy_service.encode(entries)
        assert isinstance(vectors, list)
        assert isinstance(vectors[0], list)

    def test_encode_query_returns_correct_dimension(self, dummy_service):
        """encode_query should return a vector of the model's dimension."""
        assert len(dummy_service.encode_query("what does run mean?")) == 4

    def test_encode_query_returns_list(self, dummy_service):
        """encode_query should return a list, not a numpy array."""
        assert isinstance(dummy_service.encode_query("test"), list)

    def test_encode_empty_list(self, dummy_service):
        """encode on an empty list should return an empty list."""
        assert dummy_service.encode([]) == []


class TestLazyEmbeddingService:
    """LazyEmbeddingService blocks until set_ready(), then delegates to the real service."""

    def test_delegates_once_ready(self, dummy_service):
        """Every method should match the real service's output once ready."""
        lazy = LazyEmbeddingService()
        lazy.set_ready(dummy_service)
        assert lazy.vector_size == dummy_service.vector_size
        assert lazy.batch_size == dummy_service.batch_size
        assert lazy.encode_query("test") == dummy_service.encode_query("test")

    def test_blocks_until_ready(self, dummy_service):
        """A call made before set_ready() should block, then return the real
        result as soon as set_ready() is called from another thread — not
        raise, not return a stale/placeholder value."""
        lazy = LazyEmbeddingService()
        result = {}

        def caller():
            result["vector"] = lazy.encode_query("test")

        t = threading.Thread(target=caller)
        t.start()
        time.sleep(0.1)  # give the thread a chance to start blocking on wait()
        assert "vector" not in result  # still blocked — set_ready() not called yet

        lazy.set_ready(dummy_service)
        t.join(timeout=2)
        assert result["vector"] == dummy_service.encode_query("test")

    def test_multiple_waiters_all_unblock(self, dummy_service):
        """More than one blocked caller should all wake up once ready — the
        real scenario of several concurrent requests reaching semantic_lookup
        before the background load finishes."""
        lazy = LazyEmbeddingService()
        results = [None, None, None]

        def caller(i):
            results[i] = lazy.vector_size

        threads = [threading.Thread(target=caller, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        time.sleep(0.1)
        lazy.set_ready(dummy_service)
        for t in threads:
            t.join(timeout=2)
        assert results == [dummy_service.vector_size] * 3

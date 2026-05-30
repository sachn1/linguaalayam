"""Tests for EmbeddingService encode and encode_query methods."""

from linguaalayam.models.entries import EnMlEntry


class TestEmbeddingService:
    """EmbeddingService encode / encode_query correctness."""

    def test_vector_size(self, dummy_service):
        """vector_size should match DummyModel.DIM."""
        assert dummy_service.vector_size == 4

    def test_encode_returns_correct_count(self, dummy_service):
        """encode should return one vector per input entry."""
        entries = [
            EnMlEntry(headword="run", definitions=[("v", "ഓടുക")]),
            EnMlEntry(headword="walk", definitions=[("v", "നടക്കുക")]),
        ]
        assert len(dummy_service.encode(entries)) == 2

    def test_encode_returns_correct_dimension(self, dummy_service):
        """Each encoded vector should have the model's embedding dimension."""
        entries = [EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])]
        assert len(dummy_service.encode(entries)[0]) == 4

    def test_encode_returns_list_of_lists(self, dummy_service):
        """encode should return a list of float lists, not numpy arrays."""
        entries = [EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])]
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

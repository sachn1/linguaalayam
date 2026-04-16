from linguaalayam.models.entries import EnMlEntry


class TestEmbeddingService:
    def test_vector_size(self, dummy_service):
        assert dummy_service.vector_size == 4

    def test_encode_returns_correct_count(self, dummy_service):
        entries = [
            EnMlEntry(headword="run", definitions=[("v", "ഓടുക")]),
            EnMlEntry(headword="walk", definitions=[("v", "നടക്കുക")]),
        ]
        assert len(dummy_service.encode(entries)) == 2

    def test_encode_returns_correct_dimension(self, dummy_service):
        entries = [EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])]
        assert len(dummy_service.encode(entries)[0]) == 4

    def test_encode_returns_list_of_lists(self, dummy_service):
        entries = [EnMlEntry(headword="run", definitions=[("v", "ഓടുക")])]
        vectors = dummy_service.encode(entries)
        assert isinstance(vectors, list)
        assert isinstance(vectors[0], list)

    def test_encode_query_returns_correct_dimension(self, dummy_service):
        assert len(dummy_service.encode_query("what does run mean?")) == 4

    def test_encode_query_returns_list(self, dummy_service):
        assert isinstance(dummy_service.encode_query("test"), list)

    def test_encode_empty_list(self, dummy_service):
        assert dummy_service.encode([]) == []

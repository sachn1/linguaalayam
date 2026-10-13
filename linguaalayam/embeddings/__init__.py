"""Embeddings package — sentence-transformer encoding for dictionary entries."""

from .service import EmbeddingService, LazyEmbeddingService

__all__ = [
    "EmbeddingService",
    "LazyEmbeddingService",
]

"""Embedding service for dictionary entries."""

import numpy as np
from omegaconf import DictConfig
from sentence_transformers import SentenceTransformer

from linguaalayam.models.entries import Embeddable


class EmbeddingService:
    """Service class for generating embeddings for dictionary entries."""
    def __init__(self, embedding_cfg: DictConfig) -> None:
        """Initialize the embedding service.

        Parameters
        ----------
        embedding_cfg : DictConfig
            Configuration for the embedding model.
        """
        self._cfg = embedding_cfg
        self._model = SentenceTransformer(
            embedding_cfg.model,
            model_kwargs={"torch_dtype": "int8"} if embedding_cfg.get("quantise") else {},
        )

    @property
    def vector_size(self) -> int:
        """Get the dimensionality of the embedding vectors."""
        return self._model.get_sentence_embedding_dimension()

    def encode(self, entries: list[Embeddable]) -> list[list[float]]:
        """Encode a list of embeddable entries into their vector representations.

        Parameters
        ----------
        entries : list[Embeddable]
            List of entries to encode.

        Returns
        -------
        list[list[float]]
            List of embedding vectors corresponding to the input entries.
        """
        texts = [entry.to_embed_text() for entry in entries]
        vectors: np.ndarray = self._model.encode(
            texts,
            batch_size=self._cfg.batch_size,
            show_progress_bar=False,
            normalize_embeddings=self._cfg.normalize,
        )
        return vectors.tolist()

    def encode_query(self, query: str) -> list[float]:
        """Encode a query string into its vector representation.s

        Parameters
        ----------
        query : str
            The query string to encode.

        Returns
        -------
        list[float]
            The embedding vector corresponding to the query string.
        """
        vector: np.ndarray = self._model.encode(
            query,
            normalize_embeddings=self._cfg.normalize,
        )
        return vector.tolist()

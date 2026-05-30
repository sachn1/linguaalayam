"""Embedding service for dictionary entries."""

import numpy as np
from omegaconf import DictConfig
from sentence_transformers import SentenceTransformer

from linguaalayam.models.entries import Embeddable


class EmbeddingService:
    """Sentence-transformer wrapper that encodes dictionary entries into vectors.

    Parameters
    ----------
    embedding_cfg : DictConfig
        Configuration with the following keys:

        - ``model`` — HuggingFace model ID or local path.
        - ``batch_size`` — number of texts to encode per forward pass.
        - ``normalize`` — whether to L2-normalise the output vectors.
        - ``quantise`` — if ``True``, loads the model with ``int8`` weights.

    Attributes
    ----------
    vector_size : int
        Dimensionality of the embedding vectors produced by the model.
    """

    def __init__(self, embedding_cfg: DictConfig) -> None:
        self._cfg = embedding_cfg
        self._model = SentenceTransformer(
            embedding_cfg.model,
            model_kwargs={"torch_dtype": "int8"} if embedding_cfg.get("quantise") else {},
        )

    @property
    def vector_size(self) -> int:
        """Dimensionality of the embedding vectors produced by the model."""
        return self._model.get_sentence_embedding_dimension()

    @property
    def batch_size(self) -> int:
        """Number of texts encoded per forward pass."""
        return self._cfg.batch_size

    def encode(self, entries: list[Embeddable]) -> list[list[float]]:
        """Encode a list of embeddable entries into their vector representations.

        Parameters
        ----------
        entries : list[Embeddable]
            List of entries to encode. Each entry's ``to_embed_text()`` output
            is used as the input text.

        Returns
        -------
        list[list[float]]
            List of embedding vectors corresponding to the input entries,
            in the same order.
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
        """Encode a free-text query string into its vector representation.

        Parameters
        ----------
        query : str
            The query string to encode.

        Returns
        -------
        list[float]
            The embedding vector for the query.
        """
        vector: np.ndarray = self._model.encode(
            query,
            normalize_embeddings=self._cfg.normalize,
        )
        return vector.tolist()

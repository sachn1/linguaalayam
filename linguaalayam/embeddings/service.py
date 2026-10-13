"""Embedding service for dictionary entries."""

import threading

import numpy as np
from omegaconf import DictConfig

from linguaalayam.models.entries import Embeddable


class EmbeddingService:
    """Sentence-transformer wrapper that encodes dictionary entries into vectors.

    ``sentence_transformers`` (which pulls in ``torch``, a large import —
    measured independently at several seconds) is imported lazily in
    ``__init__`` rather than at module level. This module is imported at
    module level by ``rag/tools.py``, which is in turn imported at module
    level by ``api/web.py`` and ``api/app.py`` — so a module-level import
    here would be paid on every cold start the moment those modules are
    imported, before the app's lifespan (or any background-loading of the
    actual model) ever gets a chance to run.

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
        from sentence_transformers import SentenceTransformer

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


class LazyEmbeddingService:
    """Drop-in stand-in for ``EmbeddingService`` while the real one loads in the background.

    The real ``EmbeddingService`` construction (importing ``sentence_transformers``/
    ``torch`` and loading model weights) takes several seconds — real, but only
    actually needed by MCP's ``semantic_lookup`` tool, the CLI RAG pipeline, and
    the eval harness. The web search path (``api/web.py``) doesn't call any of
    this service's methods at all. Blocking the whole app's startup on it, as
    before, meant every purely-web cold start waited for a model only a minority
    of requests ever use.

    ``DictionaryTools`` is handed one of these immediately at startup; a
    background thread constructs the real ``EmbeddingService`` and calls
    ``set_ready()`` once done. Any method called before that (i.e. a real
    `semantic_lookup`/`encode` call reaching this instance first) blocks on a
    ``threading.Event`` until the real service is ready — a bounded per-request
    wait instead of delaying every request, including ones that never needed
    this at all.
    """

    def __init__(self) -> None:
        self._service: EmbeddingService | None = None
        self._ready = threading.Event()

    def set_ready(self, service: EmbeddingService) -> None:
        """Make the real service available; wakes up any callers already waiting.

        Parameters
        ----------
        service : EmbeddingService
            The fully-constructed real embedding service.
        """
        self._service = service
        self._ready.set()

    def _wait(self) -> EmbeddingService:
        """Block until the real service is ready, then return it."""
        self._ready.wait()
        assert self._service is not None  # set_ready() always sets both together
        return self._service

    @property
    def vector_size(self) -> int:
        """Dimensionality of the embedding vectors produced by the model."""
        return self._wait().vector_size

    @property
    def batch_size(self) -> int:
        """Number of texts encoded per forward pass."""
        return self._wait().batch_size

    def encode(self, entries: list[Embeddable]) -> list[list[float]]:
        """Encode entries once the real service is ready — see EmbeddingService.encode."""
        return self._wait().encode(entries)

    def encode_query(self, query: str) -> list[float]:
        """Encode a query once the real service is ready — see EmbeddingService.encode_query."""
        return self._wait().encode_query(query)

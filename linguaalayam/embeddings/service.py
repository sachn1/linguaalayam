import numpy as np
from omegaconf import DictConfig
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

from linguaalayam.models.entries import Embeddable


class EmbeddingService:
    def __init__(self, embedding_cfg: DictConfig) -> None:
        self._cfg = embedding_cfg
        self._model = SentenceTransformer(embedding_cfg.model)

    @property
    def vector_size(self) -> int:
        return self._model.get_sentence_embedding_dimension()

    def encode(self, entries: list[Embeddable]) -> list[list[float]]:
        texts = [e.to_embed_text() for e in entries]
        vectors: np.ndarray = self._model.encode(
            texts,
            batch_size=self._cfg.batch_size,
            show_progress_bar=False,
            normalize_embeddings=self._cfg.normalize,
        )
        return vectors.tolist()

    def encode_query(self, query: str) -> list[float]:
        vector: np.ndarray = self._model.encode(
            query,
            normalize_embeddings=self._cfg.normalize,
        )
        return vector.tolist()


def batched(items: list, size: int):
    for i in range(0, len(items), size):
        yield items[i : i + size]


def embed_in_batches(
    service: EmbeddingService,
    entries: list[Embeddable],
    batch_size: int | None = None,
) -> list[list[float]]:
    """Encode all entries in batches with a progress bar."""
    size = batch_size or service._cfg.batch_size
    all_vectors: list[list[float]] = []

    for batch in tqdm(list(batched(entries, size)), desc="Embedding"):
        all_vectors.extend(service.encode(batch))

    return all_vectors
"""Cross-encoder reranker for merging and re-scoring candidates from multiple tools."""

from sentence_transformers import CrossEncoder

_DEFAULT_MODEL = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


class CrossEncoderReranker:
    """Reranks a mixed candidate list using a multilingual cross-encoder.

    Useful when exact + fuzzy + semantic results are merged: their original
    scores are incommensurable, so the cross-encoder provides a unified
    relevance signal over the combined list.

    Parameters
    ----------
    model_name : str, optional
        HuggingFace model identifier for the cross-encoder.
        Defaults to ``"cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"``.
    """

    def __init__(self, model_name: str = _DEFAULT_MODEL) -> None:
        self._model = CrossEncoder(model_name)

    def rerank(
        self,
        query: str,
        candidates: list[dict],
        top_n: int | None = None,
    ) -> list[dict]:
        """Score each (query, embed_text) pair and return candidates sorted by score.

        Parameters
        ----------
        query : str
            The user's original query string.
        candidates : list[dict]
            Candidate result dicts; each must have an ``"embed_text"`` key.
        top_n : int or None, optional
            Truncate the sorted list to this many results. Returns all when ``None``.

        Returns
        -------
        list[dict]
            Candidates sorted by descending cross-encoder score, optionally truncated.
        """
        if not candidates:
            return candidates

        pairs = [(query, c["embed_text"]) for c in candidates]
        scores = self._model.predict(pairs)

        scored = sorted(zip(scores, candidates), key=lambda x: float(x[0]), reverse=True)
        reranked = [c for _, c in scored]
        return reranked[:top_n] if top_n is not None else reranked

"""Retriever module for performing similarity search on dictionary entries."""

from sqlalchemy.orm import sessionmaker

from linguaalayam.database.queries import similarity_search
from linguaalayam.database.session import get_session
from linguaalayam.embeddings.service import EmbeddingService
from linguaalayam.models import DictionaryEntry


class Retriever:
    """Retriever class for performing similarity search on dictionary entries."""

    def __init__(self, embedding_service: EmbeddingService, session_factory: sessionmaker) -> None:
        """_summary_

        Parameters
        ----------
        embedding_service : EmbeddingService
            _description_
        session_factory : sessionmaker
            _description_
        """
        self._embedder = embedding_service
        self._session_factory = session_factory

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        source: str | None = None,
        entry_type: str | None = None,
    ) -> list[dict]:
        """_summary_

        Parameters
        ----------
        query : str
            _description_
        top_k : int, optional
            _description_, by default 5
        source : str | None, optional
            _description_, by default None
        entry_type : str | None, optional
            _description_, by default None

        Returns
        -------
        list[dict]
            _description_
        """
        query_vector = self._embedder.encode_query(query)

        with get_session(self._session_factory) as session:
            results: list[DictionaryEntry] = similarity_search(
                session,
                query_vector=query_vector,
                top_k=top_k,
                source=source,
                entry_type=entry_type,
            )

        return [self._to_context(r) for r in results]

    @staticmethod
    def _to_context(entry: DictionaryEntry) -> dict:
        """_summary_

        Parameters
        ----------
        entry : DictionaryEntry
            _description_

        Returns
        -------
        dict
            _description_
        """
        return {
            "headword": entry.headword,
            "source": entry.source,
            "entry_type": entry.entry_type,
            "embed_text": entry.embed_text,
            "data": entry.data,
        }

"""SQLAlchemy ORM model for the ``dictionary_entries`` table."""

import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, Integer, MetaData, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

_NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base with a standard naming convention for constraints."""

    metadata = MetaData(naming_convention=_NAMING_CONVENTION)


class DictionaryEntry(Base):
    """ORM model for a single dictionary entry stored in Postgres.

    All corpus entry types (EN→ML, ML→ML, thesaurus, cross-lingual) share
    this table. The ``entry_type`` column records the originating Python class
    name. Raw structured data is stored in ``data`` (JSONB) so each corpus
    can carry its own schema without additional tables.

    Attributes
    ----------
    id : int
        Auto-incrementing primary key.
    source : str
        Corpus identifier (e.g. ``"olam_enml"``, ``"datuk"``).
    entry_type : str
        Python class name of the originating entry dataclass.
    headword : str
        The primary lookup term.
    embed_text : str
        Flattened text used to generate the embedding vector.
    data : dict
        Full serialised entry as a JSONB object.
    embedding : list[float]
        768-dimensional vector from the sentence-transformer model.
    created_at : datetime
        Server-side timestamp set on insert.
    """

    __tablename__ = "dictionary_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    entry_type: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    headword: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    embed_text: Mapped[str] = mapped_column(Text, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)
    embedding: Mapped[list[float]] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("source", "headword"),
        Index(
            "ix_dictionary_entries_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("ix_dictionary_entries_source_headword", "source", "headword"),
    )

    def __repr__(self) -> str:
        """Return a concise string representation showing id, headword, and source."""
        return f"<DictionaryEntry id={self.id} headword={self.headword!r} source={self.source!r}>"

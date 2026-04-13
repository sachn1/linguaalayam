from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, Text, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import datetime


class Base(DeclarativeBase):
    pass


class DictionaryEntry(Base):
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
        # HNSW index for fast approximate nearest-neighbour search
        Index(
            "ix_dictionary_entries_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        # Composite index for filtered searches
        Index("ix_dictionary_entries_source_headword", "source", "headword"),
    )

    def __repr__(self) -> str:
        return f"<DictionaryEntry id={self.id} headword={self.headword!r} source={self.source!r}>"
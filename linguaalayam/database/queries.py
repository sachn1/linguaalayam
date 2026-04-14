from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from linguaalayam.models.entries import Embeddable
from linguaalayam.models.orm import DictionaryEntry


def batch_insert(
    session: Session,
    entries: list[Embeddable],
    vectors: list[list[float]],
) -> None:
    """Insert entries with their vectors, skipping duplicates on (source, headword, embed_text)."""
    rows = [
        {
            "source": entry.source,
            "entry_type": type(entry).__name__,
            "headword": entry.headword,
            "embed_text": entry.to_embed_text(),
            "data": asdict(entry),  # type: ignore[call-overload]
            "embedding": vector,
        }
        for entry, vector in zip(entries, vectors)
    ]

    stmt = insert(DictionaryEntry).values(rows)
    stmt = stmt.on_conflict_do_nothing()  # idempotent re-runs
    session.execute(stmt)


def similarity_search(
    session: Session,
    query_vector: list[float],
    top_k: int = 5,
    source: str | None = None,
    entry_type: str | None = None,
) -> list[DictionaryEntry]:
    """Return top_k entries ranked by cosine similarity to query_vector."""
    stmt = (
        select(DictionaryEntry)
        .order_by(DictionaryEntry.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )

    if source:
        stmt = stmt.where(DictionaryEntry.source == source)
    if entry_type:
        stmt = stmt.where(DictionaryEntry.entry_type == entry_type)

    return list(session.scalars(stmt))


def get_ingested_headwords(session: Session, source: str) -> set[str]:
    """Return the set of headwords already stored for a given source.

    Used by the ingest script to skip work already done, making re-runs
    safe and resumable after interruption.
    """
    rows = session.execute(
        select(DictionaryEntry.headword).where(DictionaryEntry.source == source)
    ).scalars()
    return set(rows)
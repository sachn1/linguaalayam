"""Database query functions for dictionary entries."""
from dataclasses import asdict

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from linguaalayam.models.entries import Embeddable
from linguaalayam.models.orm import DictionaryEntry


def batch_insert(
    session: Session,
    entries: list[Embeddable],
    vectors: list[list[float]],
) -> None:
    """Insert entries with their vectors, skipping duplicates on (source, headword).

    Uses Postgres ON CONFLICT DO NOTHING when running against Postgres.
    Falls back to a pre-insert existence check for other dialects (e.g. SQLite in tests).

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    entries : list[Embeddable]
        List of entries to insert.
    vectors : list[list[float]]
        List of vectors corresponding to the entries.
    """
    if not entries:
        return

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

    dialect = session.bind.dialect.name if session.bind else session.get_bind().dialect.name

    if dialect == "postgresql":
        stmt = pg_insert(DictionaryEntry).values(rows)
        stmt = stmt.on_conflict_do_nothing(
            constraint="uq_dictionary_entries_source_headword"
        )
        session.execute(stmt)
    else:
        # Fallback for non-Postgres (e.g. SQLite in tests): filter existing before insert
        existing = set(
            session.execute(
                select(DictionaryEntry.headword).where(
                    DictionaryEntry.source == rows[0]["source"]
                )
            ).scalars()
        )
        new_rows = [r for r in rows if r["headword"] not in existing]
        if new_rows:
            session.execute(DictionaryEntry.__table__.insert(), new_rows)


def similarity_search(
    session: Session,
    query_vector: list[float],
    top_k: int = 5,
    source: str | None = None,
    entry_type: str | None = None,
) -> list[DictionaryEntry]:
    """Return top_k entries ranked by cosine similarity to query_vector.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    query_vector : list[float]
        Query vector to compare against stored embeddings.
    top_k : int, optional
        Number of top results to return, by default 5
    source : str | None, optional
        Source identifier to filter by, by default None
    entry_type : str | None, optional
        Entry type to filter by, by default None

    Returns
    -------
    list[DictionaryEntry]
        List of dictionary entries matching the query.
    """
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

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    source : str
        Source identifier to filter by (e.g. "olam_enml")

    Returns
    -------
    set[str]
        Set of headwords already stored for the given source.
    """
    rows = session.execute(
        select(DictionaryEntry.headword).where(DictionaryEntry.source == source)
    ).scalars()
    return set(rows)

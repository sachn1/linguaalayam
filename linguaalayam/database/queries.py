"""Database query functions for dictionary entries."""

from dataclasses import asdict

from sqlalchemy import func, select
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
        stmt = stmt.on_conflict_do_nothing(constraint="uq_dictionary_entries_source_headword")
        session.execute(stmt)
    else:
        # Fallback for non-Postgres (e.g. SQLite in tests): filter existing before insert
        existing = set(
            session.execute(
                select(DictionaryEntry.headword).where(DictionaryEntry.source == rows[0]["source"])
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
) -> list[tuple[DictionaryEntry, float]]:
    """Return top_k entries ranked by cosine similarity to query_vector.

    Returns (entry, score) tuples where score = 1 - cosine_distance ∈ [0, 1].

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
    """
    cos_dist = DictionaryEntry.embedding.cosine_distance(query_vector)
    stmt = select(DictionaryEntry, cos_dist.label("dist")).order_by(cos_dist).limit(top_k)

    if source:
        stmt = stmt.where(DictionaryEntry.source == source)
    if entry_type:
        stmt = stmt.where(DictionaryEntry.entry_type == entry_type)

    return [(row[0], round(1.0 - float(row[1]), 4)) for row in session.execute(stmt)]


def exact_search(
    session: Session,
    headword: str,
    source: str | None = None,
) -> list[DictionaryEntry]:
    """Return entries whose headword is a case-insensitive exact match.

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    headword : str
        The exact headword to look up (case-insensitive).
    source : str | None, optional
        Source identifier to filter by, by default None
    """
    stmt = select(DictionaryEntry).where(func.lower(DictionaryEntry.headword) == headword.lower())
    if source:
        stmt = stmt.where(DictionaryEntry.source == source)
    return list(session.scalars(stmt))


def fuzzy_search(
    session: Session,
    query: str,
    source: str | None = None,
    threshold: float = 0.3,
    limit: int = 10,
) -> list[tuple[DictionaryEntry, float]]:
    """Return entries whose headword is trigram-similar to query (pg_trgm).

    Returns (entry, score) tuples where score is the pg_trgm similarity ∈ [0, 1].
    Falls back to ILIKE with score=1.0 for non-Postgres dialects (e.g. SQLite in tests).

    Requires the pg_trgm extension and ix_dictionary_entries_headword_trgm GIN index
    (added by Alembic migration c2a4f6b8d0e2).

    Parameters
    ----------
    session : Session
        SQLAlchemy session to use for the query.
    query : str
        The query string to match against headwords.
    source : str | None, optional
        Source identifier to filter by, by default None
    threshold : float, optional
        Minimum trigram similarity score (0–1), by default 0.3
    limit : int, optional
        Maximum number of results to return, by default 10
    """
    dialect = session.bind.dialect.name if session.bind else session.get_bind().dialect.name

    if dialect == "postgresql":
        similarity = func.similarity(DictionaryEntry.headword, query)
        stmt = (
            select(DictionaryEntry, similarity.label("score"))
            .where(similarity > threshold)
            .order_by(similarity.desc())
            .limit(limit)
        )
        if source:
            stmt = stmt.where(DictionaryEntry.source == source)
        return [(row[0], round(float(row[1]), 4)) for row in session.execute(stmt)]

    stmt = select(DictionaryEntry).where(DictionaryEntry.headword.ilike(f"%{query}%")).limit(limit)
    if source:
        stmt = stmt.where(DictionaryEntry.source == source)
    return [(entry, 1.0) for entry in session.scalars(stmt)]


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

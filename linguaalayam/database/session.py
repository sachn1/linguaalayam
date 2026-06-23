"""Database session management — engine factory, session context manager, and DDL helpers."""

from collections.abc import Generator
from contextlib import contextmanager
from urllib.parse import quote_plus

from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from linguaalayam.models.orm import Base


def build_engine(db_cfg: DictConfig) -> Engine:
    """Create a SQLAlchemy engine from a Hydra database config.

    Registers a ``connect`` listener that ensures the ``vector`` extension is
    present so pgvector operations work without a separate migration step.

    Parameters
    ----------
    db_cfg : DictConfig
        Database configuration with keys: ``user``, ``password``, ``host``,
        ``port``, ``name``, ``pool_size``, ``max_overflow``.
        An optional ``sslmode`` key (e.g. ``"require"``) is appended to the
        connection URL when present.

    Returns
    -------
    Engine
        Configured SQLAlchemy engine with connection pooling.
    """
    sslmode = OmegaConf.select(db_cfg, "sslmode")
    sslmode_param = f"?sslmode={sslmode}" if sslmode else ""
    url = (
        f"postgresql+psycopg2://{db_cfg.user}:{quote_plus(db_cfg.password)}"
        f"@{db_cfg.host}:{db_cfg.port}/{db_cfg.name}{sslmode_param}"
    )
    engine = create_engine(
        url,
        pool_pre_ping=True,
        pool_size=db_cfg.pool_size,
        max_overflow=db_cfg.max_overflow,
    )

    # TODO: check why is this relevant?
    # we deliberately connects to a pgvector supported docker image
    # why shouldn't it have a pgvector extension?
    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, _connection_record) -> None:  # pragma: no cover
        """Ensure the pgvector extension is available on every new connection."""
        with dbapi_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        dbapi_conn.commit()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker:
    """Create a SQLAlchemy session factory bound to the given engine.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine to bind sessions to.

    Returns
    -------
    sessionmaker
        A callable session factory; call it to obtain a new ``Session``.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session(session_factory: sessionmaker) -> Generator[Session, None, None]:
    """Context manager that yields a transactional database session.

    Commits on clean exit, rolls back on any exception, and always closes
    the session on exit.

    Parameters
    ----------
    session_factory : sessionmaker
        The session factory used to create the session.

    Yields
    ------
    Session
        An active SQLAlchemy session.

    Raises
    ------
    Exception
        Any exception raised within the ``with`` block after rolling back.
    """
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables(engine: Engine) -> None:
    """Create all ORM-defined tables in the database if they do not exist.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine pointing at the target database.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables(engine: Engine) -> None:
    """Drop all ORM-defined tables from the database.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine pointing at the target database.
    """
    Base.metadata.drop_all(bind=engine)

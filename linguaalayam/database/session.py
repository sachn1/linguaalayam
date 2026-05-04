"""Database session management and utilities."""

from collections.abc import Generator
from contextlib import contextmanager
from urllib.parse import quote_plus

from dotenv import load_dotenv
from omegaconf import DictConfig, OmegaConf
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from linguaalayam.models.orm import Base

load_dotenv()


def build_engine(db_cfg: DictConfig) -> Engine:
    """Build a SQLAlchemy engine for the database.

    Parameters
    ----------
    db_cfg : DictConfig
        Configuration for the database connection.

    Returns
    -------
    Engine
        The SQLAlchemy engine for the database.
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

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, _connection_record) -> None:
        """Ensure the pgvector extension is available in the database."""
        with dbapi_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        dbapi_conn.commit()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker:
    """Build a SQLAlchemy session factory.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine to bind to the session factory.

    Returns
    -------
    sessionmaker
        The SQLAlchemy session factory.
    """
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session(session_factory: sessionmaker) -> Generator[Session, None, None]:
    """

    Parameters
    ----------
    session_factory : sessionmaker
        The SQLAlchemy session factory to use for creating sessions.

    Yields
    ------
    Generator[Session, None, None]
        A generator that yields a SQLAlchemy session.
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
    """Create database tables based on the defined ORM models.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine to use for creating the tables.
    """
    Base.metadata.create_all(bind=engine)


def drop_tables(engine: Engine) -> None:
    """Drop all tables in the database.

    Parameters
    ----------
    engine : Engine
        The SQLAlchemy engine to use for dropping the tables.
    """
    Base.metadata.drop_all(bind=engine)

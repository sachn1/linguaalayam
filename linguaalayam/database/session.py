from collections.abc import Generator
from contextlib import contextmanager

from omegaconf import DictConfig
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from linguaalayam.models.orm import Base


def build_engine(db_cfg: DictConfig) -> Engine:
    engine = create_engine(
        db_cfg.url,
        pool_pre_ping=True,
        pool_size=db_cfg.pool_size,
        max_overflow=db_cfg.max_overflow,
    )

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_conn, _connection_record) -> None:
        with dbapi_conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        dbapi_conn.commit()

    return engine


def build_session_factory(engine: Engine) -> sessionmaker:
    return sessionmaker(bind=engine, expire_on_commit=False)


@contextmanager
def get_session(session_factory: sessionmaker) -> Generator[Session, None, None]:
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
    Base.metadata.create_all(bind=engine)


def drop_tables(engine: Engine) -> None:
    Base.metadata.drop_all(bind=engine)
from collections.abc import Generator
from contextlib import contextmanager

from omegaconf import DictConfig
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from urllib.parse import quote_plus

from linguaalayam.models.orm import Base
from dotenv import load_dotenv
load_dotenv()

def build_engine(db_cfg: DictConfig) -> Engine:
    url = (
    f"postgresql+psycopg2://{db_cfg.user}:{quote_plus(db_cfg.password)}"
    f"@{db_cfg.host}:{db_cfg.port}/{db_cfg.name}?sslmode=require"
)
    engine = create_engine(url, pool_pre_ping=True,
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
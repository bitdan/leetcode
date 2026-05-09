from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_session_factory(postgres_dsn: str):
    if not postgres_dsn:
        raise RuntimeError("POSTGRES_DSN 未配置")
    engine = create_engine(
        postgres_dsn,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=5,
        future=True,
    )
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)


@contextmanager
def session_scope(session_factory) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

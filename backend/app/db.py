from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


# Sync engine on purpose: routes are plain `def`, so FastAPI runs them in its threadpool and the
# blocking psycopg driver never stalls the event loop.
# hide_parameters: a failed query's error message would otherwise include the prospect's name and
# email, and that message ends up in the logs.
engine = create_engine(get_settings().database_url, pool_pre_ping=True, hide_parameters=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    with SessionLocal() as session:
        yield session

"""Database engine and session helpers (feature 05a)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def make_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()


def create_db_and_tables(bind=None) -> None:
    # Import models so their tables register on SQLModel.metadata before create_all.
    from app.models import bug, commit, config_state, expertise, task  # noqa: F401

    SQLModel.metadata.create_all(bind if bind is not None else engine)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

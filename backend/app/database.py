"""Database engine and session helpers (feature 05a)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import inspect, text
from sqlmodel import Session, SQLModel, create_engine

from app.config import get_settings


def make_engine(database_url: str | None = None):
    url = database_url or get_settings().database_url
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


engine = make_engine()

# Columns added after a DB may already exist. create_all() never alters existing
# tables, and the project has no migration tool, so add them idempotently.
_ADDED_COLUMNS: dict[str, dict[str, str]] = {
    "task": {"candidates": "JSON", "declined_emails": "JSON"},
}


def _ensure_added_columns(bind) -> None:
    inspector = inspect(bind)
    tables = set(inspector.get_table_names())
    for table, columns in _ADDED_COLUMNS.items():
        if table not in tables:
            continue
        existing = {c["name"] for c in inspector.get_columns(table)}
        with bind.begin() as conn:
            for name, col_type in columns.items():
                if name not in existing:
                    conn.execute(
                        text(f"ALTER TABLE {table} ADD COLUMN {name} {col_type} DEFAULT '[]'")
                    )


def create_db_and_tables(bind=None) -> None:
    # Import models so their tables register on SQLModel.metadata before create_all.
    from app.models import bug, commit, config_state, expertise, task  # noqa: F401

    target = bind if bind is not None else engine
    SQLModel.metadata.create_all(target)
    _ensure_added_columns(target)


def get_session() -> Iterator[Session]:
    with Session(engine) as session:
        yield session

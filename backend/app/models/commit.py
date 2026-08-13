"""Commit model — one row per (commit x file), the raw git data."""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class Commit(SQLModel, table=True):
    __tablename__ = "commits"

    id: int | None = Field(default=None, primary_key=True)
    commit_hash: str = Field(index=True)
    author_email: str = Field(index=True)
    file_path: str
    lines_added: int
    lines_deleted: int
    committed_at: datetime

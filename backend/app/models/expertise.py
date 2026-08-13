"""Expertise model — one row per (developer, module) pair."""
from __future__ import annotations

from datetime import datetime

from sqlmodel import Field, SQLModel


class Expertise(SQLModel, table=True):
    __tablename__ = "expertise"

    id: int | None = Field(default=None, primary_key=True)
    developer_email: str = Field(index=True)
    module_path: str = Field(index=True)
    score: float
    commit_count: int
    last_updated: datetime

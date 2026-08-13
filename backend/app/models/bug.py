"""Bug model — one row per submitted bug report."""
from __future__ import annotations

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Bug(SQLModel, table=True):
    __tablename__ = "bug"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    modules: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    severity: str | None = None

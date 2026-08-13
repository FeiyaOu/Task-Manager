"""Bug model — one row per submitted bug report."""
from __future__ import annotations

from sqlmodel import Field, SQLModel


class Bug(SQLModel, table=True):
    __tablename__ = "bug"

    id: int | None = Field(default=None, primary_key=True)
    title: str
    description: str
    module: str | None = None
    severity: str | None = None

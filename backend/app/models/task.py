"""Task model — one row per assignment.

Carries the extension-ready state fields (status, score, matched_modules,
reassign_count) from v1 even though v1 never transitions or reassigns.
"""
from __future__ import annotations

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel

from app.models.enums import TaskStatus


class Task(SQLModel, table=True):
    __tablename__ = "task"

    id: int | None = Field(default=None, primary_key=True)
    bug_id: int = Field(foreign_key="bug.id")
    assigned_email: str | None = None
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    score: float | None = None
    matched_modules: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    reassign_count: int = Field(default=0)
    match_tier: str | None = None  # module / broadened / text / unassigned

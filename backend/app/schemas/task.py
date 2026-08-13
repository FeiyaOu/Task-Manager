"""Task read schema for the API (spec 05-api)."""
from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import TaskStatus


class TaskRead(BaseModel):
    task_id: int
    bug_id: int
    title: str
    modules: list[str]
    assigned_email: str | None
    score: float | None
    matched_modules: list[str]
    status: TaskStatus
    match_tier: str | None = None

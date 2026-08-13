"""API schemas for bug submission and assignment result (feature 04/05)."""
from __future__ import annotations

from pydantic import BaseModel

from app.models.enums import TaskStatus


class BugSubmit(BaseModel):
    title: str
    description: str
    modules: list[str] = []
    severity: str | None = None


class CandidateRead(BaseModel):
    developer_email: str
    score: float
    matched_modules: list[str]


class AssignmentResult(BaseModel):
    bug_id: int
    task_id: int
    assigned_email: str | None
    score: float | None
    matched_modules: list[str]
    status: TaskStatus
    match_tier: str | None = None
    candidates: list[CandidateRead] = []

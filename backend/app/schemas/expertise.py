"""Expertise read schema for the API."""
from __future__ import annotations

from pydantic import BaseModel


class ExpertiseRead(BaseModel):
    developer_email: str
    module_path: str
    score: float
    commit_count: int

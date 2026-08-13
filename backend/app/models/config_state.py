"""Config state — single row tracking the last analyzed commit."""
from __future__ import annotations

from sqlmodel import Field, SQLModel


class ConfigState(SQLModel, table=True):
    __tablename__ = "config_state"

    id: int | None = Field(default=None, primary_key=True)
    last_analyzed_commit_hash: str | None = None

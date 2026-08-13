"""Application settings loaded from environment / .env (feature 05a).

Mirrors the .env keys in spec/project-structure.md.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    repo_path: str = ""
    database_url: str = "sqlite:///./taskmanager.db"
    decay_lambda: float = 0.01
    max_reassignments: int = 3
    assign_threshold: float = 0.0
    module_depth: int = 1
    cors_origins: list[str] = ["http://localhost:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()

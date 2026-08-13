"""Tests for application settings (feature 05a).

Config carries the .env values (spec/project-structure.md): REPO_PATH,
DATABASE_URL, DECAY_LAMBDA, MAX_REASSIGNMENTS, plus the assignment threshold.
"""
from __future__ import annotations

from app.config import Settings, get_settings


def test_defaults():
    s = Settings()
    assert s.decay_lambda == 0.01
    assert s.max_reassignments == 3
    assert s.assign_threshold == 0.0
    assert s.database_url.startswith("sqlite")


def test_env_override(monkeypatch):
    monkeypatch.setenv("DECAY_LAMBDA", "0.05")
    monkeypatch.setenv("REPO_PATH", "/tmp/repo")
    monkeypatch.setenv("MAX_REASSIGNMENTS", "7")
    s = Settings()
    assert s.decay_lambda == 0.05
    assert s.repo_path == "/tmp/repo"
    assert s.max_reassignments == 7


def test_get_settings_is_cached():
    assert get_settings() is get_settings()

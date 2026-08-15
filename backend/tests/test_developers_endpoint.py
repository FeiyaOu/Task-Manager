"""Tests for GET /api/developers (spec 06-developer-activity-filter).

Uses the same in-memory SQLite + TestClient pattern as test_api.py.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

import app.database as database
from app.config import get_settings
from tests.conftest import SeededCommit


@pytest.fixture
def api(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    monkeypatch.setattr(database, "engine", engine)
    database.create_db_and_tables()

    from app.main import create_app

    with TestClient(create_app()) as client:
        yield client


def _refresh(api, monkeypatch, repo: str):
    monkeypatch.setenv("REPO_PATH", repo)
    get_settings.cache_clear()
    return api.post("/api/repo/refresh")


# Edge case: no commits ever ingested -> [].
def test_no_commits_returns_empty(api):
    assert api.get("/api/developers").json() == []


# Rule 1: no `days` param -> all-time distinct emails.
def test_no_days_param_returns_all_time_developers(api, make_repo, monkeypatch):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=40,
                     files={"old/mod.py": "1\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=1,
                     files={"recent/mod.py": "1\n"}),
    ])
    _refresh(api, monkeypatch, repo)
    assert sorted(api.get("/api/developers").json()) == ["alice@x.com", "bob@x.com"]


# Rule 2: days=N -> only developers with a commit at or after now - N days.
def test_days_window_filters_by_recency(api, make_repo, monkeypatch):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=40,
                     files={"old/mod.py": "1\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=1,
                     files={"recent/mod.py": "1\n"}),
    ])
    _refresh(api, monkeypatch, repo)
    assert api.get("/api/developers", params={"days": 7}).json() == ["bob@x.com"]


# Rule 3: an author with multiple commits appears once.
def test_dedupes_repeat_committer(api, make_repo, monkeypatch):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=2,
                     files={"a/one.py": "1\n"}),
        SeededCommit("Alice", "alice@x.com", days_ago=1,
                     files={"a/two.py": "1\n"}),
    ])
    _refresh(api, monkeypatch, repo)
    assert api.get("/api/developers").json() == ["alice@x.com"]


# Rule 4: result is sorted alphabetically.
def test_result_sorted_alphabetically(api, make_repo, monkeypatch):
    repo = make_repo([
        SeededCommit("Zed", "zed@x.com", days_ago=1, files={"z/one.py": "1\n"}),
        SeededCommit("Alice", "alice@x.com", days_ago=1, files={"a/one.py": "1\n"}),
        SeededCommit("Mona", "mona@x.com", days_ago=1, files={"m/one.py": "1\n"}),
    ])
    _refresh(api, monkeypatch, repo)
    assert api.get("/api/developers").json() == ["alice@x.com", "mona@x.com", "zed@x.com"]


# Edge case: days=N with zero commits in that window -> [].
def test_days_window_with_no_activity_returns_empty(api, make_repo, monkeypatch):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=40,
                     files={"old/mod.py": "1\n"}),
    ])
    _refresh(api, monkeypatch, repo)
    assert api.get("/api/developers", params={"days": 7}).json() == []


# Edge case: negative days -> 422.
def test_negative_days_returns_422(api):
    assert api.get("/api/developers", params={"days": -1}).status_code == 422

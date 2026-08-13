"""Tests for the FastAPI layer (feature 05c / spec 05-api).

Uses a shared in-memory SQLite engine (StaticPool) so every request in a test
hits the same database, and drives the app through TestClient.
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


def _seed_repo(make_repo) -> str:
    return make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\nb\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=0,
                     files={"billing/pay.py": "x\n"}),
    ])


def _refresh(api, monkeypatch, repo: str):
    monkeypatch.setenv("REPO_PATH", repo)
    get_settings.cache_clear()
    return api.post("/api/repo/refresh")


# POST /api/bugs Rule 1: missing required fields -> 422.
def test_submit_missing_fields_422(api):
    assert api.post("/api/bugs", json={}).status_code == 422


# POST /api/bugs Rule 2: repo not analyzed -> UNASSIGNED.
def test_unanalyzed_repo_unassigned(api):
    r = api.post(
        "/api/bugs",
        json={"title": "t", "description": "d", "module": "auth/"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "unassigned"
    assert body["assigned_email"] is None


# POST /api/repo/refresh returns counts; then POST /api/bugs assigns top dev.
def test_refresh_then_assign(api, make_repo, monkeypatch):
    rr = _refresh(api, monkeypatch, _seed_repo(make_repo))
    assert rr.status_code == 200
    assert rr.json()["new_commits"] == 2

    r = api.post(
        "/api/bugs",
        json={"title": "login", "description": "auth login fails", "module": "auth/"},
    )
    body = r.json()
    assert body["assigned_email"] == "alice@x.com"
    assert body["status"] == "pending"


# GET /api/modules Rules 5 + 6: unique modules from the analyzed repo.
def test_modules_unique(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_repo(make_repo))
    mods = api.get("/api/modules").json()
    assert sorted(mods) == ["auth/", "billing/"]
    assert len(mods) == len(set(mods))


# GET /api/tasks Rules 3 + 4: newest first, includes state fields.
def test_tasks_newest_first_with_fields(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_repo(make_repo))
    api.post("/api/bugs", json={"title": "first", "description": "auth", "module": "auth/"})
    api.post("/api/bugs", json={"title": "second", "description": "billing", "module": "billing/"})

    tasks = api.get("/api/tasks").json()
    assert tasks[0]["title"] == "second"  # newest first
    assert {"status", "assigned_email", "score", "matched_modules"} <= set(tasks[0])


# GET /api/repo/status reports repo path, last commit, and counts.
def test_repo_status(api, make_repo, monkeypatch):
    repo = _seed_repo(make_repo)
    _refresh(api, monkeypatch, repo)
    body = api.get("/api/repo/status").json()
    assert body["repo_path"] == repo
    assert body["last_analyzed_commit"] is not None
    assert body["developer_count"] == 2
    assert body["module_count"] == 2


# POST /api/repo/refresh?days=N limits analysis to the recent window.
def test_refresh_days_window(api, make_repo, monkeypatch):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=40,
                     files={"old/mod.py": "1\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=1,
                     files={"recent/mod.py": "1\n"}),
    ])
    monkeypatch.setenv("REPO_PATH", repo)
    get_settings.cache_clear()
    result = api.post("/api/repo/refresh", params={"days": 7}).json()
    assert result["new_commits"] == 1
    assert api.get("/api/modules").json() == ["recent/"]


# GET /api/expertise exposes the expertise map rows.
def test_expertise_lists_rows(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_repo(make_repo))
    rows = api.get("/api/expertise").json()
    assert all(
        {"developer_email", "module_path", "score", "commit_count"} <= set(r)
        for r in rows
    )
    assert {r["developer_email"] for r in rows} == {"alice@x.com", "bob@x.com"}


# GET /api/expertise?developer= filters to one developer.
def test_expertise_filter_by_developer(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_repo(make_repo))
    rows = api.get("/api/expertise", params={"developer": "alice@x.com"}).json()
    assert {r["developer_email"] for r in rows} == {"alice@x.com"}


# POST /api/bugs now returns the ranked candidate list.
def test_bugs_returns_candidates(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_repo(make_repo))
    body = api.post(
        "/api/bugs",
        json={"title": "login", "description": "auth login fails", "module": "auth/"},
    ).json()
    assert body["candidates"][0]["developer_email"] == "alice@x.com"


# POST /api/bugs reports which fallback tier produced the assignment.
def test_bugs_returns_match_tier(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_repo(make_repo))
    body = api.post(
        "/api/bugs",
        json={"title": "login", "description": "auth login fails", "module": "auth/"},
    ).json()
    assert body["match_tier"] == "module"


# MODULE_DEPTH config controls how granular the modules are.
def test_module_depth_config(api, make_repo, monkeypatch):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"Engine/Physics/x.cpp": "1\n",
                            "Engine/Audio/y.cpp": "1\n"}),
    ])
    monkeypatch.setenv("REPO_PATH", repo)
    monkeypatch.setenv("MODULE_DEPTH", "2")
    get_settings.cache_clear()
    api.post("/api/repo/refresh")
    assert api.get("/api/modules").json() == ["Engine/Audio/", "Engine/Physics/"]

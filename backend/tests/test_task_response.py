"""Tests for accept/decline + reassignment (spec 07-task-response).

Drives the API through TestClient against a shared in-memory SQLite engine,
mirroring tests/test_api.py. Each test traces back to a Rule or Edge case in
spec/features/07-task-response.md.
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


def _seed_two_auth(make_repo) -> str:
    """Alice (stronger) and Bob both work in auth/ -> two ranked candidates."""
    return make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\nb\nc\n"}),
        SeededCommit("Alice", "alice@x.com", days_ago=1,
                     files={"auth/token.py": "a\nb\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=0,
                     files={"auth/logout.py": "x\n"}),
    ])


def _seed_one_auth(make_repo) -> str:
    """Only Alice works in auth/ -> a single ranked candidate."""
    return make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\nb\nc\n"}),
    ])


def _refresh(api, monkeypatch, repo: str, max_reassignments: str | None = None):
    monkeypatch.setenv("REPO_PATH", repo)
    if max_reassignments is not None:
        monkeypatch.setenv("MAX_REASSIGNMENTS", max_reassignments)
    get_settings.cache_clear()
    return api.post("/api/repo/refresh")


def _submit_auth_bug(api) -> dict:
    return api.post(
        "/api/bugs",
        json={"title": "login", "description": "auth login fails", "modules": ["auth/"]},
    ).json()


# Rule 1: accept is valid on a PENDING task and sets status ACCEPTED.
def test_accept_sets_accepted(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo))
    task_id = _submit_auth_bug(api)["task_id"]

    r = api.post(f"/api/tasks/{task_id}/accept")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "accepted"
    assert body["assigned_email"] == "alice@x.com"


# Rule 1 + Rule 6: ACCEPTED is terminal -> a second action returns 409.
def test_accept_twice_409(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo))
    task_id = _submit_auth_bug(api)["task_id"]

    assert api.post(f"/api/tasks/{task_id}/accept").status_code == 200
    assert api.post(f"/api/tasks/{task_id}/accept").status_code == 409
    assert api.post(f"/api/tasks/{task_id}/decline").status_code == 409


# Rules 2 + 3: decline records the declining dev, bumps reassign_count, and
# reassigns to the next-best candidate while staying PENDING.
def test_decline_reassigns_to_next_candidate(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo))
    task_id = _submit_auth_bug(api)["task_id"]

    r = api.post(f"/api/tasks/{task_id}/decline")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending"
    assert body["assigned_email"] == "bob@x.com"
    assert body["reassign_count"] == 1
    assert body["declined_emails"] == ["alice@x.com"]


# Rule 3 (exhausted branch): once every candidate has declined, the task
# becomes UNASSIGNED with no assignee.
def test_decline_exhausts_candidates_unassigned(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo))
    task_id = _submit_auth_bug(api)["task_id"]

    api.post(f"/api/tasks/{task_id}/decline")  # alice -> bob
    body = api.post(f"/api/tasks/{task_id}/decline").json()  # bob -> exhausted
    assert body["status"] == "unassigned"
    assert body["assigned_email"] is None
    assert body["declined_emails"] == ["alice@x.com", "bob@x.com"]


# Rules 4 + 5: MAX_REASSIGNMENTS (from Settings) bounds bouncing -- with the
# cap at 1, the first decline forces UNASSIGNED even though Bob is untried.
def test_decline_respects_max_reassignments(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo), max_reassignments="1")
    task_id = _submit_auth_bug(api)["task_id"]

    body = api.post(f"/api/tasks/{task_id}/decline").json()
    assert body["status"] == "unassigned"
    assert body["assigned_email"] is None
    assert body["reassign_count"] == 1


# Rule 7: an action on an unknown task_id returns 404.
def test_action_on_unknown_task_404(api):
    assert api.post("/api/tasks/9999/accept").status_code == 404
    assert api.post("/api/tasks/9999/decline").status_code == 404


# Rule 6 + Edge (zero candidates): a task that was never assigned is UNASSIGNED,
# so accept/decline both return 409.
def test_action_on_unassigned_409(api):
    # No repo analyzed -> submission yields an UNASSIGNED task.
    body = api.post(
        "/api/bugs",
        json={"title": "t", "description": "d", "modules": ["auth/"]},
    ).json()
    assert body["status"] == "unassigned"
    task_id = body["task_id"]
    assert api.post(f"/api/tasks/{task_id}/accept").status_code == 409
    assert api.post(f"/api/tasks/{task_id}/decline").status_code == 409


# Edge (single candidate): the lone candidate declines -> immediately
# UNASSIGNED even though reassign_count (1) is below MAX_REASSIGNMENTS (3).
def test_single_candidate_decline_unassigned(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_one_auth(make_repo))
    task_id = _submit_auth_bug(api)["task_id"]

    body = api.post(f"/api/tasks/{task_id}/decline").json()
    assert body["status"] == "unassigned"
    assert body["assigned_email"] is None
    assert body["reassign_count"] == 1


# Edge (MAX_REASSIGNMENTS = 0): the very first decline forces UNASSIGNED
# regardless of remaining candidates.
def test_max_reassignments_zero(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo), max_reassignments="0")
    task_id = _submit_auth_bug(api)["task_id"]

    body = api.post(f"/api/tasks/{task_id}/decline").json()
    assert body["status"] == "unassigned"
    assert body["assigned_email"] is None


# Edge (beyond exhaustion): once UNASSIGNED, any further action returns 409.
def test_decline_after_unassigned_409(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo))
    task_id = _submit_auth_bug(api)["task_id"]

    api.post(f"/api/tasks/{task_id}/decline")  # alice -> bob
    api.post(f"/api/tasks/{task_id}/decline")  # bob -> unassigned
    assert api.post(f"/api/tasks/{task_id}/decline").status_code == 409
    assert api.post(f"/api/tasks/{task_id}/accept").status_code == 409


# Data-model/schema: GET /api/tasks exposes the new read-only fields.
def test_taskread_exposes_new_fields(api, make_repo, monkeypatch):
    _refresh(api, monkeypatch, _seed_two_auth(make_repo))
    _submit_auth_bug(api)

    task = api.get("/api/tasks").json()[0]
    assert "reassign_count" in task
    assert "declined_emails" in task
    assert task["reassign_count"] == 0
    assert task["declined_emails"] == []

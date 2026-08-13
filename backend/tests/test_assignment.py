"""Tests for the assignment orchestrator (feature 04).

Each test traces back to a numbered Rule or Edge case in
``spec/features/04-assignment.md``. Uses an in-memory SQLite session so the
persistence steps are exercised end to end.
"""
from __future__ import annotations

import pytest
from sqlmodel import Session, SQLModel, create_engine, select

from app.models.bug import Bug
from app.models.enums import TaskStatus
from app.models.task import Task
from app.schemas.bug import AssignmentResult, BugSubmit
from app.services.assignment import assign_bug

EMAP = {"alice@x.com": {"auth/": 50.0}}


@pytest.fixture
def session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        yield s


def _bug(module: str | None = "auth/") -> BugSubmit:
    return BugSubmit(
        title="login broken",
        description="auth login fails",
        module=module,
        severity="high",
    )


# Rule 1: the bug is saved to the bug table before matching.
def test_bug_is_persisted(session):
    result = assign_bug(_bug(), session, EMAP)
    saved = session.get(Bug, result.bug_id)
    assert saved is not None
    assert saved.title == "login broken"


# Rule 2 + 5: top candidate is chosen -> PENDING + that developer.
def test_top_candidate_assigned_pending(session):
    result = assign_bug(_bug(), session, EMAP)
    assert result.assigned_email == "alice@x.com"
    assert result.status == TaskStatus.PENDING
    assert result.score == pytest.approx(50.0)
    assert result.matched_modules == ["auth/"]


# Rule 3 + 8: a task row is persisted with state fields and reassign_count = 0.
def test_task_persisted_with_state(session):
    result = assign_bug(_bug(), session, EMAP)
    task = session.get(Task, result.task_id)
    assert task is not None
    assert task.bug_id == result.bug_id
    assert task.status == TaskStatus.PENDING
    assert task.score == pytest.approx(50.0)
    assert task.matched_modules == ["auth/"]
    assert task.reassign_count == 0


# Rule 4 (empty list) + edge: no developers -> UNASSIGNED, no assignee.
def test_no_developers_unassigned(session):
    result = assign_bug(_bug(), session, {})
    assert result.status == TaskStatus.UNASSIGNED
    assert result.assigned_email is None


# Below ALL tier thresholds -> UNASSIGNED (module + broaden + text gates).
def test_below_threshold_unassigned(session):
    result = assign_bug(
        _bug(), session, EMAP,
        threshold=100.0, broaden_threshold=100.0, text_threshold=100.0,
    )
    assert result.status == TaskStatus.UNASSIGNED
    assert result.assigned_email is None


# Edge: exactly-at-threshold is assigned (rejection is strict <).
def test_exactly_at_threshold_is_assigned(session):
    result = assign_bug(_bug(), session, EMAP, threshold=50.0)
    assert result.status == TaskStatus.PENDING
    assert result.assigned_email == "alice@x.com"


# Rule 6: the full AssignmentResult is returned synchronously.
def test_result_shape(session):
    result = assign_bug(_bug(), session, EMAP)
    assert isinstance(result, AssignmentResult)
    assert isinstance(result.bug_id, int)
    assert isinstance(result.task_id, int)
    assert result.status in set(TaskStatus)


# Rule 7: TaskStatus enum exposes the four v1 states.
def test_task_status_values():
    assert {s.name for s in TaskStatus} == {
        "PENDING",
        "ACCEPTED",
        "DECLINED",
        "UNASSIGNED",
    }


# One submission creates exactly one bug row and one task row.
def test_single_bug_and_task_rows(session):
    assign_bug(_bug(), session, EMAP)
    assert len(session.exec(select(Bug)).all()) == 1
    assert len(session.exec(select(Task)).all()) == 1


# The full ranked candidate list is exposed on the result (not just the winner).
def test_result_includes_ranked_candidates(session):
    emap = {"alice@x.com": {"auth/": 50.0}, "carla@x.com": {"auth/": 20.0}}
    result = assign_bug(_bug(), session, emap)
    assert [c.developer_email for c in result.candidates] == [
        "alice@x.com",
        "carla@x.com",
    ]
    assert result.candidates[0].score == pytest.approx(50.0)
    assert result.candidates[0].matched_modules == ["auth/"]


# No match -> empty candidate list.
def test_no_candidates_when_unassigned(session):
    result = assign_bug(_bug(), session, {})
    assert result.candidates == []


# Tier 0 (module) assignment records match_tier = "module".
def test_module_tier_match_tier(session):
    result = assign_bug(_bug(), session, EMAP)
    assert result.match_tier == "module"
    assert session.get(Task, result.task_id).match_tier == "module"


# Tier 1 (broaden): a selected sub-module with no expert falls back to its parent.
def test_broaden_tier_assigns(session):
    emap = {"alice@x.com": {"Engine/": 50.0}}
    bug = BugSubmit(
        title="Crash on load", description="null pointer",
        module="Engine/Physics/", severity="high",
    )
    result = assign_bug(bug, session, emap)
    assert result.assigned_email == "alice@x.com"
    assert result.status == TaskStatus.PENDING
    assert result.match_tier == "broadened"


# Tier 2 (text): below the primary gate but a keyword match clears the text gate.
def test_text_tier_assigns(session):
    emap = {"alice@x.com": {"billing/": 90.0}}
    bug = BugSubmit(
        title="payment", description="billing checkout fails",
        module="auth/", severity="low",
    )
    result = assign_bug(
        bug, session, emap,
        threshold=100.0, broaden_threshold=100.0, text_threshold=50.0,
    )
    assert result.assigned_email == "alice@x.com"
    assert result.match_tier == "text"


# Tier 3 (unassigned): all gates fail -> UNASSIGNED, but the near-miss is recorded.
def test_unassigned_records_near_miss(session):
    emap = {"alice@x.com": {"auth/": 30.0}}
    bug = BugSubmit(
        title="unrelated", description="totally different topic",
        module="auth/", severity="low",
    )
    result = assign_bug(
        bug, session, emap,
        threshold=100.0, broaden_threshold=100.0, text_threshold=100.0,
    )
    assert result.status == TaskStatus.UNASSIGNED
    assert result.assigned_email is None
    assert result.match_tier == "unassigned"
    assert result.score == pytest.approx(30.0)  # near-miss preserved
    assert result.candidates[0].developer_email == "alice@x.com"

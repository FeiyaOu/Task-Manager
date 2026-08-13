"""Assignment orchestrator (feature 04).

Persists the bug, ranks developers, assigns the top candidate above threshold,
and persists the resulting task with its state. Synchronous: the full result is
returned in one call.

Contract: see ``spec/features/04-assignment.md``.
"""
from __future__ import annotations

from sqlmodel import Session

from app.models.bug import Bug
from app.models.enums import TaskStatus
from app.models.task import Task
from app.schemas.bug import AssignmentResult, BugSubmit, CandidateRead
from app.services.matcher import BugInput, rank_developers

DEFAULT_THRESHOLD = 0.0


def assign_bug(
    bug: BugSubmit,
    session: Session,
    expertise_map: dict[str, dict[str, float]],
    threshold: float = DEFAULT_THRESHOLD,
) -> AssignmentResult:
    # Rule 1: persist the bug before matching.
    bug_row = Bug(
        title=bug.title,
        description=bug.description,
        module=bug.module,
        severity=bug.severity,
    )
    session.add(bug_row)
    session.commit()
    session.refresh(bug_row)

    # Rule 2: rank developers; result[0] is the top candidate.
    candidates = rank_developers(
        BugInput(title=bug.title, description=bug.description, module=bug.module),
        expertise_map,
    )
    top = candidates[0] if candidates else None

    # Rules 4 & 5: below threshold or no match -> UNASSIGNED; else PENDING.
    if top is None or top.score < threshold:
        status = TaskStatus.UNASSIGNED
        assigned_email = None
    else:
        status = TaskStatus.PENDING
        assigned_email = top.developer_email

    score = top.score if top else None
    matched_modules = top.matched_modules if top else []

    # Rule 3 & 8: persist the task with state fields and reassign_count = 0.
    task_row = Task(
        bug_id=bug_row.id,
        assigned_email=assigned_email,
        status=status,
        score=score,
        matched_modules=matched_modules,
        reassign_count=0,
    )
    session.add(task_row)
    session.commit()
    session.refresh(task_row)

    return AssignmentResult(
        bug_id=bug_row.id,
        task_id=task_row.id,
        assigned_email=assigned_email,
        score=score,
        matched_modules=matched_modules,
        status=status,
        candidates=[
            CandidateRead(
                developer_email=c.developer_email,
                score=c.score,
                matched_modules=c.matched_modules,
            )
            for c in candidates
        ],
    )

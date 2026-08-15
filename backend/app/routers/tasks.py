"""GET /api/tasks + accept/decline transitions (spec 05-api, 07-task-response)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.bug import Bug
from app.models.enums import TaskStatus
from app.models.task import Task
from app.schemas.task import TaskRead

router = APIRouter(prefix="/api", tags=["tasks"])


def _to_read(task: Task, session: Session) -> TaskRead:
    bug = session.get(Bug, task.bug_id)
    return TaskRead(
        task_id=task.id,
        bug_id=task.bug_id,
        title=bug.title if bug else "",
        modules=bug.modules if bug else [],
        assigned_email=task.assigned_email,
        score=task.score,
        matched_modules=task.matched_modules,
        status=task.status,
        match_tier=task.match_tier,
        reassign_count=task.reassign_count,
        declined_emails=task.declined_emails,
    )


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(session: Session = Depends(get_session)) -> list[TaskRead]:
    tasks = session.exec(select(Task).order_by(Task.id.desc())).all()
    return [_to_read(task, session) for task in tasks]


def _load_pending(task_id: int, session: Session) -> Task:
    """Fetch a task, enforcing 404 (unknown) and 409 (not PENDING)."""
    task = session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status != TaskStatus.PENDING:
        raise HTTPException(status_code=409, detail="Task is not pending")
    return task


@router.post("/tasks/{task_id}/accept", response_model=TaskRead)
def accept_task(task_id: int, session: Session = Depends(get_session)) -> TaskRead:
    task = _load_pending(task_id, session)
    task.status = TaskStatus.ACCEPTED
    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task, session)


@router.post("/tasks/{task_id}/decline", response_model=TaskRead)
def decline_task(task_id: int, session: Session = Depends(get_session)) -> TaskRead:
    task = _load_pending(task_id, session)

    # Rule 2: record the decline and count it.
    task.declined_emails = task.declined_emails + [task.assigned_email]
    task.reassign_count += 1

    max_reassignments = get_settings().max_reassignments
    next_candidate = next(
        (
            c
            for c in task.candidates
            if c["developer_email"] not in task.declined_emails
        ),
        None,
    )

    # Rule 4: the cap forces UNASSIGNED even if an untried candidate remains.
    # Rule 3: otherwise reassign to the next candidate, or UNASSIGNED if none.
    if task.reassign_count >= max_reassignments or next_candidate is None:
        task.status = TaskStatus.UNASSIGNED
        task.assigned_email = None
        task.score = None
        task.matched_modules = []
    else:
        task.assigned_email = next_candidate["developer_email"]
        task.score = next_candidate["score"]
        task.matched_modules = next_candidate["matched_modules"]

    session.add(task)
    session.commit()
    session.refresh(task)
    return _to_read(task, session)

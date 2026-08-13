"""GET /api/tasks — read-only list of all tasks, newest first."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.bug import Bug
from app.models.task import Task
from app.schemas.task import TaskRead

router = APIRouter(prefix="/api", tags=["tasks"])


@router.get("/tasks", response_model=list[TaskRead])
def list_tasks(session: Session = Depends(get_session)) -> list[TaskRead]:
    tasks = session.exec(select(Task).order_by(Task.id.desc())).all()
    out: list[TaskRead] = []
    for task in tasks:
        bug = session.get(Bug, task.bug_id)
        out.append(
            TaskRead(
                task_id=task.id,
                bug_id=task.bug_id,
                title=bug.title if bug else "",
                module=bug.module if bug else None,
                assigned_email=task.assigned_email,
                score=task.score,
                matched_modules=task.matched_modules,
                status=task.status,
            )
        )
    return out

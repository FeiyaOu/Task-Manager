"""Repo endpoints: POST /api/repo/refresh and GET /api/repo/status."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.config_state import ConfigState
from app.models.expertise import Expertise
from app.services.git_analyzer import NotAGitRepositoryError, head_commit
from app.services.repo_ingest import ingest_repo

router = APIRouter(prefix="/api/repo", tags=["repo"])


@router.post("/refresh")
def refresh_repo(
    request: Request,
    days: int | None = None,
    session: Session = Depends(get_session),
) -> dict[str, int]:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    # A date window is a bounded scan (ignore the incremental commit cursor);
    # otherwise refresh incrementally from the last analyzed commit.
    since_date = now - timedelta(days=days) if days is not None else None
    state = session.exec(select(ConfigState)).first()
    since_commit = None if since_date else (state.last_analyzed_commit_hash if state else None)
    try:
        result = ingest_repo(
            session,
            settings.repo_path,
            now=now,
            lambda_decay=settings.decay_lambda,
            since_commit=since_commit,
            since_date=since_date,
            module_depth=settings.module_depth,
        )
    except NotAGitRepositoryError as exc:
        raise HTTPException(
            status_code=400,
            detail=(
                f"REPO_PATH is not a valid git repository: {settings.repo_path or '(unset)'}"
            ),
        ) from exc
    request.app.state.expertise_cache.load(session)
    return result


@router.get("/status")
def repo_status(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    state = session.exec(select(ConfigState)).first()
    last = state.last_analyzed_commit_hash if state else None
    developers = session.exec(select(Expertise.developer_email).distinct()).all()
    modules = session.exec(select(Expertise.module_path).distinct()).all()
    head = head_commit(settings.repo_path)
    return {
        "repo_path": settings.repo_path,
        "last_analyzed_commit": last,
        "head_commit": head,
        # Stale = analyzed at least once but the repo has advanced past that point.
        "is_stale": bool(last and head and head != last),
        "developer_count": len(set(developers)),
        "module_count": len(set(modules)),
    }

"""Repo endpoints: POST /api/repo/refresh and GET /api/repo/status."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session, select

from app.config import get_settings
from app.database import get_session
from app.models.config_state import ConfigState
from app.models.expertise import Expertise
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
    result = ingest_repo(
        session,
        settings.repo_path,
        now=now,
        lambda_decay=settings.decay_lambda,
        since_commit=since_commit,
        since_date=since_date,
    )
    request.app.state.expertise_cache.load(session)
    return result


@router.get("/status")
def repo_status(session: Session = Depends(get_session)) -> dict:
    settings = get_settings()
    state = session.exec(select(ConfigState)).first()
    developers = session.exec(select(Expertise.developer_email).distinct()).all()
    modules = session.exec(select(Expertise.module_path).distinct()).all()
    return {
        "repo_path": settings.repo_path,
        "last_analyzed_commit": state.last_analyzed_commit_hash if state else None,
        "developer_count": len(set(developers)),
        "module_count": len(set(modules)),
    }

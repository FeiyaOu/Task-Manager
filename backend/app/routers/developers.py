"""GET /api/developers — developers with commit activity in a recency window (spec 06)."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.database import get_session
from app.models.commit import Commit

router = APIRouter(prefix="/api", tags=["developers"])


@router.get("/developers", response_model=list[str])
def list_developers(
    days: int | None = Query(default=None, ge=0),
    session: Session = Depends(get_session),
) -> list[str]:
    query = select(Commit.author_email).distinct()
    if days is not None:
        # committed_at is stored naive/UTC (SQLite drops tzinfo) — compare naive-to-naive.
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).replace(tzinfo=None)
        query = query.where(Commit.committed_at >= cutoff)
    return sorted(set(session.exec(query).all()))

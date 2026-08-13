"""POST /api/bugs — submit a bug, assign it, return the result."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.config import get_settings
from app.database import get_session
from app.schemas.bug import AssignmentResult, BugSubmit
from app.services.assignment import assign_bug

router = APIRouter(prefix="/api", tags=["bugs"])


@router.post("/bugs", response_model=AssignmentResult)
def submit_bug(
    bug: BugSubmit,
    request: Request,
    session: Session = Depends(get_session),
) -> AssignmentResult:
    cache = request.app.state.expertise_cache
    threshold = get_settings().assign_threshold
    return assign_bug(bug, session, cache.map, threshold=threshold)

"""GET /api/modules — unique module paths from the expertise table."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.expertise import Expertise

router = APIRouter(prefix="/api", tags=["modules"])


@router.get("/modules", response_model=list[str])
def list_modules(session: Session = Depends(get_session)) -> list[str]:
    rows = session.exec(select(Expertise.module_path).distinct()).all()
    return sorted(set(rows))

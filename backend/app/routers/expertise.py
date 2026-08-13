"""GET /api/expertise — browse the expertise map (who knows what, how well)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.expertise import Expertise
from app.schemas.expertise import ExpertiseRead

router = APIRouter(prefix="/api", tags=["expertise"])


@router.get("/expertise", response_model=list[ExpertiseRead])
def list_expertise(
    developer: str | None = None,
    module: str | None = None,
    session: Session = Depends(get_session),
) -> list[Expertise]:
    query = select(Expertise)
    if developer is not None:
        query = query.where(Expertise.developer_email == developer)
    if module is not None:
        query = query.where(Expertise.module_path == module)
    return session.exec(query.order_by(Expertise.score.desc())).all()

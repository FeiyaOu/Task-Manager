"""In-memory expertise cache (feature 05b).

Loads the Expertise table into the dict shape the matcher expects
(``author_email -> {module -> score}``) for fast runtime lookup.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.models.expertise import Expertise


class ExpertiseCache:
    def __init__(self) -> None:
        self._map: dict[str, dict[str, float]] = {}

    def load(self, session: Session) -> dict[str, dict[str, float]]:
        rows = session.exec(select(Expertise)).all()
        new_map: dict[str, dict[str, float]] = {}
        for row in rows:
            new_map.setdefault(row.developer_email, {})[row.module_path] = row.score
        self._map = new_map
        return self._map

    @property
    def map(self) -> dict[str, dict[str, float]]:
        return self._map

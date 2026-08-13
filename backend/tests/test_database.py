"""Tests for the database engine/session helpers (feature 05a)."""
from __future__ import annotations

from sqlmodel import Session, select

import app.database as database_module
from app.database import create_db_and_tables, get_session, make_engine
from app.models.bug import Bug


def test_create_db_and_tables_creates_schema():
    engine = make_engine("sqlite://")
    create_db_and_tables(engine)
    with Session(engine) as s:
        s.add(Bug(title="t", description="d"))
        s.commit()
        assert len(s.exec(select(Bug)).all()) == 1


def test_get_session_yields_session(monkeypatch):
    engine = make_engine("sqlite://")
    create_db_and_tables(engine)
    monkeypatch.setattr(database_module, "engine", engine)
    gen = get_session()
    session = next(gen)
    try:
        assert isinstance(session, Session)
    finally:
        gen.close()

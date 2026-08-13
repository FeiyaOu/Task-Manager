"""Tests for the repo ingest pipeline (feature 05b).

Ties git_analyzer + scoring into persistence: analyze -> save commits ->
recompute expertise -> update config_state. Reuses the temp-git-repo fixture.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from sqlmodel import select

from app.models.commit import Commit
from app.models.config_state import ConfigState
from app.models.expertise import Expertise
from app.services.repo_ingest import ingest_repo
from tests.conftest import FIXED_NOW, SeededCommit


def _repo(make_repo):
    return make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\nb\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=0,
                     files={"billing/pay.py": "x\n"}),
    ])


def test_ingest_persists_commits(db_session, make_repo):
    result = ingest_repo(db_session, _repo(make_repo), now=FIXED_NOW)
    assert result["new_commits"] == 2
    assert len(db_session.exec(select(Commit)).all()) == 2


def test_ingest_builds_expertise(db_session, make_repo):
    ingest_repo(db_session, _repo(make_repo), now=FIXED_NOW)
    rows = db_session.exec(select(Expertise)).all()
    by_dev = {(r.developer_email, r.module_path): r for r in rows}
    assert ("alice@x.com", "auth/") in by_dev
    assert ("bob@x.com", "billing/") in by_dev
    # Alice changed 2 lines today -> weight 1.0 -> score 2.0.
    assert by_dev[("alice@x.com", "auth/")].score == pytest.approx(2.0)


def test_ingest_reports_module_count(db_session, make_repo):
    result = ingest_repo(db_session, _repo(make_repo), now=FIXED_NOW)
    assert result["modules"] == 2


def test_ingest_updates_config_state(db_session, make_repo):
    ingest_repo(db_session, _repo(make_repo), now=FIXED_NOW)
    state = db_session.exec(select(ConfigState)).first()
    assert state is not None
    assert state.last_analyzed_commit_hash is not None


def test_incremental_no_new_commits_no_duplicates(db_session, make_repo):
    repo = _repo(make_repo)
    ingest_repo(db_session, repo, now=FIXED_NOW)
    last = db_session.exec(select(ConfigState)).first().last_analyzed_commit_hash

    second = ingest_repo(db_session, repo, now=FIXED_NOW, since_commit=last)
    assert second["new_commits"] == 0
    assert len(db_session.exec(select(Commit)).all()) == 2  # no duplicate rows


def test_empty_repo_ingest(db_session, empty_repo):
    result = ingest_repo(db_session, empty_repo, now=FIXED_NOW)
    assert result["new_commits"] == 0
    assert result["modules"] == 0


def test_since_date_limits_ingested_commits(db_session, make_repo):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=10,
                     files={"old/mod.py": "1\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=1,
                     files={"recent/mod.py": "1\n"}),
    ])
    result = ingest_repo(
        db_session, repo, now=FIXED_NOW, since_date=FIXED_NOW - timedelta(days=3)
    )
    assert result["new_commits"] == 1
    modules = {e.module_path for e in db_session.exec(select(Expertise)).all()}
    assert modules == {"recent/"}


def test_module_depth_threads_through(db_session, make_repo):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"Engine/Physics/x.cpp": "1\n",
                            "Engine/Audio/y.cpp": "1\n"}),
    ])
    ingest_repo(db_session, repo, now=FIXED_NOW, module_depth=2)
    modules = {e.module_path for e in db_session.exec(select(Expertise)).all()}
    assert modules == {"Engine/Physics/", "Engine/Audio/"}


def test_ingest_stores_commit_message(db_session, make_repo):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/x.py": "1\n"}, message="Fix billing rounding"),
    ])
    ingest_repo(db_session, repo, now=FIXED_NOW)
    commit = db_session.exec(select(Commit)).first()
    assert commit.message == "Fix billing rounding"

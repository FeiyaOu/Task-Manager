"""Tests for the TF-IDF module index (commit-message enrichment).

Proves that the words developers write in commit messages let a bug's text find
the right module even when the folder is named differently (billing -> payments/).
"""
from __future__ import annotations

from app.services.module_index import ModuleIndex
from app.services.repo_ingest import ingest_repo
from tests.conftest import FIXED_NOW, SeededCommit


def _repo(make_repo):
    return make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"payments/charge.py": "1\n"},
                     message="fix billing invoice calculation"),
        SeededCommit("Bob", "bob@x.com", days_ago=0,
                     files={"engine/render.py": "1\n"},
                     message="optimize rendering pipeline"),
    ])


def test_not_ready_before_build():
    assert ModuleIndex().is_ready is False


def test_empty_repo_not_ready(db_session, empty_repo):
    ingest_repo(db_session, empty_repo, now=FIXED_NOW)
    index = ModuleIndex()
    index.build(db_session)
    assert index.is_ready is False


def test_message_vocabulary_connects_to_module(db_session, make_repo):
    ingest_repo(db_session, _repo(make_repo), now=FIXED_NOW)
    index = ModuleIndex()
    index.build(db_session)
    assert index.is_ready

    rel = index.relevance("billing problem")
    # "billing" only appears in the payments/ commit message.
    assert rel.get("payments/", 0.0) > 0.0
    assert rel.get("payments/", 0.0) > rel.get("engine/", 0.0)


def test_relevance_uses_module_depth(db_session, make_repo):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"Engine/Physics/x.cpp": "1\n"},
                     message="collision solver"),
    ])
    ingest_repo(db_session, repo, now=FIXED_NOW, module_depth=2)
    index = ModuleIndex()
    index.build(db_session, module_depth=2)
    rel = index.relevance("collision")
    assert rel.get("Engine/Physics/", 0.0) > 0.0

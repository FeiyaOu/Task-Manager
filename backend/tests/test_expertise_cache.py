"""Tests for the in-memory expertise cache (feature 05b)."""
from __future__ import annotations

from app.services.expertise_cache import ExpertiseCache
from app.services.repo_ingest import ingest_repo
from tests.conftest import FIXED_NOW, SeededCommit


def test_cache_loads_map_from_db(db_session, make_repo):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\n"}),
    ])
    ingest_repo(db_session, repo, now=FIXED_NOW)

    cache = ExpertiseCache()
    m = cache.load(db_session)
    assert "auth/" in m["alice@x.com"]
    assert isinstance(m["alice@x.com"]["auth/"], float)


def test_cache_shape_matches_matcher_contract(db_session, make_repo):
    repo = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\n", "user/p.py": "b\n"}),
    ])
    ingest_repo(db_session, repo, now=FIXED_NOW)
    m = ExpertiseCache().load(db_session)
    # dict[email -> dict[module -> float]]
    assert set(m["alice@x.com"]) == {"auth/", "user/"}


def test_cache_empty_when_no_expertise(db_session):
    cache = ExpertiseCache()
    assert cache.load(db_session) == {}
    assert cache.map == {}

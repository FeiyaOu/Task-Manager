"""Tests for the matcher (feature 03).

Each test traces back to a numbered Rule or Edge case in
``spec/features/03-matcher.md``. The matcher is pure; inputs are built directly.
"""
from __future__ import annotations

import pytest

from app.services.matcher import BugInput, Candidate, rank_developers

EMAP = {
    "alice@x.com": {"auth/": 50.0, "user/": 10.0},
    "bob@x.com": {"billing/": 90.0},
    "carla@x.com": {"auth/": 20.0},
}


# Rule 1 + 2: returns a ranked list (not a winner), sorted by score descending.
def test_returns_ranked_list_desc():
    result = rank_developers(BugInput(module="auth/"), EMAP)
    assert isinstance(result, list)
    assert [c.developer_email for c in result] == ["alice@x.com", "carla@x.com"]
    scores = [c.score for c in result]
    assert scores == sorted(scores, reverse=True)


# Rule 3: when bug.module is provided, relevance is driven by that module's score.
def test_module_drives_relevance():
    result = rank_developers(BugInput(module="auth/"), EMAP)
    assert result[0].developer_email == "alice@x.com"  # 50 in auth/ > carla's 20
    assert result[0].score == pytest.approx(50.0)


# Rule 4: matched_modules contains every module that contributed to the score.
def test_matched_modules_lists_all_contributors():
    bug = BugInput(
        title="billing bug",
        description="user cannot pay in billing",
        module="auth/",
    )
    result = rank_developers(bug, EMAP)
    by_email = {c.developer_email: c for c in result}

    # alice: auth/ (selected) + user/ (keyword "user")
    assert by_email["alice@x.com"].matched_modules == ["auth/", "user/"]
    assert by_email["alice@x.com"].score == pytest.approx(60.0)
    # bob: matched purely via the "billing" keyword
    assert by_email["bob@x.com"].matched_modules == ["billing/"]


# Rule 5: ties are broken deterministically by developer_email ascending.
def test_ties_broken_by_email():
    tie_map = {
        "bob@x.com": {"auth/": 30.0},
        "alice@x.com": {"auth/": 30.0},
    }
    result = rank_developers(BugInput(module="auth/"), tie_map)
    assert [c.developer_email for c in result] == ["alice@x.com", "bob@x.com"]


# Rule 6: a developer with zero relevant expertise is excluded.
def test_irrelevant_developer_excluded():
    emap = {**EMAP, "dave@x.com": {"payments/": 100.0}}
    result = rank_developers(BugInput(module="auth/"), emap)
    assert "dave@x.com" not in {c.developer_email for c in result}


# Keyword-only matching (no module selected) still works.
def test_keyword_only_match():
    result = rank_developers(
        BugInput(description="fix the billing checkout"), EMAP
    )
    assert [c.developer_email for c in result] == ["bob@x.com"]
    assert result[0].matched_modules == ["billing/"]


# Candidate shape.
def test_candidate_shape():
    result = rank_developers(BugInput(module="auth/"), EMAP)
    c = result[0]
    assert isinstance(c, Candidate)
    assert isinstance(c.developer_email, str)
    assert isinstance(c.score, float)
    assert isinstance(c.matched_modules, list)


# Edge: empty expertise_map -> [].
def test_empty_expertise_map():
    assert rank_developers(BugInput(module="auth/"), {}) == []


# Edge: nothing matches the bug's module/keywords -> [].
def test_no_match_returns_empty():
    result = rank_developers(
        BugInput(description="quantum flux", module="nonexistent/"), EMAP
    )
    assert result == []


# Edge: empty description and no module -> [] (nothing to match on).
def test_no_module_no_description():
    assert rank_developers(BugInput(), EMAP) == []


# Multi-segment (deep) modules keyword-match on any path segment.
def test_deep_module_keyword_match():
    emap = {"dev@x.com": {"Engine/Physics/": 40.0}}
    # "physics" is a segment of the module path, not the whole name.
    result = rank_developers(BugInput(description="physics glitch"), emap)
    assert [c.developer_email for c in result] == ["dev@x.com"]
    assert result[0].matched_modules == ["Engine/Physics/"]

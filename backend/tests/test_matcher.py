"""Tests for the matcher (feature 03) — multi-module + coverage-weighted.

The matcher now takes a *list* of selected modules and rewards developers who
span more of them (coverage), not just whoever has the largest single number.
Score = sum(expertise over matched modules) * (1 + covered)/(1 + |selected|).
"""
from __future__ import annotations

import pytest

from app.services.matcher import BugInput, Candidate, rank_developers


# Empty expertise map -> [].
def test_empty_map():
    assert rank_developers(BugInput(modules=["auth/"]), {}) == []


# A single selected module matches the developer who has it.
def test_single_selected_module():
    emap = {"alice@x.com": {"auth/": 50.0}, "bob@x.com": {"billing/": 90.0}}
    result = rank_developers(BugInput(modules=["auth/"]), emap)
    assert [c.developer_email for c in result] == ["alice@x.com"]


# Coverage: a developer spanning ALL selected modules beats one who is huge in one.
def test_coverage_beats_magnitude():
    emap = {
        "spanner@x.com": {"auth/": 30.0, "payments/": 30.0, "api/": 30.0},
        "specialist@x.com": {"auth/": 90.0},
    }
    result = rank_developers(
        BugInput(modules=["auth/", "payments/", "api/"]), emap
    )
    assert result[0].developer_email == "spanner@x.com"
    # spanner: 90 * (1+3)/(1+3) = 90 ; specialist: 90 * (1+1)/(1+3) = 45
    by = {c.developer_email: c for c in result}
    assert by["spanner@x.com"].score == pytest.approx(90.0)
    assert by["specialist@x.com"].score == pytest.approx(45.0)


# Partial coverage lowers the score but does not eliminate (soft).
def test_partial_coverage_soft():
    emap = {"alice@x.com": {"auth/": 40.0}}
    result = rank_developers(BugInput(modules=["auth/", "payments/"]), emap)
    # covered 1 of 2 -> factor (1+1)/(1+2)=2/3 -> 40 * 2/3
    assert result[0].score == pytest.approx(40.0 * 2 / 3)


# No selection -> pure keyword matching against module paths (factor 1.0).
def test_keyword_only_no_selection():
    emap = {"alice@x.com": {"billing/": 90.0}}
    result = rank_developers(
        BugInput(description="fix the billing flow", modules=[]), emap
    )
    assert result[0].developer_email == "alice@x.com"
    assert result[0].score == pytest.approx(90.0)


# matched_modules lists selected + keyword-matched contributors.
def test_matched_modules_listed():
    emap = {"alice@x.com": {"auth/": 50.0, "billing/": 20.0}}
    bug = BugInput(description="billing issue", modules=["auth/"])
    result = rank_developers(bug, emap)
    assert result[0].matched_modules == ["auth/", "billing/"]


# Ties broken by developer_email ascending.
def test_tie_break_by_email():
    emap = {"bob@x.com": {"auth/": 30.0}, "alice@x.com": {"auth/": 30.0}}
    result = rank_developers(BugInput(modules=["auth/"]), emap)
    assert [c.developer_email for c in result] == ["alice@x.com", "bob@x.com"]


# A developer with zero relevant expertise is excluded.
def test_irrelevant_excluded():
    emap = {"alice@x.com": {"auth/": 50.0}, "dave@x.com": {"unrelated/": 99.0}}
    result = rank_developers(BugInput(modules=["auth/"]), emap)
    assert "dave@x.com" not in {c.developer_email for c in result}


# Candidate shape.
def test_candidate_shape():
    emap = {"alice@x.com": {"auth/": 50.0}}
    c = rank_developers(BugInput(modules=["auth/"]), emap)[0]
    assert isinstance(c, Candidate)
    assert isinstance(c.score, float)
    assert isinstance(c.matched_modules, list)


# Empty description and no modules -> [] (nothing to match on).
def test_nothing_to_match():
    emap = {"alice@x.com": {"auth/": 50.0}}
    assert rank_developers(BugInput(modules=[]), emap) == []


# module_relevance (TF-IDF) weights expertise by graded relevance.
def test_relevance_weighting():
    emap = {"alice@x.com": {"payments/": 100.0}}
    result = rank_developers(
        BugInput(description="billing", modules=[]),
        emap,
        module_relevance={"payments/": 0.5},
    )
    assert result[0].score == pytest.approx(50.0)  # 100 * 0.5


# A selected module always gets full weight, overriding relevance.
def test_selected_overrides_relevance():
    emap = {"alice@x.com": {"auth/": 40.0}}
    result = rank_developers(
        BugInput(modules=["auth/"]),
        emap,
        module_relevance={"auth/": 0.2},
    )
    assert result[0].score == pytest.approx(40.0)  # selected -> weight 1.0


# With relevance provided, a module of zero relevance does not match.
def test_zero_relevance_excluded():
    emap = {"alice@x.com": {"billing/": 90.0}}
    result = rank_developers(
        BugInput(description="unrelated", modules=[]),
        emap,
        module_relevance={},
    )
    assert result == []

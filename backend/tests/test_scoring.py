"""Tests for the scoring / expertise builder (feature 02).

Each test traces back to a numbered Rule or Edge case in
``spec/features/02-scoring.md``. Scoring is pure, so records are constructed
directly — no git repository required.
"""
from __future__ import annotations

import math
from datetime import timedelta

import pytest

from app.services.git_analyzer import CommitFileRecord
from app.services.scoring import ExpertiseCell, compute_expertise, module_of
from tests.conftest import FIXED_NOW


def rec(
    email: str,
    file_path: str,
    *,
    added: int = 0,
    deleted: int = 0,
    days_ago: int = 0,
    commit_hash: str = "c1",
    name: str = "Dev",
) -> CommitFileRecord:
    return CommitFileRecord(
        commit_hash=commit_hash,
        author_name=name,
        author_email=email,
        committed_at=FIXED_NOW - timedelta(days=days_ago),
        file_path=file_path,
        lines_added=added,
        lines_deleted=deleted,
    )


# Rule 1: a file path normalizes to its top-level directory + "/".
def test_module_is_top_level_dir():
    result = compute_expertise(
        [rec("a@x.com", "auth/sub/login.py", added=1)], now=FIXED_NOW
    )
    assert set(result["a@x.com"]) == {"auth/"}


# module_of respects a configurable depth.
def test_module_of_depth():
    assert module_of("Engine/Physics/Collision.cpp", depth=1) == "Engine/"
    assert module_of("Engine/Physics/Collision.cpp", depth=2) == "Engine/Physics/"
    # Fewer directories than depth -> use what is available.
    assert module_of("Engine/foo.cpp", depth=2) == "Engine/"
    # Root file stays "./" at any depth.
    assert module_of("README.md", depth=2) == "./"


# compute_expertise groups by the requested module depth.
def test_compute_expertise_respects_depth():
    records = [
        rec("a@x.com", "Engine/Physics/x.cpp", added=1),
        rec("a@x.com", "Engine/Audio/y.cpp", added=1),
    ]
    depth1 = compute_expertise(records, now=FIXED_NOW, module_depth=1)
    assert set(depth1["a@x.com"]) == {"Engine/"}

    depth2 = compute_expertise(records, now=FIXED_NOW, module_depth=2)
    assert set(depth2["a@x.com"]) == {"Engine/Physics/", "Engine/Audio/"}


# Rule 2: a file at repo root normalizes to module "./".
def test_root_file_module_is_dot_slash():
    result = compute_expertise(
        [rec("a@x.com", "README.md", added=1)], now=FIXED_NOW
    )
    assert set(result["a@x.com"]) == {"./"}


# Rule 3: lines_changed = lines_added + lines_deleted.
def test_lines_changed_is_added_plus_deleted():
    # committed today -> weight 1.0, so score == lines_changed.
    result = compute_expertise(
        [rec("a@x.com", "auth/x.py", added=10, deleted=5, days_ago=0)],
        now=FIXED_NOW,
    )
    assert result["a@x.com"]["auth/"].score == pytest.approx(15.0)


# Rule 4 + edge: days_ago = 0 -> weight 1.0.
def test_today_commit_weight_is_one():
    result = compute_expertise(
        [rec("a@x.com", "auth/x.py", added=8, days_ago=0)], now=FIXED_NOW
    )
    assert result["a@x.com"]["auth/"].score == pytest.approx(8.0)


# Rule 5: score sums lines_changed * recency_weight over all matching records.
def test_score_sums_over_records():
    records = [
        rec("a@x.com", "auth/x.py", added=10, days_ago=0, commit_hash="c1"),
        rec("a@x.com", "auth/y.py", added=5, days_ago=0, commit_hash="c2"),
    ]
    result = compute_expertise(records, now=FIXED_NOW)
    assert result["a@x.com"]["auth/"].score == pytest.approx(15.0)


# Rule 6: a commit 100 days old contributes lines_changed * 0.3679 (+/-1e-3).
def test_recency_decay_100_days():
    result = compute_expertise(
        [rec("a@x.com", "auth/x.py", added=1, days_ago=100)],
        now=FIXED_NOW,
        lambda_decay=0.01,
    )
    assert result["a@x.com"]["auth/"].score == pytest.approx(
        math.exp(-1.0), abs=1e-3
    )


# Rule 7: commit_count is the number of DISTINCT commit hashes for the pair.
def test_commit_count_distinct_commits():
    # One commit touching two files in the same module counts once.
    records = [
        rec("a@x.com", "auth/x.py", added=1, commit_hash="same"),
        rec("a@x.com", "auth/y.py", added=1, commit_hash="same"),
    ]
    result = compute_expertise(records, now=FIXED_NOW)
    assert result["a@x.com"]["auth/"].commit_count == 1


def test_commit_count_counts_multiple_commits():
    records = [
        rec("a@x.com", "auth/x.py", added=1, commit_hash="c1"),
        rec("a@x.com", "auth/y.py", added=1, commit_hash="c2"),
    ]
    result = compute_expertise(records, now=FIXED_NOW)
    assert result["a@x.com"]["auth/"].commit_count == 2


# Multiple developers and modules are kept separate.
def test_developers_and_modules_are_separated():
    records = [
        rec("a@x.com", "auth/x.py", added=1, commit_hash="c1"),
        rec("a@x.com", "user/y.py", added=1, commit_hash="c2"),
        rec("b@x.com", "billing/z.py", added=1, commit_hash="c3"),
    ]
    result = compute_expertise(records, now=FIXED_NOW)
    assert set(result) == {"a@x.com", "b@x.com"}
    assert set(result["a@x.com"]) == {"auth/", "user/"}
    assert set(result["b@x.com"]) == {"billing/"}


# Rule 8: scoring is pure — recomputing from the same records is identical
# (no accumulation on top of stale state).
def test_recompute_is_pure():
    records = [rec("a@x.com", "auth/x.py", added=3, days_ago=10)]
    first = compute_expertise(records, now=FIXED_NOW)
    second = compute_expertise(records, now=FIXED_NOW)
    assert first["a@x.com"]["auth/"].score == second["a@x.com"]["auth/"].score


# Output shape: cells are ExpertiseCell with score:float, commit_count:int.
def test_output_cell_type():
    result = compute_expertise(
        [rec("a@x.com", "auth/x.py", added=1)], now=FIXED_NOW
    )
    cell = result["a@x.com"]["auth/"]
    assert isinstance(cell, ExpertiseCell)
    assert isinstance(cell.score, float)
    assert isinstance(cell.commit_count, int)


# Edge: empty records -> empty dict.
def test_empty_records_returns_empty_dict():
    assert compute_expertise([], now=FIXED_NOW) == {}

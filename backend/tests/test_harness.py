"""Smoke test: confirms the pytest harness and the temp-git-repo fixture work.

This is Phase 0's green checkpoint before feature TDD begins. It does NOT test any
production code yet — it only proves the fixture can build a repo with real commits.
"""
from git import Repo

from tests.conftest import FIXED_NOW, SeededCommit


def test_harness_runs():
    assert FIXED_NOW.year == 2026


def test_make_repo_creates_commits(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "print('hi')\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=10,
                     files={"billing/checkout.py": "x = 1\n"}),
    ])
    commits = list(Repo(repo_path).iter_commits())
    assert len(commits) == 2
    emails = {c.author.email for c in commits}
    assert emails == {"alice@x.com", "bob@x.com"}


def test_empty_repo_has_no_commits(empty_repo):
    repo = Repo(empty_repo)
    # A freshly initialized repo has an unborn HEAD (no commits yet), so
    # iter_commits() would fail to resolve a ref. is_valid() is the correct
    # way to detect the "no commits" state.
    assert repo.head.is_valid() is False

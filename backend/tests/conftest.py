"""Shared pytest fixtures.

The temp-git-repo fixture is the backbone of the suite: it builds a throwaway
git repository with commits at known authors, dates, files, and line counts so
that git-analyzer and scoring tests can assert exact values deterministically.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone

import pytest

# Make the test suite hermetic: ignore the developer's global/system git config
# so commits use only the fixture's actors and dates. This also avoids sandboxed
# environments where ~/.gitconfig is not readable. These must be set BEFORE
# importing `git`, because GitPython runs `git version` at import time.
os.environ.setdefault("GIT_CONFIG_GLOBAL", os.devnull)
os.environ.setdefault("GIT_CONFIG_SYSTEM", os.devnull)

from git import Actor, Repo  # noqa: E402  (import after env setup, intentional)


# A fixed reference "now" so recency-decay math is reproducible across runs.
FIXED_NOW = datetime(2026, 8, 12, tzinfo=timezone.utc)


@dataclass
class SeededCommit:
    """Description of one commit to create in the fixture repo."""
    author_name: str
    author_email: str
    days_ago: int
    files: dict[str, str]  # relative path -> file content


def _commit_datetime(days_ago: int) -> str:
    """Return git's internal date format: ``<unix-timestamp> <utc-offset>``.

    GitPython's ``parse_date`` cannot parse an ISO-8601 string whose offset
    uses a colon (e.g. ``+00:00``); its ``strptime`` call chokes on the
    remaining ``+00:00``. The unambiguous ``"<timestamp> +0000"`` form is
    parsed directly and keeps dates deterministic.
    """
    ts = int(FIXED_NOW.timestamp() - days_ago * 86400)
    return f"{ts} +0000"


@pytest.fixture
def make_repo(tmp_path):
    """Factory that builds a git repo from a list of SeededCommit specs.

    Usage:
        repo_path = make_repo([
            SeededCommit("Alice", "alice@x.com", days_ago=0,
                         files={"auth/login.py": "print('hi')\\n"}),
        ])
    Returns the absolute path to the repository.
    """
    def _build(commits: list[SeededCommit], name: str = "sample-repo") -> str:
        repo_dir = tmp_path / name
        repo_dir.mkdir()
        repo = Repo.init(repo_dir)

        for spec in commits:
            for rel_path, content in spec.files.items():
                file_path = repo_dir / rel_path
                file_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.write_text(content)
                repo.index.add([str(file_path)])

            actor = Actor(spec.author_name, spec.author_email)
            date = _commit_datetime(spec.days_ago)
            repo.index.commit(
                f"commit by {spec.author_name} ({spec.days_ago}d ago)",
                author=actor,
                committer=actor,
                author_date=date,
                commit_date=date,
            )
        return str(repo_dir)

    return _build


@pytest.fixture
def empty_repo(tmp_path):
    """An initialized git repo with zero commits."""
    repo_dir = tmp_path / "empty-repo"
    repo_dir.mkdir()
    Repo.init(repo_dir)
    return str(repo_dir)


@pytest.fixture
def non_git_dir(tmp_path):
    """A plain directory that is not a git repository."""
    plain = tmp_path / "plain"
    plain.mkdir()
    return str(plain)


@pytest.fixture
def db_session():
    """An in-memory SQLite session with all app tables created."""
    from sqlmodel import Session, create_engine

    from app.database import create_db_and_tables

    engine = create_engine("sqlite://", connect_args={"check_same_thread": False})
    create_db_and_tables(engine)
    with Session(engine) as session:
        yield session

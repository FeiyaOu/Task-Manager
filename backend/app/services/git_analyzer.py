"""Git analyzer (feature 01).

Reads a local git repository's history and produces raw commit-file records —
one per (commit x file) pair. Knows nothing about scoring or persistence.

Contract: see ``spec/features/01-git-analyzer.md``.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from git import Repo
from git.exc import InvalidGitRepositoryError, NoSuchPathError
from gitdb.exc import BadName, BadObject


class NotAGitRepositoryError(Exception):
    """Raised when ``repo_path`` is not a valid git repository."""


class UnknownCommitError(Exception):
    """Raised when ``since_commit`` cannot be found in the repository."""


@dataclass
class CommitFileRecord:
    commit_hash: str
    author_name: str
    author_email: str
    committed_at: datetime  # timezone-aware, UTC
    file_path: str
    lines_added: int
    lines_deleted: int


def analyze_repository(
    repo_path: str, since_commit: str | None = None
) -> list[CommitFileRecord]:
    """Return commit-file records for ``repo_path``, oldest to newest.

    When ``since_commit`` is given, only commits *after* it are returned.
    Merge commits (2+ parents) are skipped.
    """
    try:
        repo = Repo(repo_path)
    except (InvalidGitRepositoryError, NoSuchPathError) as exc:
        raise NotAGitRepositoryError(str(repo_path)) from exc

    if not repo.head.is_valid():  # no commits yet
        return []

    if since_commit is None:
        commits = list(repo.iter_commits())
    else:
        try:
            repo.commit(since_commit)
        except (BadName, BadObject, ValueError) as exc:
            raise UnknownCommitError(str(since_commit)) from exc
        commits = list(repo.iter_commits(f"{since_commit}..HEAD"))

    commits = [c for c in commits if len(c.parents) < 2]
    commits.sort(key=lambda c: c.committed_datetime)

    records: list[CommitFileRecord] = []
    for commit in commits:
        committed_at = commit.committed_datetime.astimezone(timezone.utc)
        for file_path, stat in commit.stats.files.items():
            records.append(
                CommitFileRecord(
                    commit_hash=commit.hexsha,
                    author_name=commit.author.name,
                    author_email=commit.author.email,
                    committed_at=committed_at,
                    file_path=file_path,
                    lines_added=int(stat.get("insertions", 0)),
                    lines_deleted=int(stat.get("deletions", 0)),
                )
            )
    return records

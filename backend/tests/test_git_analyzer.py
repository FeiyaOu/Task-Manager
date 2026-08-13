"""Tests for the git analyzer (feature 01).

Each test traces back to a numbered Rule or Edge case in
``spec/features/01-git-analyzer.md``. No production code exists yet — these are
the TDD red step.
"""
from __future__ import annotations

from datetime import timedelta, timezone

import pytest
from git import Actor, Repo

from app.services.git_analyzer import (
    CommitFileRecord,
    NotAGitRepositoryError,
    UnknownCommitError,
    analyze_repository,
)
from tests.conftest import FIXED_NOW, SeededCommit


def _by_path(records: list[CommitFileRecord]) -> dict[str, CommitFileRecord]:
    return {r.file_path: r for r in records}


# Rule 1: a commit touching N files emits exactly N records.
def test_one_record_per_file(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\n", "auth/utils.py": "b\n"}),
    ])
    records = analyze_repository(repo_path)
    assert len(records) == 2
    assert {r.file_path for r in records} == {"auth/login.py", "auth/utils.py"}


# Rule 2: author_email comes from the commit author.
def test_author_email_is_used(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\n"}),
    ])
    records = analyze_repository(repo_path)
    assert records[0].author_email == "alice@x.com"
    assert records[0].author_name == "Alice"


# Rule 3: committed_at is timezone-aware and normalized to UTC.
def test_committed_at_is_utc_aware(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"auth/login.py": "a\n"}),
    ])
    record = analyze_repository(repo_path)[0]
    assert record.committed_at.tzinfo is not None
    assert record.committed_at.utcoffset() == timezone.utc.utcoffset(None)


# Rule 4: merge commits (2+ parents) are skipped.
def test_merge_commits_are_skipped(tmp_path):
    repo_dir = tmp_path / "merge-repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    actor = Actor("Alice", "alice@x.com")

    def commit(rel_path: str, msg: str) -> str:
        (repo_dir / rel_path).parent.mkdir(parents=True, exist_ok=True)
        (repo_dir / rel_path).write_text("x\n")
        repo.index.add([str(repo_dir / rel_path)])
        return repo.index.commit(msg, author=actor, committer=actor).hexsha

    commit("base.py", "base")
    main_branch = repo.active_branch.name
    repo.git.checkout("-b", "feature")
    commit("feature_file.py", "feature work")
    repo.git.checkout(main_branch)
    commit("main_file.py", "main work")
    merge_sha = repo.git.merge("feature", "--no-ff", "-m", "merge").split()[-1]

    records = analyze_repository(str(repo_dir))
    hashes = {r.commit_hash for r in records}
    # The merge commit contributes nothing; the branch work is still recorded.
    assert repo.head.commit.hexsha not in hashes  # HEAD is the merge commit
    assert "feature_file.py" in {r.file_path for r in records}
    assert "main_file.py" in {r.file_path for r in records}
    assert merge_sha  # sanity: a merge commit was actually created


# Rule 5: binary files yield a record with 0 lines added/deleted.
def test_binary_file_has_zero_line_counts(tmp_path):
    repo_dir = tmp_path / "binary-repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    actor = Actor("Alice", "alice@x.com")
    (repo_dir / "image.bin").write_bytes(bytes([0, 1, 2, 0, 255, 0, 42]))
    repo.index.add([str(repo_dir / "image.bin")])
    repo.index.commit("add binary", author=actor, committer=actor)

    record = _by_path(analyze_repository(str(repo_dir)))["image.bin"]
    assert record.lines_added == 0
    assert record.lines_deleted == 0


# Rule 6: since_commit excludes commits up to and including it.
def test_since_commit_excludes_older_and_itself(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=30,
                     files={"a.py": "1\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=20,
                     files={"b.py": "1\n"}),
        SeededCommit("Carla", "carla@x.com", days_ago=10,
                     files={"c.py": "1\n"}),
    ])
    full = analyze_repository(repo_path)
    middle_hash = _by_path(full)["b.py"].commit_hash

    newer = analyze_repository(repo_path, since_commit=middle_hash)
    paths = {r.file_path for r in newer}
    assert paths == {"c.py"}  # only the commit after b.py


# Rule 7: results are ordered oldest -> newest by committed_at.
def test_records_ordered_oldest_to_newest(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=10,
                     files={"a.py": "1\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=30,
                     files={"b.py": "1\n"}),
        SeededCommit("Carla", "carla@x.com", days_ago=0,
                     files={"c.py": "1\n"}),
    ])
    records = analyze_repository(repo_path)
    times = [r.committed_at for r in records]
    assert times == sorted(times)
    assert records[0].file_path == "b.py"   # 30 days ago = oldest
    assert records[-1].file_path == "c.py"  # today = newest


# Rule 1 + line counting: added/deleted counts are captured per file.
def test_line_counts_are_captured(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"a.py": "l1\nl2\nl3\n"}),
    ])
    record = analyze_repository(repo_path)[0]
    assert record.lines_added == 3
    assert record.lines_deleted == 0


# Edge: empty repository -> [].
def test_empty_repo_returns_empty(empty_repo):
    assert analyze_repository(empty_repo) == []


# Edge: not a git repo -> NotAGitRepositoryError.
def test_non_git_dir_raises(non_git_dir):
    with pytest.raises(NotAGitRepositoryError):
        analyze_repository(non_git_dir)


# Edge: unknown since_commit -> UnknownCommitError.
def test_unknown_since_commit_raises(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=0,
                     files={"a.py": "1\n"}),
    ])
    with pytest.raises(UnknownCommitError):
        analyze_repository(repo_path, since_commit="deadbeef" * 5)


# Edge: a commit that only deletes a file -> one record for the deleted path.
def test_delete_only_commit(tmp_path):
    repo_dir = tmp_path / "delete-repo"
    repo_dir.mkdir()
    repo = Repo.init(repo_dir)
    actor = Actor("Alice", "alice@x.com")
    target = repo_dir / "gone.py"
    target.write_text("l1\nl2\n")
    repo.index.add([str(target)])
    repo.index.commit("add", author=actor, committer=actor)
    repo.index.remove([str(target)], working_tree=True)
    del_sha = repo.index.commit("delete", author=actor, committer=actor).hexsha

    records = analyze_repository(str(repo_dir))
    del_records = [r for r in records if r.commit_hash == del_sha]
    assert len(del_records) == 1
    assert del_records[0].file_path == "gone.py"
    assert del_records[0].lines_deleted == 2
    assert del_records[0].lines_added == 0


# since_date: only commits at/after the cutoff are returned.
def test_since_date_keeps_only_recent(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=10,
                     files={"old.py": "1\n"}),
        SeededCommit("Bob", "bob@x.com", days_ago=1,
                     files={"recent.py": "1\n"}),
    ])
    cutoff = FIXED_NOW - timedelta(days=3)
    records = analyze_repository(repo_path, since_date=cutoff)
    assert {r.file_path for r in records} == {"recent.py"}


# since_date newer than every commit -> [].
def test_since_date_excludes_all(make_repo):
    repo_path = make_repo([
        SeededCommit("Alice", "alice@x.com", days_ago=10,
                     files={"old.py": "1\n"}),
    ])
    records = analyze_repository(repo_path, since_date=FIXED_NOW + timedelta(days=1))
    assert records == []

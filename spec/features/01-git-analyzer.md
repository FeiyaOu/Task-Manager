# Feature: Git Analyzer

## Purpose
Read a local git repository's history and produce raw commit-file records.

## Inputs
- `repo_path: str` — absolute path to a local git repository.
- `since_commit: str | None` — optional commit hash; only process commits *after* it
  (incremental refresh). `None` means process full history.
- `since_date: datetime | None` — optional time cutoff; only process commits whose
  `committed_at` is at or after this time. Combinable with `since_commit`.

## Outputs
- `list[CommitFileRecord]` where each record has:
  - `commit_hash: str`
  - `author_name: str`
  - `author_email: str`   (the developer identifier)
  - `committed_at: datetime`  (timezone-aware, UTC)
  - `file_path: str`
  - `lines_added: int`
  - `lines_deleted: int`
- One record **per (commit × file)** pair.

## Rules
1. For a commit touching N files, emit exactly N records.
2. `author_email` is taken from the commit author (not committer).
3. `committed_at` is timezone-aware and normalized to UTC.
4. Merge commits (2+ parents) are skipped.
5. Binary files yield a record with `lines_added = 0` and `lines_deleted = 0`.
6. When `since_commit` is provided, commits up to and including it are excluded;
   only newer commits are returned.
7. Results are ordered oldest → newest by `committed_at`.
8. When `since_date` is provided, only commits with `committed_at >= since_date` are
   returned (a git `--after` hint bounds the walk; a Python filter enforces exactness).

## Edge cases
- Empty repository (no commits) → return `[]`.
- `repo_path` is not a git repo → raise `NotAGitRepositoryError`.
- `since_commit` not found in history → raise `UnknownCommitError`.
- A commit that only deletes a file → one record for the deleted path.

## Out of scope
- Writing to the database (a separate persistence step consumes these records).
- Score computation (see `02-scoring.md`).

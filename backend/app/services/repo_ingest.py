"""Repo ingest pipeline (feature 05b).

Orchestrates the analyze -> persist -> score -> persist flow:
1. read new commits from git (optionally since the last analyzed commit),
2. persist them as Commit rows,
3. recompute expertise from scratch over ALL persisted commits,
4. rewrite the Expertise table and update ConfigState.

Recomputing from all commits (not just the new ones) keeps recency-weighted
scores correct, as required by the scoring spec.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import Session, select

from app.models.commit import Commit
from app.models.config_state import ConfigState
from app.models.expertise import Expertise
from app.services.git_analyzer import CommitFileRecord, analyze_repository
from app.services.scoring import DEFAULT_LAMBDA, compute_expertise


def _as_aware(dt: datetime) -> datetime:
    # SQLite loses tzinfo; treat stored timestamps as UTC for scoring math.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def ingest_repo(
    session: Session,
    repo_path: str,
    now: datetime,
    lambda_decay: float = DEFAULT_LAMBDA,
    since_commit: str | None = None,
    since_date: datetime | None = None,
) -> dict[str, int]:
    records = analyze_repository(repo_path, since_commit, since_date)
    # Idempotency guard: never insert a (commit, file) pair already persisted.
    existing = set(session.exec(select(Commit.commit_hash)).all())
    new_records = [r for r in records if r.commit_hash not in existing]
    for r in new_records:
        session.add(
            Commit(
                commit_hash=r.commit_hash,
                author_email=r.author_email,
                file_path=r.file_path,
                lines_added=r.lines_added,
                lines_deleted=r.lines_deleted,
                committed_at=r.committed_at,
            )
        )
    session.commit()
    new_commits = len({r.commit_hash for r in new_records})

    # Recompute expertise from scratch over every persisted commit.
    all_commits = session.exec(select(Commit)).all()
    all_records = [
        CommitFileRecord(
            commit_hash=c.commit_hash,
            author_name="",
            author_email=c.author_email,
            committed_at=_as_aware(c.committed_at),
            file_path=c.file_path,
            lines_added=c.lines_added,
            lines_deleted=c.lines_deleted,
        )
        for c in all_commits
    ]
    expertise = compute_expertise(all_records, now=now, lambda_decay=lambda_decay)

    for row in session.exec(select(Expertise)).all():
        session.delete(row)
    session.commit()
    for email, modules in expertise.items():
        for module, cell in modules.items():
            session.add(
                Expertise(
                    developer_email=email,
                    module_path=module,
                    score=cell.score,
                    commit_count=cell.commit_count,
                    last_updated=now,
                )
            )
    session.commit()

    state = session.exec(select(ConfigState)).first()
    if state is None:
        state = ConfigState()
    if records:
        state.last_analyzed_commit_hash = records[-1].commit_hash
    session.add(state)
    session.commit()

    module_count = len({module for mods in expertise.values() for module in mods})
    return {"new_commits": new_commits, "modules": module_count}

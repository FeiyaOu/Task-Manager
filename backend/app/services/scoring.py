"""Scoring / expertise builder (feature 02).

Turns raw commit-file records into per-(developer, module) expertise scores
using recency-weighted line changes. Pure and deterministic: ``now`` is injected
so tests are reproducible.

Contract: see ``spec/features/02-scoring.md``.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime

from app.services.git_analyzer import CommitFileRecord

DEFAULT_LAMBDA = 0.01


@dataclass
class ExpertiseCell:
    score: float
    commit_count: int


def module_of(file_path: str) -> str:
    """Normalize a file path to its module = top-level directory + "/".

    A file at the repository root (no directory) maps to ``"./"``.
    """
    head, sep, _ = file_path.partition("/")
    return head + "/" if sep else "./"


def compute_expertise(
    records: list[CommitFileRecord],
    now: datetime,
    lambda_decay: float = DEFAULT_LAMBDA,
) -> dict[str, dict[str, ExpertiseCell]]:
    """Build ``author_email -> {module -> ExpertiseCell}`` from records.

    Score for a (developer, module) pair is
    ``sum(lines_changed * e^(-lambda_decay * days_ago))`` over matching records;
    ``commit_count`` is the number of distinct commit hashes for the pair.
    """
    result: dict[str, dict[str, ExpertiseCell]] = {}
    commit_hashes: dict[tuple[str, str], set[str]] = {}

    for r in records:
        module = module_of(r.file_path)
        days_ago = (now - r.committed_at).total_seconds() / 86400
        weight = math.exp(-lambda_decay * days_ago)
        lines_changed = r.lines_added + r.lines_deleted

        cell = result.setdefault(r.author_email, {}).setdefault(
            module, ExpertiseCell(score=0.0, commit_count=0)
        )
        cell.score += lines_changed * weight

        commit_hashes.setdefault((r.author_email, module), set()).add(r.commit_hash)

    for (email, module), hashes in commit_hashes.items():
        result[email][module].commit_count = len(hashes)

    return result

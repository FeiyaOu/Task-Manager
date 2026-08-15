"""Assignment orchestrator (feature 04).

Persists the bug, ranks developers, assigns the top candidate above threshold,
and persists the resulting task with its state. Synchronous: the full result is
returned in one call.

Contract: see ``spec/features/04-assignment.md``.
"""
from __future__ import annotations

from sqlmodel import Session

from app.models.bug import Bug
from app.models.enums import TaskStatus
from app.models.task import Task
from app.schemas.bug import AssignmentResult, BugSubmit, CandidateRead
from app.services.matcher import BugInput, rank_developers

DEFAULT_THRESHOLD = 0.0


def _parent_modules(module: str | None) -> list[str]:
    """Progressively broader parent modules, most specific first.

    ``Engine/Physics/Foo/`` -> [``Engine/Physics/``, ``Engine/``]. A top-level
    module (or none) has no parents.
    """
    if not module:
        return []
    parts = [p for p in module.strip("/").split("/") if p]
    return ["/".join(parts[:i]) + "/" for i in range(len(parts) - 1, 0, -1)]


def assign_bug(
    bug: BugSubmit,
    session: Session,
    expertise_map: dict[str, dict[str, float]],
    threshold: float = DEFAULT_THRESHOLD,
    broaden_threshold: float = DEFAULT_THRESHOLD,
    text_threshold: float = DEFAULT_THRESHOLD,
    module_relevance: dict[str, float] | None = None,
) -> AssignmentResult:
    # Rule 1: persist the bug before matching.
    bug_row = Bug(
        title=bug.title,
        description=bug.description,
        modules=bug.modules,
        severity=bug.severity,
    )
    session.add(bug_row)
    session.commit()
    session.refresh(bug_row)

    def rank(modules: list[str]):
        return rank_developers(
            BugInput(title=bug.title, description=bug.description, modules=modules),
            expertise_map,
            module_relevance=module_relevance,
        )

    # Tiered fallback: module-scoped -> broaden up the path -> text-only.
    # First tier whose top score clears its gate wins.
    primary = rank(bug.modules)
    tiers: list[tuple[str, list, float]] = [("module", primary, threshold)]
    broadened = sorted({p for m in bug.modules for p in _parent_modules(m)})
    if broadened:
        tiers.append(("broadened", rank(broadened), broaden_threshold))
    tiers.append(("text", rank([]), text_threshold))

    chosen = None
    match_tier = "unassigned"
    ranked = primary
    for tier_name, tier_ranked, gate in tiers:
        if tier_ranked and tier_ranked[0].score >= gate:
            chosen = tier_ranked[0]
            match_tier = tier_name
            ranked = tier_ranked
            break

    if chosen is not None:
        status = TaskStatus.PENDING
        assigned_email = chosen.developer_email
        score = chosen.score
        matched_modules = chosen.matched_modules
    else:
        # Tier 3: nothing cleared a gate. Record the best near-miss for triage.
        status = TaskStatus.UNASSIGNED
        assigned_email = None
        near_miss = primary[0] if primary else None
        score = near_miss.score if near_miss else None
        matched_modules = near_miss.matched_modules if near_miss else []

    # Snapshot the winning tier's ranked list so a later decline can reassign.
    candidates = [
        {
            "developer_email": c.developer_email,
            "score": c.score,
            "matched_modules": c.matched_modules,
        }
        for c in ranked
    ]

    # Persist the task with state fields and reassign_count = 0.
    task_row = Task(
        bug_id=bug_row.id,
        assigned_email=assigned_email,
        status=status,
        score=score,
        matched_modules=matched_modules,
        reassign_count=0,
        match_tier=match_tier,
        candidates=candidates,
        declined_emails=[],
    )
    session.add(task_row)
    session.commit()
    session.refresh(task_row)

    return AssignmentResult(
        bug_id=bug_row.id,
        task_id=task_row.id,
        assigned_email=assigned_email,
        score=score,
        matched_modules=matched_modules,
        status=status,
        match_tier=match_tier,
        candidates=[
            CandidateRead(
                developer_email=c.developer_email,
                score=c.score,
                matched_modules=c.matched_modules,
            )
            for c in ranked
        ],
    )

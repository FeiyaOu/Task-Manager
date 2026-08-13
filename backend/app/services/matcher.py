"""Matcher (feature 03).

Given a bug and the expertise map, return developers ranked best -> worst, each
with a score and the modules that explain the match. Returns a ranked *list*
(never a single winner) so extensions like reassignment can use the next-best.

Contract: see ``spec/features/03-matcher.md``. The matching heuristic may evolve;
the ranked-list contract is fixed.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class BugInput:
    title: str = ""
    description: str = ""
    module: str | None = None


@dataclass
class Candidate:
    developer_email: str
    score: float
    matched_modules: list[str] = field(default_factory=list)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def rank_developers(
    bug: BugInput, expertise_map: dict[str, dict[str, float]]
) -> list[Candidate]:
    """Rank developers best -> worst for ``bug``.

    A developer's relevant modules are the selected module (``bug.module``) plus
    any module whose name appears as a keyword in the bug's title/description.
    Score is the sum of that developer's expertise across those modules.
    """
    selected = (bug.module or "").strip()
    tokens = _tokenize(f"{bug.title} {bug.description}")

    candidates: list[Candidate] = []
    for email, modules in expertise_map.items():
        matched = {
            module: score
            for module, score in modules.items()
            if (selected and module == selected) or (_tokenize(module) & tokens)
        }
        total = sum(matched.values())
        if not matched or total <= 0:
            continue
        candidates.append(
            Candidate(
                developer_email=email,
                score=float(total),
                matched_modules=sorted(matched),
            )
        )

    candidates.sort(key=lambda c: (-c.score, c.developer_email))
    return candidates

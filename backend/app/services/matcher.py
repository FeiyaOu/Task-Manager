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
    modules: list[str] = field(default_factory=list)


@dataclass
class Candidate:
    developer_email: str
    score: float
    matched_modules: list[str] = field(default_factory=list)


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def rank_developers(
    bug: BugInput,
    expertise_map: dict[str, dict[str, float]],
    module_relevance: dict[str, float] | None = None,
) -> list[Candidate]:
    """Rank developers best -> worst for ``bug``.

    A module's weight is 1.0 if the user selected it. Otherwise, if
    ``module_relevance`` is provided (TF-IDF cosine of the bug text vs. each
    module's commit-message corpus), that graded relevance is the weight; when
    it is ``None`` we fall back to binary path-token keyword overlap.

    Score sums ``expertise * weight`` over matched modules, then applies a soft
    coverage factor ``(1 + covered)/(1 + |selected|)`` that rewards developers
    who span more of the selected modules. With no selection the factor is 1.0.
    """
    selected = {m for m in (bug.modules or []) if m}
    tokens = _tokenize(f"{bug.title} {bug.description}")

    def weight(module: str) -> float:
        if module in selected:
            return 1.0
        if module_relevance is not None:
            return module_relevance.get(module, 0.0)
        return 1.0 if (_tokenize(module) & tokens) else 0.0

    candidates: list[Candidate] = []
    for email, modules in expertise_map.items():
        matched = {
            module: score * w
            for module, score in modules.items()
            if (w := weight(module)) > 0
        }
        total = sum(matched.values())
        if not matched or total <= 0:
            continue

        if selected:
            covered = sum(1 for m in selected if modules.get(m, 0.0) > 0)
            coverage = (1 + covered) / (1 + len(selected))
        else:
            coverage = 1.0

        candidates.append(
            Candidate(
                developer_email=email,
                score=float(total) * coverage,
                matched_modules=sorted(matched),
            )
        )

    candidates.sort(key=lambda c: (-c.score, c.developer_email))
    return candidates

# Feature: Matcher

## Purpose
Given a bug report and the expertise map, return developers ranked from best to worst
match, each with a score and the reasons (matched modules).

This is the single most important function for the interview extensions
(accept/decline needs "next-best"; workload balancing re-ranks; "explain" needs reasons).

## Inputs
- `bug: BugInput` with at least:
  - `title: str`
  - `description: str`
  - `module: str | None`   (chosen from the dropdown; may be empty)
- `expertise_map: dict[str, dict[str, float]]` — `author_email -> {module -> score}`.

## Outputs
- `list[Candidate]`, ordered best → worst. Each `Candidate`:
  - `developer_email: str`
  - `score: float`
  - `matched_modules: list[str]`   (why this developer matched)

## Rules
1. Return a **ranked list**, never a single winner. `result[0]` is the top match;
   `result[1]` is the next-best (used for reassignment).
2. The list is sorted by `score` descending.
3. When `bug.module` is provided, a developer's relevance is driven primarily by their
   expertise score in that module.
4. `matched_modules` contains every module that contributed to a developer's score.
   Keyword matching tokenizes the **full module path** (e.g. `Engine/Physics/` yields
   `engine`, `physics`), so a bug mentioning any path segment matches that module.
5. Ties (equal score) are broken deterministically by `developer_email` ascending,
   so ordering is reproducible in tests.
6. A developer with zero relevant expertise is excluded from the result.

## Edge cases
- Empty `expertise_map` → return `[]`.
- No developer matches the bug's module/keywords → return `[]`.
- Bug with empty description and no module → return `[]` (nothing to match on).

## Out of scope
- Persisting the assignment / task state (see `04-assignment.md`).
- The TF-IDF implementation detail may evolve; the **contract above is fixed**.

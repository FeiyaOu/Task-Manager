# Feature: Developer Activity Filter

## Purpose
Expose which developers have actually committed within a given recency window, so the frontend
can populate a simple "filter by developer" dropdown on the All Tasks page that reflects real
recent activity — not the full all-time developer list from the expertise map.

## Inputs
- `GET /api/developers` query param `days: int | None` (optional).
  - Reuses the same "last N days" value already used by the repo-analysis day-window control
    (`RepoSetup`); it is a live filter over already-ingested `commits` rows, independent of
    whether a fresh `POST /api/repo/refresh` has just run.

## Outputs
- **200:** `list[str]` — distinct `author_email` values from the `commits` table, sorted
  alphabetically for a stable, testable ordering.

## Rules
1. No `days` param -> return all-time distinct `author_email` values (every developer who has
   ever committed, regardless of recency).
2. `days=N` -> return only `author_email` values with at least one commit where
   `committed_at >= now - N days` (inclusive boundary — a commit exactly `N` days old counts,
   matching the existing `since_date` semantics in `git_analyzer.analyze_repository`).
3. Each email appears at most once in the result, even if the developer has many commits in
   the window.
4. Result is sorted alphabetically (deterministic, testable, and stable dropdown ordering).

## Edge cases
- No commits ever ingested (repo not yet analyzed) -> `[]`.
- `days=N` with zero commits in that window -> `[]`.
- `days=0` -> only commits whose `committed_at` is exactly "now" by the same inclusive cutoff
  math as other windows; in practice this is almost always `[]` but must not error.
- Negative `days` -> 422 (invalid — reuse FastAPI/Pydantic query validation, `ge=0`).

## Out of scope
- Server-side filtering of `GET /api/tasks` by developer (the frontend filters the already-fetched
  task list client-side by `assigned_email`).
- Any change to `GET /api/expertise` or `GET /api/repo/status` (both remain all-time).

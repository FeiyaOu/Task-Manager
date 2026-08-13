# Feature: Assignment

## Purpose
Orchestrate a bug submission end to end: persist the bug, rank developers, assign the
top candidate, and persist the resulting task with its state.

## Inputs
- `bug: BugSubmit` (title, description, module, severity).
- A database session.
- `expertise_map` (from the cache).
- `threshold: float` — minimum acceptable top score (default from config).

## Outputs
- `AssignmentResult`:
  - `bug_id: int`
  - `task_id: int`
  - `assigned_email: str | None`
  - `score: float | None`
  - `matched_modules: list[str]`
  - `status: TaskStatus`

## Rules
1. The bug is saved to the `bug` table before matching runs.
2. `matcher.rank_developers` is called; `result[0]` is chosen when present.
3. A `task` row is persisted with `status`, `score`, `matched_modules`, `reassign_count = 0`.
4. If the ranked list is empty OR `result[0].score < threshold`, the task is created
   with `status = UNASSIGNED` and `assigned_email = None`.
5. Otherwise the task is created with `status = PENDING` and the chosen developer.
6. The whole operation is synchronous — the full result is returned in one request.

## Task state machine (v1 wires the fields; transitions arrive in extensions)
```
PENDING --accept--> ACCEPTED
PENDING --decline--> (reassign to next-best) --> PENDING
                     (reassign_count >= MAX) --> UNASSIGNED
low score / no match --------------------------> UNASSIGNED
```

## Rules — state fields present in v1
7. `TaskStatus` enum exists with: `PENDING, ACCEPTED, DECLINED, UNASSIGNED`.
8. `reassign_count` defaults to 0 and is stored even though v1 never increments it.
   (So accept/decline is a state transition later, not a schema migration.)

## Edge cases
- No developers in the system → `UNASSIGNED`.
- Exactly-at-threshold score → assigned (threshold is a strict `<` for rejection).

## Out of scope
- Accept/decline endpoints and reassignment loop (interview extension).
- Notifications/email (v2).

## Tiered fallback (post-v1 improvement)
When the primary module-scoped match does not clear its gate, assignment relaxes through tiers
instead of giving up. The first tier whose top score clears its threshold wins; `match_tier`
(stored on the task and returned in the result) records which one.

| Tier | Scope | Gate | `match_tier` |
|---|---|---|---|
| 0 | expertise in `bug.module` (+ keyword) | `ASSIGN_THRESHOLD` | `module` |
| 1 | walk up the path (`Engine/Physics/` -> `Engine/`), re-rank | `BROADEN_THRESHOLD` | `broadened` |
| 2 | drop the module; keyword/text match only | `TEXT_THRESHOLD` | `text` |
| 3 | nothing cleared a gate | — | `unassigned` (best near-miss recorded in `score`/`candidates`) |

Default thresholds are all `0.0` (assign whenever any signal exists). The matcher stays pure;
`assignment` orchestrates the tiers. "Most-active maintainer" is intentionally not a default tier.

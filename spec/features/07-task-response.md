# Feature: Task Accept/Decline + Reassignment

## Purpose
Let the assigned developer accept or decline a pending task. Declining reassigns the task to the
next-best candidate from the same ranked list computed at submission time; after the candidate
pool is exhausted (or `MAX_REASSIGNMENTS` is reached), the task is flagged `UNASSIGNED` for human
triage. This is the interview-anticipated extension the codebase was already wired for
(`TaskStatus.ACCEPTED` / `DECLINED`, `Task.reassign_count`, `MAX_REASSIGNMENTS` in `.env`).

## Inputs
- `POST /api/tasks/{task_id}/accept` — no body.
- `POST /api/tasks/{task_id}/decline` — no body. (No "responder" identity in the request: the app
  has no auth/login, so the action always applies to the task's *current* `assigned_email`.)

## Data model changes
`Task` gains two columns (JSON, both required for reassignment to work):
- `candidates: list[{developer_email, score, matched_modules}]` — snapshot of the **full ranked
  list from the tier that won** at assignment time (`assignment.assign_bug`'s `ranked` variable),
  winner first. Persisted once, at creation; never recomputed.
- `declined_emails: list[str]` (default `[]`) — developers who have already declined this task, so
  reassignment never re-offers it to them.

`TaskRead` gains `reassign_count: int` and `declined_emails: list[str]` (read-only, for the
frontend to show decline history / decide when to show the "needs human assignment" message).

## Outputs
- **200:** updated `TaskRead` (existing shape + the two new fields above).
- **404:** unknown `task_id`.
- **409:** action attempted on a task that is not currently `PENDING` (already `ACCEPTED`,
  `DECLINED`-terminal/`UNASSIGNED`, or was never assigned — `assigned_email is None`).

## Rules
1. **Accept** — only valid when `status == PENDING`. Sets `status = ACCEPTED`. Terminal: no further
   accept/decline calls are valid on this task (Rule 6).
2. **Decline** — only valid when `status == PENDING`. Appends the current `assigned_email` to
   `declined_emails` and increments `reassign_count`.
3. After a decline, pick the next candidate from the persisted `candidates` list (in ranked order)
   whose email is not already in `declined_emails`.
   - If found: reassign — `assigned_email = <next candidate>`, `score`/`matched_modules` updated
     to that candidate's values, `status` stays `PENDING` (so the new assignee's row now shows
     accept/decline buttons).
   - If not found (candidate list exhausted): `status = UNASSIGNED`, `assigned_email = None`.
4. Regardless of candidates remaining, once `reassign_count >= MAX_REASSIGNMENTS`
   (default 3, from `Settings`), a decline forces `status = UNASSIGNED`, `assigned_email = None` —
   even if an untried candidate would otherwise exist. This bounds how many times one task can be
   bounced.
5. `MAX_REASSIGNMENTS` is read from `Settings` (already defined; not a new config key).
6. Accept/decline on a task whose `status` is not `PENDING` -> 409 (covers: already `ACCEPTED`,
   already `UNASSIGNED`, or a task that was never assigned in the first place).
7. Accept/decline on a nonexistent `task_id` -> 404.

## Edge cases
- Task had zero candidates at submission (already `UNASSIGNED` from the initial threshold check,
  `assigned_email is None`) -> accept/decline -> 409 (nothing to respond to).
- Candidate list has only one entry and it declines -> immediately `UNASSIGNED` (no more
  candidates), even though `reassign_count` (1) is below `MAX_REASSIGNMENTS` (3).
- `MAX_REASSIGNMENTS = 0` -> the very first decline forces `UNASSIGNED` regardless of remaining
  candidates.
- Declining the same task repeatedly beyond exhaustion is impossible — once `UNASSIGNED`, Rule 6
  returns 409 on any further action.

## Out of scope
- A decline "reason" field (overloaded / not-right-area / needs-context) — not requested for this
  feature; `.env`/spec's original design notes mention it as a future addition, not required now.
- Notifications/email on reassignment.
- Manual override endpoint (`PATCH /api/tasks/{id}` to force-assign) — separate future feature.
- Frontend "who declined" history UI beyond exposing `declined_emails` on `TaskRead` (the data is
  there; a dedicated timeline view is not required).

# Feature: API Layer

## Purpose
Expose the v1 HTTP surface with FastAPI. Thin routers that delegate to services.

## Endpoints

### POST /api/bugs
- **Body:** `BugSubmit { title, description, module, severity }`.
- **Behavior:** save -> rank -> assign top -> return synchronously.
- **200:** `AssignmentResult` (bug_id, task_id, assigned_email, score, matched_modules, status).
- **Rules:**
  1. Missing required fields -> 422 (Pydantic validation).
  2. Repo not yet analyzed (no expertise) -> task returned with `status = UNASSIGNED`.

### GET /api/tasks
- **Behavior:** return all tasks joined with bug + developer info (read-only).
- **200:** `list[TaskRead]`.
- **Rules:**
  3. Ordered newest first.
  4. Includes `status`, `assigned_email`, `score`, `matched_modules`.

### GET /api/modules
- **Behavior:** unique module paths from the expertise table.
- **200:** `list[str]`.
- **Rules:**
  5. No duplicates.
  6. Reflects the currently analyzed repo (updates after refresh).

### POST /api/repo/refresh
- **Behavior:** re-scan git since last analyzed commit, update expertise + cache.
- **200:** `{ new_commits: int, modules: int }`.

### GET /api/repo/status
- **200:** `{ repo_path, last_analyzed_commit, developer_count, module_count }`.

## Cross-cutting rules
7. CORS allows the local frontend origin.
8. App binds `0.0.0.0` so the LAN can reach the dashboard.
9. On startup, the expertise cache is loaded from SQLite into memory.

## Out of scope
- Auth (v2).
- Accept/decline routes (interview extension) — but `TaskRead` already exposes `status`.

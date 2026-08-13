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

## Implementation (as built)

Feature 05 was delivered in three stacked sub-branches (each its own PR, TDD, green before merge).
See `spec/dev-notes.md` for the sub-branch rationale and the issues encountered.

### 05a — foundation  (PR #5)
- `app/config.py` — `Settings` (pydantic-settings): `repo_path`, `database_url`, `decay_lambda`,
  `max_reassignments`, `assign_threshold`, `cors_origins`; cached `get_settings()`.
- `app/database.py` — `make_engine()`, `create_db_and_tables(bind=None)`, `get_session()`.
- Tests: `test_config.py`, `test_database.py` (5).

### 05b — repo pipeline + cache  (PR #6)
- Models: `models/commit.py` (`commits`), `models/expertise.py` (`expertise`),
  `models/config_state.py` (`config_state.last_analyzed_commit_hash`).
- `app/services/repo_ingest.py` — `ingest_repo(session, repo_path, now, lambda_decay, since_commit)`:
  analyze → persist new commits (idempotent) → recompute expertise **from all commits** →
  rewrite `expertise` → update `config_state`; returns `{new_commits, modules}`.
- `app/services/expertise_cache.py` — `ExpertiseCache.load(session)` → `email -> {module -> score}`.
- Shared `db_session` fixture added to `conftest.py`. Tests: `test_repo_ingest.py`,
  `test_expertise_cache.py` (9).

### 05c — API layer  (PR to main)
- `app/main.py` — `create_app()`: CORS + lifespan (create tables + load cache into
  `app.state.expertise_cache`); mounts routers.
- `app/routers/` — `bugs.py`, `tasks.py`, `modules.py`, `repo.py` (the five endpoints above).
- `app/schemas/task.py` — `TaskRead`.
- Tests: `test_api.py` — 6 FastAPI `TestClient` tests.

### Notes / deviations from the bare spec
- **Expertise recompute is from-scratch over ALL persisted commits**, not just the new ones —
  required for correct recency weights (scoring spec Rule 8). `since_commit` only limits what is
  *fetched* from git, not what is *scored*.
- **Idempotent commit insert**: `ingest_repo` skips `(commit_hash)` already persisted, so a refresh
  never duplicates rows even if `since_commit` resolution is ambiguous (see dev-notes issue #2).
- **`0.0.0.0` bind (Rule 8)** is a run-time concern handled by `run.sh` / uvicorn args, not app code.

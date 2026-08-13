# Dev Notes — Clarifications & Sequencing

> Companion to `project-structure.md`. That file is the canonical *plan* (the "what").
> This file captures *clarifications, sequencing, and gotchas* (the "when / why") decided
> during development so they don't have to be re-derived.

## Build strategy: TDD one seam at a time

The five feature specs are built in dependency order, each red → green before the next:

1. `git_analyzer` → 2. `scoring` → 3. `matcher` → 4. `assignment` → 5. `api`

Key point: **`git_analyzer` and `scoring` need no DB/foundation.** Their specs mark
persistence as out of scope — they are pure functions returning dataclasses/dicts. So the
shared foundation (`config.py`, `database.py`, `models/`) is **not** a prerequisite for
starting; it's only needed once `matcher`/`assignment`/routers must persist data.

"Scaffold the foundation" is therefore a *later* step, not a competing choice to TDD.

### Git workflow
- One branch per feature, e.g. `feat/01-git-analyzer`, merged to `main` when the seam is green.
- Keeps `main` always-green and demonstrates clean workflow (graded in the live interview).
- Solo/fast alternative: commit each phase straight to `main`. Either is fine.

## matcher vs assignment (they look similar but aren't)

| | `matcher` (03) | `assignment` (04) |
|---|---|---|
| Layer | pure logic | orchestration + DB |
| Input | bug + expertise_map (dict) | bug + **DB session** + map + threshold |
| Returns | *all* candidates ranked best→worst | *one* persisted task (`AssignmentResult`) |
| Threshold / UNASSIGNED rule | not its job | owns it |
| Task state / `reassign_count` | no | yes |
| Testable without a DB | yes | needs a session |

Relationship: **assignment calls matcher.** `rank_developers(bug, map) → result[0] → write Task`.
Split exists because the likely live extension (accept/decline + reassignment) needs the
*next-best* candidate (`result[1]`, already in the ranked list) and a task state transition
(lives entirely in `assignment.py`). matcher ranks; assignment decides and records.

## SQLite — nothing to install

SQLite ships in Python's stdlib (`sqlite3`); SQLModel/SQLAlchemy use it via that driver.
- No `pip install` / `brew install`, no server to run.
- `DATABASE_URL` = e.g. `sqlite:///./taskmanager.db`.
- `create_db_and_tables()` in `database.py` creates the `.db` file on first run.
- The only "SQLite work" is writing `database.py` during foundation scaffold.

## When to start the frontend

Frontend is **build step 6** and needs two backend endpoints live first:
- `GET /api/modules` (step 4) → dropdown source
- `POST /api/bugs` (step 5) → submit → success card

Green light = those endpoints return real data (verify via `/docs` or curl).
Then: submit page (step 6) → `GET /api/tasks` + task table (step 7).

## Backend components beyond the 5 feature specs

The specs cover the *core logic*; `project-structure.md` also lists supporting glue that has
no dedicated spec file:

**Foundation (boilerplate, no spec):**
- `config.py` — pydantic-settings, loads `.env` (`REPO_PATH`, `DATABASE_URL`, `DECAY_LAMBDA`, …)
- `database.py` — engine, `create_db_and_tables()`, `get_session()`
- `main.py` — FastAPI app, CORS, startup analysis, mounts routers
- `models/` — SQLModel tables + `TaskStatus` enum
- `schemas/` — API request/response Pydantic models

**Services beyond the 5 specs:**
- `expertise_cache.py` — in-memory dict loaded from SQLite on startup/refresh
- scoring **persistence/upsert** — the thin wrapper that writes the pure scorer's output
  into the `expertise` table
- `watcher.py` — watchdog on `.git` for "stays current" (build **step 8**, last; app works
  via manual `POST /api/repo/refresh` until then)

**Routers (partly in `05-api.md`):**
- `POST /api/repo/refresh` + `GET /api/repo/status`

Mental map:
```
5 feature specs = the brains (git_analyzer, scoring, matcher, assignment, api)
not-yet-specced = the plumbing (config, database, main, models, schemas,
                  expertise_cache, scoring-persistence, watcher)
```
Only genuine non-boilerplate "feature" here is `watcher.py`; everything else is standard glue.

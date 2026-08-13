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

## Feature 05 sub-branch split (as built)

Feature 05 (API) was too large for one branch, so it shipped as three dependency-ordered,
stacked sub-branches — each its own PR, TDD, green before merge:

| Sub-branch | Scope | PR |
|---|---|---|
| `feat/05a-foundation` | `config.py`, `database.py` | #5 |
| `feat/05b-repo-pipeline` | `commit`/`expertise`/`config_state` models, `repo_ingest.py`, `expertise_cache.py` | #6 |
| `feat/05c-api` | `main.py`, routers, `TaskRead`, startup cache | — |

05b was **stacked on 05a** (needed its DB helpers) — when opening a stacked PR, set its base to the
parent branch, not `main`; GitHub auto-retargets to `main` after the parent merges.
The full breakdown is in `spec/features/05-api.md` → "Implementation (as built)".

## Issues encountered & fixes

Durable record of non-obvious problems hit during feature 05, so they aren't re-debugged later.

### 1. Stray `taskmanager.db` written into the repo during tests
- **Symptom:** running the *full* suite created `backend/taskmanager.db` (no single test file did
  it alone — it was a cross-file interaction with the unused module-level default engine).
- **Cause:** `app.database` creates a module-level `engine` from the default
  `DATABASE_URL=sqlite:///./taskmanager.db`. Importing the app in tests could touch it.
- **Fix:** made the suite hermetic — `conftest.py` sets `DATABASE_URL=sqlite://` (in-memory) before
  app import, mirroring the existing `GIT_CONFIG_*` hardening. Tests inject their own engines.
  `.gitignore` already covers `*.db` as a backstop.

### 2. Incremental refresh duplicated / miscounted commits with identical timestamps
- **Symptom:** `test_incremental_no_new_commits_no_duplicates` reported `new_commits == 1` when it
  should be 0.
- **Cause:** two seeded commits shared `days_ago=0` (identical `committed_at`). The analyzer sorts
  by `committed_at`, so `records[-1]` (used as `last_analyzed_commit_hash`) was ambiguous, and the
  ancestry range `{since}..HEAD` re-fetched an already-persisted commit.
- **Fix:** added a **DB-level idempotency guard** in `repo_ingest.ingest_repo` — skip any
  `commit_hash` already persisted. `since_commit` is treated as a fetch optimization only; the DB
  dedup is the correctness guarantee.

### 3. Making the engine test-injectable for `TestClient`
- **Need:** API tests must run against an in-memory DB shared across requests.
- **Fix:** `create_db_and_tables(bind=None)` and `get_session()` resolve the module-global `engine`
  at **call time**, and `main.py` references `database.engine` lazily. Tests `monkeypatch` a
  `StaticPool` in-memory engine (StaticPool so all connections share one in-memory DB).

### 4. SQLite drops timezone info on stored datetimes
- **Symptom:** scoring math on DB-read `committed_at` would mix naive/aware datetimes.
- **Fix:** `repo_ingest._as_aware()` re-attaches UTC to naive timestamps read back from SQLite
  before handing them to `compute_expertise`.

## Decision: `watcher.py` dropped as unnecessary

The original build order (`project-structure.md` step 8) planned a `watchdog` observer on `.git/`
to auto-refresh so the system "stays current." **We are not building it.**

**Why it's now redundant:** "stays current" is already satisfied and demonstrable without it —
1. the `RepoSetup` panel has a one-click **Re-analyze** (returns `new_commits`, so change pickup is
   visible live);
2. **incremental refresh** via `since_commit` + the DB idempotency dedup makes re-analysis cheap;
3. the `days` window scopes re-scans.

**Why we actively skip it:** a background `watchdog` thread means threading against SQLite,
concurrent cache reloads, `.git` write debouncing, and app-lifecycle management — a lot of fragile
surface area for what amounts to saving one click on a local tool. Explicit refresh is also better
UX than a surprise background job.

**If zero-click freshness is ever wanted** (no new dependency, no thread): React Query
`refetchOnWindowFocus` / `refetchInterval` on `repoStatus` + `modules`, or a small "auto re-analyze
every N min" toggle. Preferred over a filesystem watcher.

Interview framing: if asked about "stays current," explain that in-app analyze/re-analyze +
incremental refresh meets the requirement with far less risk than a watcher.

## Refresh semantics: "All" (incremental) vs. day-window (absolute) — and the gap risk

`POST /api/repo/refresh` has two distinct modes, driven by whether `days` is passed:

```python
since_date   = now - timedelta(days=days) if days is not None else None
since_commit = None if since_date else (state.last_analyzed_commit_hash if state else None)
```

| Mode | Range analyzed | Uses `last_analyzed_commit` cursor? | Gap risk |
|---|---|---|---|
| **All** (`days` omitted) | `last_tip..HEAD` (incremental) | ✅ yes | ❌ none |
| **Window** (`days=N`) | absolute `[now−N, now]` | ❌ no (cursor is bypassed) | ✅ yes |

**Counterintuitive but important:** "All" is the *gap-free* option — it walks from the last analyzed
commit to HEAD, so it never skips anything. A **day window is an absolute snapshot** that ignores
the cursor, so it can leave a permanent hole.

**Worked example.** Last scan Monday with `days=7` → sets `last_analyzed_commit` to Monday's tip.
Next scan Friday with `days=1` → window is `[Thursday, Friday]`, `since_commit` bypassed. Tuesday–
Wednesday commits are **never ingested** (they were outside Monday's earlier window too) → a gap.
Choosing **All** on Friday instead would fetch `Monday_tip..HEAD` = Tue→Fri, filling the gap.

Non-destructive: a window scan **adds** its commits (dedup-guarded) to whatever is already stored
and recomputes expertise over the union; it just won't *back-fill* ranges outside its window. Only
**All** (or a wide-enough window) covers the gap. A true clean rescan = delete `taskmanager.db`.

**Possible UX follow-ups (not built):** relabel as "All (since last scan)" vs "Window (last N days)";
make All a genuine full rescan (ignore `since_commit`); or warn when a chosen window starts after the
last-analyzed commit's date (potential gap).

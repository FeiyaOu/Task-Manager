# Task Manager — v1 Project Structure

> v1 plan derived from `spec/project-basic-info.md` and the design reasoning in `docs/design-discussion.md`.
> Scope: **submit page + read-only task list**. Structured so the likely interview extensions
> (accept/decline + reassignment, workload balancing, assignment explanations) drop in without a rewrite.

## Design principles

The live extension will almost certainly touch *how a developer is chosen or how the choice is presented*.
The structure enforces four independent seams so that extension is safe and fast:

1. **`git_analyzer`** — reads the repo, knows nothing about scoring.
2. **`scoring`** — turns commits into expertise numbers, knows nothing about bugs.
3. **`matcher`** — returns a **ranked list** `[(developer, score, reasons), ...]`, never just a winner.
4. **`assignment`** — orchestrates and owns task *state*, so state-machine features live in one place.

## Directory structure

```
Task-Manager/
├── .env                          # REPO_PATH, DATABASE_URL, DECAY_LAMBDA, MAX_REASSIGNMENTS
├── .env.example
├── .gitignore                    # already ignores docs/
├── README.md                     # install + "point at a repo" instructions (graded!)
├── run.sh                        # one command: starts backend + serves frontend build
├── spec/
│   ├── project-basic-info.md
│   └── project-structure.md      # this file
├── docs/                         # gitignored working notes
│   └── design-discussion.md
│
├── backend/
│   ├── requirements.txt
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app, CORS, startup analysis, mounts routers
│   │   ├── config.py             # pydantic-settings, loads .env
│   │   ├── database.py           # engine, create_db_and_tables(), get_session()
│   │   │
│   │   ├── models/               # SQLModel tables (DB + schema in one class)
│   │   │   ├── __init__.py
│   │   │   ├── developer.py
│   │   │   ├── commit.py         # one row per commit × file
│   │   │   ├── expertise.py      # one row per developer × module
│   │   │   ├── bug.py
│   │   │   ├── task.py           # status + score + matched_modules + reassign_count
│   │   │   ├── enums.py          # TaskStatus enum  <- extension-ready
│   │   │   └── config_state.py   # last_analyzed_commit_hash
│   │   │
│   │   ├── schemas/              # API-only Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── bug.py            # BugSubmit, AssignmentResult
│   │   │   └── task.py           # TaskRead, DeclineRequest (unused in v1, ready for ext)
│   │   │
│   │   ├── routers/
│   │   │   ├── __init__.py
│   │   │   ├── bugs.py           # POST /api/bugs   (submit -> assign -> return)
│   │   │   ├── tasks.py          # GET  /api/tasks  (read-only list = the demo proof)
│   │   │   ├── modules.py        # GET  /api/modules
│   │   │   └── repo.py           # POST /api/repo/refresh, GET /api/repo/status
│   │   │
│   │   └── services/            # <- all business logic, the four seams
│   │       ├── __init__.py
│   │       ├── git_analyzer.py   # GitPython -> commit rows
│   │       ├── scoring.py        # recency decay, per-module accumulation, upsert
│   │       ├── expertise_cache.py# in-memory dict, load on startup / refresh
│   │       ├── matcher.py        # TF-IDF -> RANKED list of candidates + reasons
│   │       ├── assignment.py     # picks top candidate, writes Task, owns state
│   │       └── watcher.py        # watchdog on .git -> incremental refresh
│   │
│   └── tests/
│       ├── conftest.py           # temp git repo fixture
│       ├── test_git_analyzer.py
│       ├── test_scoring.py
│       ├── test_matcher.py       # asserts ranked order, not just winner
│       └── test_assignment.py
│
└── frontend/
    ├── package.json
    ├── vite.config.js            # proxy /api -> localhost:8000
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── main.jsx              # QueryClientProvider
        ├── App.jsx               # 2 routes: /  and  /tasks
        ├── api/
        │   └── client.js         # one fetch wrapper per endpoint
        ├── hooks/
        │   ├── useModules.js
        │   ├── useSubmitBug.js
        │   └── useTasks.js
        ├── pages/
        │   ├── BugSubmitPage.jsx
        │   └── TaskListPage.jsx  # read-only table = proof assignment distributes
        └── components/
            ├── BugForm.jsx
            ├── SuccessCard.jsx   # assignee + score + [Submit another][View tasks]
            ├── ModuleDropdown.jsx
            └── TaskTable.jsx
```

## The one function that makes extension easy

Build `matcher.py` to return a ranked list, never a single winner:

```python
# services/matcher.py
def rank_developers(bug, expertise_map) -> list[Candidate]:
    """Return developers ranked best->worst with score + reasons.
    Winner = result[0]. Next-best (for reassignment) = result[1], etc."""
    ...

# Candidate = {developer_email, score, matched_modules: list[str]}
```

Why this unlocks each likely extension:

| Live feature | What changes | Cost |
|---|---|---|
| **Accept/Decline + reassign** | `assignment.py` picks `result[n+1]` on decline; flip `TaskStatus` | small — data already there |
| **Workload balancing** | re-sort `result` by `score / (1 + open_tasks)` | one function, one query |
| **Explain the assignment** | expose `matched_modules` already on the Task | near-zero |
| **Confidence / unassigned** | if `result[0].score < threshold` -> `TaskStatus.UNASSIGNED` | one `if` |
| **Manual override** | `PATCH /api/tasks/{id}` sets developer | one route |

Because the `Task` model carries `status`, `score`, `matched_modules`, and `reassign_count` from v1
(even if unused), none of these need a schema migration during the interview.

## Data model (v1)

| Table | Grain | Extension-ready fields |
|---|---|---|
| `developer` | one per email | — |
| `commit` | one per commit × file | — |
| `expertise` | one per developer × module | `score, commit_count, last_updated` |
| `bug` | one per submission | `title, description, module, severity` |
| `task` | one per assignment | `status`, `score`, `matched_modules`, `reassign_count` <- pre-wired |
| `config_state` | single row | `last_analyzed_commit_hash` (incremental refresh) |

## API surface (v1)

- `POST /api/bugs` — submit -> `rank_developers` -> assign top -> return result
- `GET /api/tasks` — full list (powers the demo-critical task table)
- `GET /api/modules` — dynamic dropdown source
- `POST /api/repo/refresh` + `GET /api/repo/status` — "stays current" requirement

## Build order

1. Scaffold + config + models (with extension-ready `Task` fields and `TaskStatus` enum).
2. `git_analyzer.py` -> populate `commit` table from `REPO_PATH`.
3. `scoring.py` + `expertise_cache.py` -> build expertise, load on startup.
4. `GET /api/modules` -> unblocks frontend dropdown.
5. `matcher.rank_developers()` + `assignment.py` -> `POST /api/bugs`.
6. Frontend submit page -> success card.
7. `GET /api/tasks` + task table page.
8. `watcher.py` -> "stays current" as repo changes.

## v1 scope guardrails

- **In:** submit page, read-only task list, synchronous assignment, LAN bind (`0.0.0.0`),
  SQLite, incremental refresh.
- **Out (v2):** auth, workload UI, accept/decline UI, email, cloud/Postgres — but the data model
  and matcher already accommodate them so the live add is fast.

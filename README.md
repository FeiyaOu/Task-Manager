# Task Manager — Git-Aware Bug Assignment

A local web app that assigns incoming bug reports to the **most relevant developer**, based on
who has actually worked on the related code. Point it at any local git repository; it reads that
repo's history, builds a per-developer expertise map from real commits, and routes each submitted
bug to the best-matched engineer.

> The "repository" is the software project your team maintains — **not** this app. You supply a
> path to a local git repo, and the app analyzes *its* history.

## How it works

```
git history (GitPython)
   → commit-file records         (per commit × file, incl. commit message)
   → recency-weighted scores      (per developer × module)
   → expertise map                (SQLite + in-memory cache)
   → TF-IDF module index          (commit messages + path tokens per module)
   → matcher                      (coverage-weighted ranked candidates)
   → assignment                   (tiered fallback → persisted task)
```

Expertise score per (developer, module): `Σ (lines_changed × e^(−λ · days_ago))` — recent work
counts more than old work (exponential decay, λ = 0.01 by default).

## Matching algorithm

When a bug is submitted, the matcher ranks every developer and the assignment step picks the top
candidate through a series of fallback tiers.

### 1. Coverage-weighted score

For each developer:

```
score = Σ (expertise[module] × weight(module))  ×  coverage_factor

weight(module) = 1.0                       if the module was explicitly selected
               = TF-IDF relevance(module)  if a module-relevance map is supplied
               = 1.0 if the module path shares a word with the bug text, else 0.0

coverage_factor = (1 + covered) / (1 + |selected|)     # 1.0 when nothing is selected
```

`covered` is how many of the **selected** modules the developer has expertise in, so a developer
who spans more of the selected area outranks one with a single large score. Developers with zero
relevant expertise are excluded; ties break by email for reproducibility.

### 2. TF-IDF module relevance (commit-message enrichment)

The `ModuleIndex` builds one document per module from its **commit messages + file-path tokens**,
fits a `TfidfVectorizer` (English stop words), and scores the **cosine similarity** between the bug
text (title + description) and each module. This lets bug text like *"billing"* find a `payments/`
module when developers described that work as *"fix billing"* in their commits — enrichment supplies
the vocabulary, IDF down-weights common words like *fix*/*update*. It is still lexical, not semantic
(true synonyms would need embeddings — out of scope). When the index isn't ready, the matcher falls
back to plain path-token overlap, so behaviour degrades gracefully.

### 3. Assignment fallback tiers

The assignment step tries progressively broader matches and records which tier won as `match_tier`:

| Tier | Basis | Gate |
|---|---|---|
| `module` | the selected modules only | `ASSIGN_THRESHOLD` |
| `broadened` | parent modules (strip path segments, e.g. `Engine/Physics/Foo/` → `Engine/Physics/`, `Engine/`) | `BROADEN_THRESHOLD` |
| `text` | text-only match (no module constraint) | `TEXT_THRESHOLD` |
| `unassigned` | no tier cleared its gate → task left UNASSIGNED, best near-miss recorded | — |

## Features

- **Point at any local git repo** and analyze its full history.
- **Submit bug reports** through the web UI (title, description, one or more affected modules, severity).
- **Automatic assignment** to the best-matched developer, showing the matched modules, score, and match tier.
- **Full candidate ranking** returned per bug (top match plus next-best for reassignment).
- **Read-only task list** showing how bugs distribute across the team.
- **Dynamic module dropdown** (multi-select) sourced from the analyzed repo — nothing hardcoded.
- **Stays current** as the repo changes via incremental refresh, with a staleness indicator.

## Tech stack

- **Backend:** FastAPI 0.115, SQLModel 0.0.22 (SQLAlchemy + Pydantic), GitPython 3.1, scikit-learn 1.6 (TF-IDF), pydantic-settings 2.7, uvicorn 0.34
- **Database:** SQLite (built into Python — nothing to install)
- **Frontend:** React 18, Vite 5, TailwindCSS 3, TanStack Query 5, React Router 6, TypeScript 5

## Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)
- A local git repository to point the app at

## Setup

```bash
# 1. Clone this project
git clone <this-repo-url>
cd Task-Manager

# 2. Configure — copy the example env and set the repo you want analyzed
cp .env.example .env
#   then edit REPO_PATH in .env to point at a local git repository
```

### Configuration (`.env`)

| Setting | Default | Purpose |
|---|---|---|
| `REPO_PATH` | *(unset — required)* | Absolute path to the git repo to analyze |
| `DATABASE_URL` | `sqlite:///./taskmanager.db` | SQLite location (relative paths resolve from the project root) |
| `DECAY_LAMBDA` | `0.01` | Recency decay constant (larger = older commits fade faster) |
| `MODULE_DEPTH` | `1` | Path depth that defines a "module" (1 = top-level folder) |
| `ASSIGN_THRESHOLD` | `0.0` | Score gate for the `module` tier |
| `BROADEN_THRESHOLD` | `0.0` | Score gate for the `broadened` tier |
| `TEXT_THRESHOLD` | `0.0` | Score gate for the `text` tier |
| `MAX_REASSIGNMENTS` | `3` | Reserved for the accept/decline extension |
| `CORS_ORIGINS` | `["http://localhost:5173"]` | Allowed frontend origins (JSON list) |

## Running

The backend and the frontend run as two processes, so use **two terminals**.

```bash
# Terminal 1 — backend API on http://0.0.0.0:8000
# (creates the venv, installs deps, then starts uvicorn)
./run.sh
```

```bash
# Terminal 2 — frontend UI on http://localhost:5173
# (Vite dev server; proxies /api → localhost:8000)
cd frontend
npm install
npm run dev
```

`run.sh` requires a `.env` file and exits if one is missing. It serves the **API only** — open the
UI at **http://localhost:5173**, submit a bug, and watch it get assigned. Interactive API docs are
at `http://localhost:8000/docs`.

To populate the expertise map, analyze your repo via the **Repo Setup** page in the UI or:

```bash
curl -X POST http://localhost:8000/api/repo/refresh
```

> **Schema-change gotcha:** the SQLite file resolves relative to the working directory, so `run.sh`
> creates it at the **project root** (`./taskmanager.db`). `create_all` only creates missing tables —
> it never adds columns to an existing one. After a model change, delete the root DB and re-analyze:
> `rm -f taskmanager.db`.

## API surface

| Method & path | Purpose |
|---|---|
| `POST /api/bugs` | Submit a bug (`title`, `description`, `modules: string[]`, `severity`) → rank developers → assign top → return result with `match_tier` and full `candidates` |
| `GET /api/tasks` | All tasks (bug + assignee + score + matched modules + status + tier), newest first |
| `GET /api/modules` | Unique module paths from the analyzed repo (multi-select dropdown source) |
| `GET /api/expertise` | Expertise rows (filterable by `developer` / `module`), score-sorted |
| `POST /api/repo/refresh` | Re-scan git (incremental, or bounded by `?days=`); rebuild expertise + TF-IDF index |
| `GET /api/repo/status` | `repo_path`, `last_analyzed_commit`, `head_commit`, `is_stale`, `developer_count`, `module_count` |

## Testing

`run.sh` creates the virtualenv at `backend/.venv`, so run it once first (or `python -m venv
backend/.venv && pip install -r backend/requirements.txt`). Then:

```bash
cd backend
source .venv/bin/activate
pytest
```

96 tests across 11 files. Development follows TDD in dependency order — every rule in the feature
specs maps to at least one test, and no production code is written without a failing test first.

## Project structure

```
Task-Manager/
├── backend/
│   └── app/
│       ├── routers/    # bugs, tasks, modules, repo, expertise
│       ├── services/   # git_analyzer, repo_ingest, scoring, expertise_cache,
│       │               #   matcher, module_index (TF-IDF), assignment
│       ├── models/     # bug, task, commit, expertise, config_state, enums
│       └── schemas/    # request/response shapes
├── frontend/           # React + TypeScript + Vite + Tailwind (submit page, task list, repo setup)
├── spec/               # specs & feature contracts — see spec/README.md for the index
└── docs/               # working design notes (gitignored)
```

## Documentation

- **[spec/README.md](spec/README.md)** — index of all specs: which file answers which question.
- **[spec/project-basic-info.md](spec/project-basic-info.md)** — product vision & data model.
- **[spec/project-structure.md](spec/project-structure.md)** — architecture, seams, build order.
- **[spec/features/](spec/features/)** — per-feature contracts (git analyzer → scoring → matcher → assignment → API).
- **[spec/dev-notes.md](spec/dev-notes.md)** — sequencing, gotchas, and clarifications.

## Project status

v1 complete and green (96 tests):

- [x] **Phase 0** — scaffold, test harness, temp-git-repo fixture
- [x] **Phase 1** — `git_analyzer` (repo → commit-file records, incl. commit messages)
- [x] **Phase 2** — `scoring` (records → recency-weighted expertise)
- [x] **Phase 3** — foundation (`config`, `database`, `models`) + `GET /api/modules`
- [x] **Phase 4** — `matcher` + `assignment` + `POST /api/bugs`
- [x] **Phase 5** — frontend submit page + `GET /api/tasks` task list
- [x] **Extras** — multi-module select, coverage-weighted matching, TF-IDF commit-message enrichment, tiered assignment fallback, repo staleness + incremental refresh, expertise API

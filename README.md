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
   → commit-file records        (per commit × file)
   → recency-weighted scores     (per developer × module)
   → expertise map               (SQLite + in-memory cache)
   → matcher                     (ranked candidates for a bug)
   → assignment                  (top candidate → persisted task)
```

Expertise score per (developer, module): `Σ (lines_changed × e^(−λ · days_ago))` — recent work
counts more than old work (exponential decay, λ = 0.01 by default).

## Features (v1)

- **Point at any local git repo** and analyze its full history.
- **Submit bug reports** through the web UI (title, description, affected module, severity).
- **Automatic assignment** to the best-matched developer, with the matched modules and score shown.
- **Read-only task list** showing how bugs distribute across the team (the proof the matcher works).
- **Dynamic module dropdown** sourced from the analyzed repo — nothing hardcoded.
- **Stays current** as the repo changes, via incremental refresh (and an optional file watcher).

## Tech stack

- **Backend:** FastAPI, SQLModel (SQLAlchemy + Pydantic), GitPython, scikit-learn (TF-IDF), watchdog
- **Database:** SQLite (built into Python — nothing to install)
- **Frontend:** React + Vite + TailwindCSS

## Prerequisites

- Python 3.11+
- Node.js 18+ (for the frontend)
- A local git repository to point the app at

## Installation

```bash
# 1. Clone this project
git clone <this-repo-url>
cd Task-Manager

# 2. Backend
cd backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# 3. Frontend (once it exists)
cd ../frontend
npm install
```

## Configuration

Copy `.env.example` to `.env` in the project root and set the path to the repo you want analyzed:

```bash
REPO_PATH=/Users/you/projects/my-app   # the git repo to analyze
DATABASE_URL=sqlite:///./taskmanager.db
DECAY_LAMBDA=0.01                       # recency decay constant
MAX_REASSIGNMENTS=3                     # reserved for accept/decline extension
```

## Running

```bash
# From the project root, one command (starts backend + serves frontend build):
./run.sh
```

Or run the pieces individually during development:

```bash
# Backend (binds 0.0.0.0:8000 so the LAN can reach it)
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (Vite dev server, proxies /api → localhost:8000)
cd frontend
npm run dev
```

Then open the frontend URL, submit a bug, and watch it get assigned. Interactive API docs are at
`http://localhost:8000/docs`.

## API surface (v1)

| Method & path | Purpose |
|---|---|
| `POST /api/bugs` | Submit a bug → rank developers → assign top → return result |
| `GET /api/tasks` | All tasks (bug + assignee + score + status), newest first |
| `GET /api/modules` | Unique module paths from the analyzed repo (dropdown source) |
| `POST /api/repo/refresh` | Re-scan git since last analyzed commit; update expertise |
| `GET /api/repo/status` | Repo path, last analyzed commit, developer/module counts |

## Testing

```bash
cd backend
pytest
```

Development follows TDD in dependency order — every rule in the feature specs maps to at least one
test, and no production code is written without a failing test first.

## Project structure

```
Task-Manager/
├── backend/        # FastAPI app, services (git_analyzer, scoring, matcher, assignment), tests
├── frontend/       # React + Vite + Tailwind (submit page + task list)
├── spec/           # Specs & feature contracts — see spec/README.md for the index
└── docs/           # Working design notes (gitignored)
```

## Documentation

- **[spec/README.md](spec/README.md)** — index of all specs: which file answers which question.
- **[spec/project-basic-info.md](spec/project-basic-info.md)** — product vision & data model.
- **[spec/project-structure.md](spec/project-structure.md)** — architecture, seams, build order.
- **[spec/features/](spec/features/)** — per-feature contracts (git analyzer → scoring → matcher → assignment → API).
- **[spec/dev-notes.md](spec/dev-notes.md)** — sequencing, gotchas, and clarifications.

## Project status

v1 in progress, built seam by seam:

- [x] **Phase 0** — scaffold, test harness, temp-git-repo fixture
- [ ] **Phase 1** — `git_analyzer` (repo → commit-file records)
- [ ] **Phase 2** — `scoring` (records → expertise scores)
- [ ] **Phase 3** — foundation (`config`, `database`, `models`) + `GET /api/modules`
- [ ] **Phase 4** — `matcher` + `assignment` + `POST /api/bugs`
- [ ] **Phase 5** — frontend submit page + `GET /api/tasks` task list
- [ ] **Phase 6** — `watcher` (auto-refresh as the repo changes)

# Task Manager Project Basic Info

## Project goal
Build a local task management application for a software engineering team. It should be able to point at any local git repository on the machine, analyze that repository's history, and assign bug reports to the most relevant developer based on prior work in the repo.

## Core idea
The system should run locally as a web app and allow team members to submit bug reports through the product itself. The backend reads the target repository's git history and builds a developer expertise map from historical code contributions. When a bug is submitted, the system matches the bug description against that expertise map to choose the most relevant developer and create an assignment.

## Repository meaning
The "repository" in this project is not the task manager app itself. It is the software project being managed by the team. The app should accept a path to a local git repository, such as:

- /Users/you/projects/my-app
- /home/user/work/project

The app reads from that repository's git metadata to understand who changed what.

## Developer definition
Developers are identified from the git history of the target repository, usually by author name and email from commits. The system does not need a separate manual specialty database as the primary source of truth. Instead, developer expertise is inferred from:

- files they changed
- modules or directories they modified
- commit frequency
- recency of changes
- commit messages and file paths

This means the system can stay aligned with the repository as it evolves.

## Product UI flow
The product includes a web interface with at least:

1. Bug submission form
   - title
   - description
   - affected component or area
   - optional severity or priority

2. Developer dashboard
   - assigned tasks
   - task status
   - developer workload
   - task history

## Assignment logic
The assignment engine should:

1. Save the submitted bug report to the database
2. Load or refresh the developer expertise map
3. Compare the bug description to developer expertise using keywords, file relevance, and historical contributions
4. Select the developer with the strongest match
5. Save the task assignment in the database
6. Return the data to the frontend so it can be displayed in the dashboard

## Expertise map — storage design

The expertise map uses two layers:

- SQLite table = persistent storage, survives restarts, easy to query
- Python dict in memory = fast runtime lookup, loaded from SQLite on startup

The flow is:
1. On startup, load expertise table into a Python dict
2. When serving a bug assignment, use the in-memory dict
3. When repo changes, recompute affected parts, update both SQLite and the dict

### Expertise table structure

One row per (developer, module) pair. A developer can have many rows — one per module they have touched.

| developer_id | module_path | score | commit_count | last_updated |
|---|---|---|---|---|
| 1 (alice) | auth/ | 47.3 | 18 | 2026-08-12 |
| 1 (alice) | user/ | 18.6 | 9 | 2026-08-12 |
| 2 (bob) | billing/ | 97.1 | 27 | 2026-08-12 |

### In-memory dict shape (Python)

```python
expertise_map = {
    "alice@example.com": {
        "auth/": 47.3,
        "user/": 18.6,
    },
    "bob@example.com": {
        "billing/": 97.1,
        "payments/": 8.5,
    }
}
```

This is a dict of dicts — a mapping from developer email to their per-module scores.

## Commits table — raw git data

The commits table stores one row per (commit, file) pair. This is the raw material for building expertise scores.

| id | commit_hash | author_email | file_path | lines_added | lines_deleted | committed_at |
|---|---|---|---|---|---|---|
| 1 | a1b2c3 | alice@x.com | auth/login.py | 40 | 10 | 2026-08-10 |
| 2 | a1b2c3 | alice@x.com | auth/utils.py | 5 | 2 | 2026-08-10 |
| 3 | d4e5f6 | bob@x.com | billing/checkout.py | 80 | 30 | 2026-08-11 |

## Score calculation

File paths are normalized to modules by taking the top-level directory:

- auth/login.py → auth/
- billing/checkout.py → billing/

The score for each (developer, module) pair is:

score = sum over all commits of: lines_changed × recency_weight

Recency weight uses exponential decay so older commits count less:

recency_weight = e^(−λ × days_ago)

With λ = 0.01, a commit from 100 days ago is worth about 37% of a commit from today.

## How the expertise table updates

The expertise table is a living summary that keeps changing as new commits arrive.

- commit_count increments with each new commit touching that module
- score is recalculated from scratch for affected (developer, module) pairs because recency weights change over time

Only affected pairs are recomputed. Everything else is left unchanged. This is the incremental update strategy.

A config table stores the last analyzed commit hash so the system only processes new commits since that point on each refresh.

Recalculate from scratch means: re-sum all commits for that (developer, module) pair using current recency weights, not just add new ones on top. This avoids score drift from stale weights.

## What to extract from git log

For each commit:

- author name
- author email (used as the developer identifier)
- commit timestamp
- changed file paths
- lines added per file
- lines deleted per file

GitPython is used to read this from the local git repository.

## SQLModel and SQLAlchemy

SQLAlchemy is the most popular Python ORM. It lets you define database tables as Python classes and handle queries without writing raw SQL.

SQLModel is built on top of SQLAlchemy and Pydantic. It is made by the same author as FastAPI and integrates naturally with it. You define one class that serves as both the database model and the API response schema. SQLModel is the recommended choice for this project.

## Keeping the system current
The app should refresh expertise data when the repository changes. This can happen through:

- startup analysis
- periodic re-scan of git history
- a file system watcher or background job that triggers repo refresh when code changes are detected

This keeps the assignment engine current as developers continue making commits.

## Architecture overview
The project is likely split into these main parts:

1. Frontend UI
   - React + Vite + TailwindCSS

2. Backend API
   - FastAPI (recommended) or Express

3. Database
   - SQLite for a local app is a good simple choice

4. Git analysis layer
   - parse git log, commit metadata, changed files, and author information

5. Matching / assignment engine
   - keyword matching, file overlap, contribution scoring

6. Repo watcher / refresh logic
   - keeps expertise map updated

## Dynamic module list for the bug submission form

The bug submission form must not hardcode module names. Each repository has its own directory structure and naming conventions. The frontend must fetch available modules from the backend and populate the dropdown dynamically.

Backend exposes an endpoint:

GET /api/modules → returns a list of unique module paths from the expertise table

The frontend fetches this on load and builds the dropdown from the response. When the repo refreshes and new modules appear, the endpoint returns the updated list automatically.

This means the form content always reflects the actual structure of whatever repository the app is pointed at.

## Data pipeline summary

```
git log (GitPython)
    ↓
commits table (one row per commit × file)
    ↓
normalize file path to module (top-level directory)
compute recency weight per commit
accumulate score per (author_email, module)
    ↓
expertise table (upsert — one row per developer × module)
    ↓
in-memory Python dict (loaded at startup, refreshed on change)
    ↓
/api/modules endpoint → frontend dropdown
assignment engine → bug-to-developer matching
```

## Full tech stack

### Frontend
| Technology | Purpose |
|---|---|
| React | UI component framework |
| Vite | fast dev server and build tool |
| TailwindCSS | utility-first styling |
| React Query (TanStack Query) | server state management, data fetching, polling |

### Backend
| Technology | Purpose |
|---|---|
| Python 3.11+ | primary language |
| FastAPI | async web framework, auto-generates /docs |
| Uvicorn | ASGI server that runs FastAPI |
| Pydantic | request/response validation and schema definition |
| SQLModel | ORM built on SQLAlchemy + Pydantic, integrates cleanly with FastAPI |
| SQLite | file-based local database, no separate install needed |

### Git analysis
| Technology | Purpose |
|---|---|
| GitPython | reads git log, commit history, file stats from local repo |

### Assignment / matching engine
| Technology | Purpose |
|---|---|
| scikit-learn | TF-IDF vectorizer for matching bug description to module keywords |
| Python math / collections | exponential decay scoring, defaultdict for expertise map accumulation |

### Repo change detection
| Technology | Purpose |
|---|---|
| watchdog | Python library that watches the file system for changes in the .git folder |

### Python environment
| Technology | Purpose |
|---|---|
| pip + requirements.txt | dependency management |
| python-dotenv | load REPO_PATH and other config from a .env file |

### Why this stack
- Everything runs locally with no cloud dependency
- SQLite means zero database setup for the end user
- FastAPI auto-generates interactive API docs at /docs which helps during development
- SQLModel removes boilerplate by combining database models and API schemas in one class
- GitPython avoids shelling out to git commands directly and handles edge cases cleanly
- scikit-learn TF-IDF is a proven, simple, and explainable algorithm for keyword-to-module matching

## Why not use manual specialties as the main source of truth
Manual specialties can be useful as a supplement, but the repository history is more reliable because it reflects actual historical work done. It reduces bias and keeps assignment grounded in real contribution patterns.

## Why the app runs locally
The requirement says the app should be cloneable, installable, and able to point at any local repository. This means the final product is a local software application that runs on the user's machine, not a hosted SaaS service. The user chooses which git repository to analyze when starting the app or configuring it.

## Developer notification and accept/decline workflow

### Dashboard vs email

The developer dashboard is the primary interface. It is preferred over email as the main interaction surface because:

- the app is local and has no external service dependency
- a dashboard provides a central view of all tasks, statuses, and workload
- email only delivers a one-time notification and cannot easily support status updates

Email is recommended as an optional supplement, not a replacement.

### Accept or decline

Developers should be able to accept or decline an assigned task. This is important because:

- a developer may be overloaded, on leave, or not the right person despite their score
- forced assignment with no recourse reduces trust in the system
- accept/decline creates a feedback loop for improving future assignments

When a developer declines, the system picks the next-best scored developer and repeats. A maximum reassignment limit (e.g. 3) should be set, after which the task is flagged as unassigned for manual review.

Developers should provide a brief reason when declining:
- overloaded
- not the right area
- needs more context

The reason is stored and can be used to improve future scoring over time.

### Assignment status flow

```
Bug submitted
    ↓
System picks top-scored developer → status: pending acceptance
    ↓
Developer sees task on dashboard (or receives email notification)
    ↓
    ├── Accepts → status: in progress
    └── Declines (with reason) → next-best developer → status: pending acceptance
                                      ↓
                                 repeat up to max reassignments
                                      ↓
                                 if limit reached → status: unassigned (manual review)
```

## Dashboard access and network considerations

### Same network (LAN)

The app binds to `0.0.0.0` instead of `127.0.0.1`. All developers on the same WiFi or office network can access the dashboard at the host machine's local IP address:

```
http://192.168.1.x:8000
```

This requires no deployment and works out of the box.

### Distributed team (different networks)

LAN access breaks when team members are remote. Options:

| Option | How it works | Tradeoffs |
|---|---|---|
| ngrok / cloudflared | tunnels local app to a public URL | URL changes on restart unless paid plan |
| Deploy to small VPS | run app on DigitalOcean or Fly.io | proper solution, minimal extra complexity |
| Email notification only | no network access needed for notifications | accept/decline links still need reachable backend |

### Email for notifications

Email solves the notification problem regardless of network because delivery does not require the app to be reachable. The developer only needs an internet connection to receive the message.

However, if accept/decline links are embedded in the email, those links call back to the backend API. If the backend is not publicly reachable, those links will not work.

Practical resolution:

| Scenario | Recommended approach |
|---|---|
| Team on same network | Dashboard only |
| Team distributed, notification only | Email works perfectly |
| Team distributed, accept/decline in email | Email + ngrok or cloud deployment |
| Team distributed, full workflow | Cloud deployment is the clean answer |

### Design for future cloud migration

The app should be built locally first but architected so switching to cloud is a single config change:

- use SQLModel so swapping SQLite for PostgreSQL only requires changing the database URL in `.env`
- keep all environment-specific config in `.env` (database URL, repo path, SMTP credentials, public base URL)
- this satisfies the original local requirement and leaves the door open for cloud deployment as phase two

## Bug submission form — UX flow

### Assignment is returned immediately

The backend computes the assignment synchronously in a single request — save bug, run matching, assign, return result. The full assignment result is available the moment the form is submitted. There is no need to poll or wait.

### Submission flow step by step

1. User fills in the form (title, description, module dropdown, severity)
2. User clicks Submit
3. Submit button disables and shows a loading spinner to prevent double submission
4. React calls the backend API with `fetch`
5. API responds with the bug record and assignment details
6. React stores the result in state and flips a `submitted` flag
7. The form is replaced by a success card on the same page — no page reload

### Success card content

```
✓ Bug report submitted

  Title:       "Login crashes after password reset"
  Module:      auth/
  Assigned to: Alice Chen  (alice@company.com)
  Score:       47.3

  [ Submit another bug ]     [ View all bugs → ]
```

Two action buttons:
- Submit another bug — resets the form on the same page without navigating away
- View all bugs — navigates to the bug list or developer dashboard

Do not auto-redirect. The submitter should be able to see who was assigned before deciding what to do next.

### Error state

If the backend returns an error (no developers found, repo not yet analyzed):

```
✗ Could not assign this bug

  The report was saved but no developer could be matched.
  Reason: no expertise data found for module "auth/"

  [ Try again ]     [ View unassigned bugs → ]
```

### What NOT to do

- Do not show a generic success toast and nothing else — the assignment result is useful and should be visible
- Do not auto-redirect after a timeout — this hides the result and is disorienting
- Do not reload the whole page — use React state to swap between the form view and the success view

### How React state switching works

In a traditional HTML form, clicking submit causes the browser to reload the entire page. React prevents this with `e.preventDefault()` and instead manages what is shown using a state variable.

```tsx
const [submitted, setSubmitted] = useState(false);
const [result, setResult] = useState(null);

async function handleSubmit(e) {
  e.preventDefault();           // stops browser reload
  const res = await fetch("/api/bugs", { method: "POST", body: ... });
  const data = await res.json();
  setResult(data);              // store assignment result
  setSubmitted(true);           // flip to success view
}

if (submitted) {
  return <SuccessCard result={result} />;   // show result
}

return <BugForm onSubmit={handleSubmit} />; // show form
```

When `submitted` is true, React renders the success card instead of the form. No page reload, no flash, no lost state. Clicking "Submit another bug" just calls `setSubmitted(false)` to flip back to the form instantly.

## Rate limiting

To prevent one person from spamming the bug submission form, use `slowapi` — the standard rate limiting library for FastAPI.

```python
@limiter.limit("5/minute")
async def create_bug(request: Request, bug: BugCreate):
    ...
```

- Limit: 5 submissions per minute per IP address
- Exceeded requests receive HTTP 429 Too Many Requests
- Frontend catches 429 and shows: "You are submitting too quickly. Please wait before submitting again."
- Rate limit value is configurable in `.env`

## Concurrency — simultaneous submissions

FastAPI on Uvicorn uses an async event loop. Since assignment work is mostly I/O (SQLite reads and writes), it handles concurrent requests without blocking.

| Simultaneous submissions | Behaviour |
|---|---|
| 1–10 | no issue |
| 10–50 | fine; SQLite may serialize writes briefly |
| 50–200 | SQLite write lock becomes a bottleneck |
| 200+ | switch to PostgreSQL via `.env` config change |

SQLite only allows one writer at a time. For a local team of 5–20 developers this is never a problem in practice. The architecture is designed so swapping to PostgreSQL is a single config change if needed.

## Duplicate detection — same issue reported by multiple people

When a new bug is submitted, compare it against recent open bugs using TF-IDF cosine similarity before saving.

```python
def find_duplicates(new_bug_text, existing_bugs, threshold=0.85):
    all_texts = [b.title + " " + b.description for b in existing_bugs]
    all_texts.append(new_bug_text)
    tfidf_matrix = vectorizer.fit_transform(all_texts)
    scores = cosine_similarity(tfidf_matrix[-1], tfidf_matrix[:-1])
    return [existing_bugs[i] for i, s in enumerate(scores[0]) if s > threshold]
```

A similarity score above 0.85 is treated as a likely duplicate. The submitter sees a warning:

```
⚠ A similar bug may already exist

  "Login crashes after password reset" — filed 2 hours ago, assigned to Alice

  [ View existing bug ]     [ Submit anyway ]
```

The submission is not blocked — the user decides. If they submit anyway, the new bug is linked to the original via a `duplicate_of` field in the bugs table.

## Batching — many requests arriving at once

For a typical team, batching is not necessary. Each assignment takes ~10–30ms, so 10 concurrent requests finish in under a second even when processed individually.

If high volume ever requires it, a background queue approach can be used:

```
Requests arrive
    ↓
Each bug is saved immediately to DB
    ↓
Bug IDs are pushed onto an in-memory queue
    ↓
Background worker drains the queue every 500ms
    ↓
Worker vectorizes all pending descriptions in one TF-IDF pass
    ↓
Assigns all bugs in one batch, updates all assignment records
```

This is only worth building for high-traffic scenarios. For a small local team, process each submission immediately as it arrives — simpler and sufficient.

## No-match fallback — when the algorithm cannot find a developer

Three common reasons a match may fail:

- the affected module is new and no developer has touched it yet
- the bug description is too vague to match any module keywords
- all developers have zero score for the relevant module

### Fallback cascade (in order)

```
1. TF-IDF match against module expertise scores
   → found → assign with High confidence

2. Match against commit messages instead of file paths
   (developer may have worked in the area without a clear module path)
   → found → assign with Medium confidence

3. Assign to the developer with the highest total score across all modules
   (most active contributor overall)
   → assign with Low confidence

4. No developers exist at all
   → mark bug as unassigned → flag for manual review
```

### Confidence level shown in the UI

The success card after submission shows the confidence of the assignment:

```
Assigned to: Alice Chen    Confidence: High   (direct module match)
Assigned to: Bob           Confidence: Low    (no direct match — most active contributor)
```

Low confidence assignments are also highlighted in an "uncertain assignments" section on the developer dashboard so a team lead can review them.

## Local app vs SaaS — scale perspective

Most of the concurrency and performance concerns discussed above are real engineering problems, but they are not concerns for this project at its current scope.

### For a local app used by a small team

| Concern | Reality |
|---|---|
| Rate limiting spam | unlikely — you know your teammates |
| Concurrency overload | unlikely — maybe 5 developers, not 5000 |
| SQLite write lock | not a real problem at this scale |
| Batching for performance | not needed |
| Duplicate storms | unlikely |

### For a SaaS or cloud-deployed app

| Concern | Reality |
|---|---|
| Rate limiting | thousands of users, bots, or abuse attempts |
| Concurrency | simultaneous submissions from many users |
| SQLite | cannot handle the load — PostgreSQL becomes necessary |
| Batching | TF-IDF on thousands of descriptions per second benefits from matrix batching |
| Duplicates | same bug reported by hundreds of users at once |

The architecture of this app is already designed to scale if needed — SQLModel abstracts the database so swapping SQLite for PostgreSQL is a single config change. These concerns are worth understanding for the full design space but the simpler local-first path is correct for now.

## What batching actually means

Batching means collecting multiple individual items and processing them together in one operation instead of one by one.

### Database batching
Instead of 10 separate INSERT statements:
```python
for bug in bugs:
    db.insert(bug)
```
Do one bulk insert:
```python
db.bulk_insert(bugs)
```

### ML batching
Instead of running TF-IDF on one description at a time, feed all pending descriptions into the vectorizer in one call:
```python
vectorizer.transform([bug1_text, bug2_text, bug3_text])
```
scikit-learn is optimized for matrix operations — processing 10 items together is not 10x the cost of processing 1.

### Is batching relevant for this project?

No. TF-IDF matching takes ~5–20ms per bug. Even 10 bugs arriving simultaneously finish in well under a second processed individually. There is no meaningful gain from batching at this scale. It is a valid technique for high-volume SaaS systems but not a concern here.

## SQLite vs PostgreSQL — why SQLite has write limits

SQLite is a file-based database. The entire database is a single `.db` file on disk with no separate server process. This design has one key limitation: only one writer at a time.

### How SQLite handles writes

When any part of the app writes to the database, SQLite places a lock on the entire file. Every other write must wait until that lock is released.

```
Request A writes bug #1  →  lock acquired
Request B tries to write →  waits...
Request C tries to write →  waits...
Request A finishes       →  lock released
Request B writes         →  lock acquired
```

Reads are fine with many simultaneous readers. The bottleneck is writes only.

### Why this is fine locally

A local team of 5–10 developers submitting bug reports every few minutes means a handful of writes per hour. SQLite handles thousands of writes per second under ideal conditions, and the lock is held for only 1–5ms per write. The chance of two writes colliding is nearly zero.

### Why this breaks at SaaS scale

If 500 users submit bug reports at the same moment, each submission triggers at least two writes (bug record + assignment record). That is 1000 writes queuing behind a single file lock. Response times balloon, users see timeouts, and the app becomes unusable.

### What PostgreSQL does differently

PostgreSQL is a full database server running as a separate process. It uses row-level locking instead of file-level locking, so multiple transactions can write to different rows simultaneously without blocking each other.

```
Request A writes bug #1  →  row lock on row 1
Request B writes bug #2  →  row lock on row 2  (no waiting)
Request C writes bug #3  →  row lock on row 3  (no waiting)
```

It also provides a connection pool, query planner, and other mechanisms built for concurrent production load.

### Summary

SQLite locks the whole file for every write — correct for a small local team, breaks under many simultaneous users. PostgreSQL uses row-level locks and a server process designed for concurrent access. For this project SQLite is the right choice. Switching to PostgreSQL is a future option if the app ever needs to handle serious traffic, and it requires only a single `.env` config change due to the SQLModel abstraction.

## App pages

The app has two main pages and one optional page:

| Route | Purpose | Audience |
|---|---|---|
| /submit | Bug submission form | Anyone reporting a bug |
| /dashboard | Developer task management | Developers managing their assigned tasks |
| /bugs (optional) | Full bug list with all statuses | Team lead overview |

### /submit — Bug submission form

**Audience:** anyone reporting a bug

**Form fields:**
- title
- description
- affected module — dynamic dropdown fetched from `/api/modules`, populated from the target repo's directory structure
- severity or priority (optional)

**After submission:**
- submit button disables and shows a loading spinner
- form is replaced by a success card showing:
  - bug title
  - module
  - assigned developer name and email
  - confidence level (High / Medium / Low)
- two buttons: Submit another bug (resets the form) and View all bugs (navigates away)

**Error states:**
- duplicate warning if a similar bug already exists, with option to view existing bug or submit anyway
- error card if assignment failed (repo not ready, no match found)
- 429 message if rate limit is exceeded

---

### /dashboard — Developer dashboard

**Audience:** developers managing their assigned tasks

**Contents:**
- developer selector — dropdown to choose who you are (no login required in the simple version)
- list of task cards filtered to the selected developer, each showing:
  - bug ID, title, module, confidence level
  - time since filing
  - current status label
  - action buttons depending on status (see buttons-per-status table)
- uncertain assignments section — low confidence matches flagged for team lead review
- data refreshes automatically via React Query polling every 10–15 seconds

---

### /bugs — Full bug list (optional)

**Audience:** team lead

**Contents:**
- all bugs across all developers
- all assignment statuses
- unassigned bugs flagged for manual review
- overview of team workload distribution

Not required for the first version but useful for team lead oversight.

## Developer dashboard

### Purpose

The submission success card shows the result to the bug reporter. The dashboard is a separate page that serves a different audience — developers who need to see what has been assigned to them, and team leads who need to see all bugs and their statuses. Both pages are necessary.

### Task cards

The dashboard shows one task card per bug assigned to the developer:

```
┌─────────────────────────────────────────────┐
│  My Assigned Tasks                          │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ BUG-42  Login crashes after reset   │    │
│  │ Module: auth/   Confidence: High    │    │
│  │ Filed: 2 hours ago                  │    │
│  │ Status: ● Pending acceptance        │    │
│  │                                     │    │
│  │  [ Accept ]      [ Decline ▾ ]      │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ BUG-38  Checkout fails for prepaid  │    │
│  │ Module: billing/  Confidence: High  │    │
│  │ Filed: 1 day ago                    │    │
│  │ Status: ● In progress               │    │
│  │                                     │    │
│  │  [ Mark as Resolved ]               │    │
│  └─────────────────────────────────────┘    │
└─────────────────────────────────────────────┘
```

### Buttons shown per status

| Status | Buttons shown on card |
|---|---|
| pending_acceptance | Accept, Decline |
| accepted | Start Working, Decline |
| in_progress | Mark as Resolved |
| resolved | no buttons — shows ✓ Resolved label |

## Assignment status — how it updates

### Source of truth

The `resolved` status (and all status changes) come from the developer clicking a button on the dashboard. The system cannot detect completion automatically — the developer is the one who knows when a task is done.

### Status transition flow

```
pending_acceptance  →  accepted  →  in_progress  →  resolved
                    ↓
                  declined  →  reassigned to next-best developer
```

### What triggers each status change

| Status | What triggers it |
|---|---|
| pending_acceptance | backend sets automatically on assignment creation |
| accepted | developer clicks Accept |
| in_progress | developer clicks Start Working |
| resolved | developer clicks Mark as Resolved |
| declined | developer clicks Decline and selects a reason |

### Database fields on the assignments table

| Field | Purpose |
|---|---|
| status | current state |
| accepted_at | timestamp when accepted |
| resolved_at | timestamp when marked resolved |
| decline_reason | reason text if declined |

### How the PATCH call works

When a developer clicks Mark as Resolved:

```
PATCH /api/assignments/42
body: { "status": "resolved" }

Backend: UPDATE assignments SET status='resolved', resolved_at=now() WHERE id=42
```

React Query then re-fetches and the card updates without a page reload.

### How the dashboard stays current

React Query polls `GET /api/assignments` every 10–15 seconds. When any developer updates a status, everyone viewing the dashboard sees the updated state on the next poll — no websockets needed at this scale.

## Developer identity on the dashboard

The dashboard needs to know which developer is viewing it to show their tasks. Two approaches:

**Simple — no login:**
Developer selects their name from a dropdown when opening the dashboard. The app filters tasks by that name. No passwords or sessions required. Suitable for a trusted local team.

**Proper — with login:**
Developers have accounts and log in. The dashboard shows only their tasks based on their session. More complex to build but more secure.

For a local team tool, the simple dropdown approach is recommended for the first version.



This project is best understood as a local bug-assignment tool that learns developer expertise from repository history and uses that to assign incoming bug reports to the most relevant engineer. The product includes a web UI for bug submission and a developer dashboard, while the backend analyzes git history and keeps expertise data current as the repo changes. Developers can accept or decline assignments, triggering reassignment to the next best match. The app runs on LAN by default and can be extended to support remote teams via ngrok or cloud deployment without changing the core code.

## Assignment performance

Bug submission and assignment is very fast — well under 100ms in normal conditions.

| Step | Estimated time |
|---|---|
| Validate request (Pydantic) | < 1ms |
| Save bug to SQLite | 1–5ms |
| Load expertise map from memory | < 1ms |
| Tokenize bug text | 1–2ms |
| TF-IDF matching | 5–20ms |
| Pick top developer | < 1ms |
| Save assignment to SQLite | 1–5ms |
| Serialize and return JSON | < 1ms |
| **Total** | **~10–30ms** |

Anything under 100ms feels instant to a human. The loading spinner on the submit button will barely appear before the success card shows.

The only genuinely slow operation is the initial git repo scan at startup. On a large repo with thousands of commits this can take several seconds to a minute. That happens once when the server boots, not during bug submission.

## Startup scan and the race condition

### What "startup" means

Startup is when the server process boots — when the user runs `uvicorn main:app`. At that point the backend begins scanning the target git repository to build the commits table and expertise map. This initial scan can take anywhere from a few seconds to a minute depending on repo size.

### The race condition

A user could open the browser and submit a bug before the scan finishes. If the expertise map is empty at that point, the assignment engine has no data to work with.

### Backend guard

The server tracks scan state in memory:

```python
app.state.repo_ready = False
app.state.scan_progress = 0   # 0–100

# set to True when scan completes
```

The bug submission endpoint checks this before attempting assignment:

```python
if not app.state.repo_ready:
    raise HTTPException(
        status_code=503,
        detail="Repository is still being analyzed. Please try again shortly."
    )
```

The backend always guards this independently of the frontend. Never rely only on the UI to block early submissions.

### Frontend status polling

A dedicated status endpoint is exposed:

```
GET /api/repo/status
→ { "ready": false, "progress": 42, "message": "Scanning commits... 42%" }
```

React Query polls this every 2 seconds on page load. While the scan is in progress, the UI shows a banner and disables the submit button:

```
⏳ Analyzing repository history... 42%
   Bug submission will be available shortly.
```

Once `ready: true` the banner disappears and the form becomes active.

### Frontend states for repo readiness

| State | What the UI shows |
|---|---|
| Scan in progress | top banner with progress percentage, form disabled |
| Scan complete | banner disappears, form enabled |
| Bug submitted before ready (edge case) | error card: "Repository not ready yet" |
| Scan failed | error banner with a retry option |

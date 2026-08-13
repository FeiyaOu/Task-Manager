# Spec Index — Start Here

> Map of the `spec/` folder: **which file answers which question.** Read this first, then
> jump to the specific file. Order below follows the build/dependency order.

## Quick lookup: "Where do I find…?"

| I need to know… | Look in |
|---|---|
| What the product is and why it exists | [project-basic-info.md](project-basic-info.md) |
| Data model, tables, scoring formula, expertise-map design | [project-basic-info.md](project-basic-info.md) |
| Folder/file layout, service seams, API surface, build order | [project-structure.md](project-structure.md) |
| How each feature spec is formatted + traceability rule | [features/README.md](features/README.md) |
| How to read git history → commit-file records | [features/01-git-analyzer.md](features/01-git-analyzer.md) |
| Recency-decay scoring, module normalization, `commit_count` | [features/02-scoring.md](features/02-scoring.md) |
| Ranking developers for a bug (the ranked-list contract) | [features/03-matcher.md](features/03-matcher.md) |
| Persisting a bug → task, thresholds, `TaskStatus` state machine | [features/04-assignment.md](features/04-assignment.md) |
| HTTP endpoints, request/response shapes, CORS, startup | [features/05-api.md](features/05-api.md) |
| Build sequencing, SQLite, when to start frontend, matcher-vs-assignment, plumbing beyond the 5 specs | [dev-notes.md](dev-notes.md) |
| Interview context, why this scope, likely live extension | [../docs/design-discussion.md](../docs/design-discussion.md) *(gitignored notes)* |

## The files, by role

### Vision & data model
- **[project-basic-info.md](project-basic-info.md)** — the source of truth for *what* and *why*.
  Product goal, "repository = the analyzed repo, not this app", developer identity (git author
  email), expertise-map two-layer storage (SQLite + in-memory dict), commits table, score
  formula (`lines_changed × e^(−λ·days_ago)`), incremental-refresh strategy, UI flow.

### Architecture & plan
- **[project-structure.md](project-structure.md)** — the *how it's organized*. Directory tree,
  the four independent seams (git_analyzer / scoring / matcher / assignment), the ranked-list
  design bet, data-model table grain, v1 API surface, **build order**, v1 scope guardrails.

### Feature specs (TDD units — each Rule → ≥1 test)
Build/dependency order:
1. **[features/01-git-analyzer.md](features/01-git-analyzer.md)** — repo → `CommitFileRecord` list. Pure, no DB.
2. **[features/02-scoring.md](features/02-scoring.md)** — records → per-(dev,module) scores. Pure, no DB.
3. **[features/03-matcher.md](features/03-matcher.md)** — bug + expertise → **ranked** candidates. Pure.
4. **[features/04-assignment.md](features/04-assignment.md)** — orchestrates: save bug → rank → assign → persist task.
5. **[features/05-api.md](features/05-api.md)** — FastAPI routers over the services.
- **[features/README.md](features/README.md)** — spec template + traceability rule (no code without a failing test).

### Working notes
- **[dev-notes.md](dev-notes.md)** — clarifications & sequencing decided during dev: TDD/branch
  strategy, matcher-vs-assignment table, SQLite needs no install, frontend timing, backend
  plumbing beyond the 5 specs.
- **[../docs/design-discussion.md](../docs/design-discussion.md)** — interview reasoning (scope
  choices, likely live extension = accept/decline + reassignment). Gitignored; not a deliverable.

## Detailed topic map (what's inside each file)

Use this when you need a *specific* fact and want to jump straight to the right section.

### [project-basic-info.md](project-basic-info.md) — vision & data model
- Project goal; "repository" = the analyzed repo, **not** this app
- Developer definition (identified by git author name + email)
- Product UI flow (bug submission form fields; developer dashboard)
- Assignment logic (6-step flow: save → load map → compare → select → save task → return)
- Expertise map storage design: SQLite table **+** in-memory Python dict; load-on-startup flow
- `expertise` table structure (one row per developer × module)
- In-memory dict shape (`email → {module → score}`)
- `commits` table (one row per commit × file — raw git data)
- **Score calculation**: module normalization, `score = Σ lines_changed × recency_weight`,
  `recency_weight = e^(−λ·days_ago)`, λ = 0.01 example
- Incremental update strategy (recompute affected pairs from scratch; `last_analyzed_commit_hash`)
- What to extract from `git log`; why GitPython
- Why SQLModel/SQLAlchemy
- Keeping current (startup / periodic / watcher); dynamic `/api/modules` dropdown
- Architecture overview (frontend / backend / db / git layer / matcher / watcher)

### [project-structure.md](project-structure.md) — architecture & plan
- Design principles: the **four independent seams** (git_analyzer, scoring, matcher, assignment)
- Full directory tree (backend `app/` modules, `services/`, `models/`, `schemas/`, `routers/`, frontend)
- "The one function that makes extension easy" — `rank_developers` ranked-list contract
- Extension table (accept/decline, workload balancing, explain, confidence, manual override)
- Data model (v1) — table grain + extension-ready fields
- API surface (v1) — the five endpoints
- **Build order** (1 scaffold → 8 watcher)
- v1 scope guardrails (in vs. out)

### [dev-notes.md](dev-notes.md) — clarifications & sequencing
- TDD one-seam-at-a-time; git_analyzer/scoring need **no** DB foundation
- Git workflow (branch per feature)
- **matcher vs assignment** comparison table + relationship
- SQLite needs no install (stdlib; `create_db_and_tables()` makes the file)
- When to start the frontend (needs `/api/modules` + `/api/bugs` first; step 6)
- Backend components **beyond the 5 specs** (foundation, expertise_cache, scoring-persistence, watcher, repo router)

### Feature specs — each follows: Purpose / Inputs / Outputs / Rules / Edge cases / Out of scope
- **[01-git-analyzer.md](features/01-git-analyzer.md)**: per-(commit×file) records; author email; UTC; skip merges; binary→0/0; `since_commit` incremental; oldest→newest; errors `NotAGitRepositoryError` / `UnknownCommitError`.
- **[02-scoring.md](features/02-scoring.md)**: module normalization (`auth/login.py`→`auth/`, root→`./`); `lines_changed`; recency weight; per-pair score; distinct-commit `commit_count`; recompute-from-scratch.
- **[03-matcher.md](features/03-matcher.md)**: ranked list (never single winner); sort by score desc; module-driven relevance; `matched_modules` reasons; deterministic tie-break by email; exclude zero-expertise.
- **[04-assignment.md](features/04-assignment.md)**: save bug first; call matcher; threshold → `PENDING` vs `UNASSIGNED`; persist task with state/score/reasons/`reassign_count`; `TaskStatus` state machine.
- **[05-api.md](features/05-api.md)**: `POST /api/bugs`, `GET /api/tasks`, `GET /api/modules`, `POST /api/repo/refresh`, `GET /api/repo/status`; CORS; `0.0.0.0` bind; startup cache load.

## Reading paths by goal

- **New to the project?** → [project-basic-info.md](project-basic-info.md) → [project-structure.md](project-structure.md) → this folder's feature specs in order.
- **About to implement a feature?** → its `features/0N-*.md` (the Rules are your tests) → [dev-notes.md](dev-notes.md) for sequencing gotchas.
- **Deciding what to build next / how to sequence?** → [project-structure.md](project-structure.md) build order → [dev-notes.md](dev-notes.md).
- **Prepping for the live extension?** → [../docs/design-discussion.md](../docs/design-discussion.md) + [features/03-matcher.md](features/03-matcher.md) + [features/04-assignment.md](features/04-assignment.md).

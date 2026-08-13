---
name: start-feature
description: "Use when starting a new feature/phase in the Task-Manager project. Runs the standard git + TDD workflow: switch to main, pull, create a feat branch, then write tests-first (red) and implementation (green) from the matching spec/features file, and make a single combined commit. Trigger phrases: start a feature, start feature N, begin next feature, new feature branch, start the next phase."
---

# Start a New Feature

Standard workflow for building one feature/phase in this repo. Follow the steps in order.
**Do NOT push** — the user pushes to remote themselves as the final step.

## Steps

### 1. Sync main and branch off it
Run these from the repo root:
```bash
git switch main
git pull origin main
git switch -c feat/<NN>-<slug>
```
- `<NN>` = zero-padded feature number (e.g. `03`), `<slug>` = short name (e.g. `matcher`).
- Match the number/name to the spec file in `spec/features/` (e.g. `03-matcher.md` → `feat/03-matcher`).
- Confirm the branch was created and the tree is clean before writing code.

### 2. Read the spec
Open the matching `spec/features/<NN>-*.md`. Every numbered **Rule** and every **Edge case**
must become at least one test. If anything is ambiguous, check `spec/README.md` for where the
detail lives before coding.

### 3. TDD red — write the tests first
- Add `backend/tests/test_<name>.py`.
- One test per Rule/edge case, with a short comment tracing each back to its Rule.
- Reuse existing fixtures in `backend/tests/conftest.py` (e.g. `make_repo`, `FIXED_NOW`,
  `SeededCommit`). Pure functions can build their inputs directly — no git repo needed.
- Run and confirm they fail for the right reason (usually `ModuleNotFoundError`):
```bash
cd backend && source .venv/bin/activate && python -m pytest tests/test_<name>.py -q
```

### 4. TDD green — implement
- Create the module under `backend/app/services/` (add `__init__.py` if the package is new).
- Implement the minimum to satisfy the spec contract. Keep the seam clean: a service knows
  only about its own inputs/outputs (git_analyzer → records; scoring → expertise; etc.).
- Run the **full** suite until everything passes:
```bash
cd backend && source .venv/bin/activate && python -m pytest -q
```

### 5. Commit (one combined commit)
Stage only the feature's files and make a single green commit (tests + implementation together —
every commit stays green; no separate failing "red" commit):
```bash
git add backend/app/services/<name>.py backend/tests/test_<name>.py
git commit -m "feat(<slug>): <one-line summary> (spec <NN>)" \
           -m "<what it does>. Adds N tests, one per Rule/edge case in spec/features/<NN>-*.md."
```

### 6. Hand off
Report the branch name, the commit hash, and the test count. Then suggest a PR title and
description the user can paste when they open the PR. **Stop there** — the user pushes and opens
the PR themselves.

Suggested PR **title**:
```
feat(<slug>): <one-line summary> (spec <NN>)
```

Suggested PR **description**:
```markdown
## Summary
<1-2 sentences: what this feature does and which seam it implements.>

## Spec
Implements `spec/features/<NN>-*.md`.

## Changes
- `backend/app/services/<name>.py` — <what was added>
- `backend/tests/test_<name>.py` — N tests, one per Rule/edge case

## Testing
- [x] Full suite green: `cd backend && source .venv/bin/activate && python -m pytest -q`
- [x] Every Rule and edge case in the spec maps to at least one test
```

## Project conventions (reminders)
- Tests run from `backend/` with the venv active: `source .venv/bin/activate`.
- `now` and other time inputs are injected for determinism — never call `datetime.now()` inside
  scored/tested logic.
- Persistence and API wiring are separate later phases; keep pure services free of DB/HTTP code
  unless the spec for that phase says otherwise.
- Build order: git_analyzer → scoring → matcher → assignment → api (see `spec/project-structure.md`).

# Feature: Scoring / Expertise

## Purpose
Turn raw commit-file records into per-(developer, module) expertise scores using
recency-weighted line changes.

## Inputs
- `records: list[CommitFileRecord]` — from the git analyzer.
- `now: datetime` — injected reference time (NOT `datetime.now()` inside the function,
  so tests are deterministic).
- `lambda_decay: float` — exponential decay constant (default `0.01`).

## Outputs
- `dict[str, dict[str, ExpertiseCell]]` — mapping:
  `author_email -> { module_path -> ExpertiseCell }`
- `ExpertiseCell`:
  - `score: float`
  - `commit_count: int`

## Rules
1. A file path is normalized to its module = top-level directory + `/`
   (e.g. `auth/login.py` -> `auth/`).
2. A file at repo root (no directory) normalizes to module `./`.
3. `lines_changed = lines_added + lines_deleted` per record.
4. `recency_weight = e^(-lambda_decay * days_ago)` where
   `days_ago = (now - committed_at).total_seconds() / 86400`.
5. `score` for a (developer, module) pair =
   `sum(lines_changed * recency_weight)` over all matching records.
6. With `lambda_decay = 0.01`, a commit 100 days old contributes
   `lines_changed * 0.3679` (±1e-3).
7. `commit_count` = number of **distinct** commit hashes touching that (developer, module) pair.
8. Score is recomputed from scratch for affected pairs (no incremental accumulation
   on top of stale weights).

## Edge cases
- Empty `records` → empty dict.
- Same developer, same module, multiple commits → scores sum; `commit_count` counts
  distinct commits (a commit touching 2 files in the module counts once).
- `days_ago = 0` (commit "today") → weight `1.0`.

## Out of scope
- Persistence / upsert into SQLite (thin wrapper consumes this output).
- Matching bugs to developers (see `03-matcher.md`).

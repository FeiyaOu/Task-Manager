# Feature: Matcher

## Purpose
Given a bug report and the expertise map, return developers ranked from best to worst
match, each with a score and the reasons (matched modules).

This is the single most important function for the interview extensions
(accept/decline needs "next-best"; workload balancing re-ranks; "explain" needs reasons).

## Inputs
- `bug: BugInput` with at least:
  - `title: str`
  - `description: str`
  - `modules: list[str]`   (chosen from the multi-select dropdown; may be empty)
- `expertise_map: dict[str, dict[str, float]]` — `author_email -> {module -> score}`.

## Scoring (coverage-weighted, soft)
A developer's matched modules = the selected modules plus any module whose path shares a word
with the bug's title/description. Score = `sum(expertise over matched) * (1 + covered)/(1 + |selected|)`,
where `covered` = how many selected modules the developer has expertise in. This rewards developers
who **span more of the selected modules**, not just whoever has the largest single number. With no
selection the factor is `1.0` (pure keyword matching).

### Module relevance weighting (optional)
`rank_developers` accepts an optional `module_relevance: dict[str, float]` — a per-module
relevance score for the bug text, supplied by the TF-IDF `ModuleIndex` (see below). When
provided, an unselected module contributes `expertise * relevance` instead of a binary
token-overlap weight; selected modules always weigh `1.0`; a module with zero relevance is
excluded. When `module_relevance` is omitted the matcher falls back to binary path-token
overlap, so existing behaviour is unchanged.

### ModuleIndex (TF-IDF over commit messages)
`ModuleIndex.build(session, module_depth)` builds one document per module from its stored
commit messages plus file-path tokens, fits a `TfidfVectorizer`, and exposes
`relevance(text) -> {module: cosine_similarity}`. This lets bug text like *"billing"* find a
`payments/` module when developers described that work as *"fix billing"* in their commits.
Enrichment (commit messages) supplies vocabulary; TF-IDF (IDF) down-weights common words like
*fix*/*update*. It is still lexical, not semantic — true synonyms need embeddings (out of scope).

## Outputs
- `list[Candidate]`, ordered best → worst. Each `Candidate`:
  - `developer_email: str`
  - `score: float`
  - `matched_modules: list[str]`   (why this developer matched)

## Rules
1. Return a **ranked list**, never a single winner. `result[0]` is the top match;
   `result[1]` is the next-best (used for reassignment).
2. The list is sorted by `score` descending.
3. When `bug.module` is provided, a developer's relevance is driven primarily by their
   expertise score in that module.
4. `matched_modules` contains every module that contributed to a developer's score.
   Keyword matching tokenizes the **full module path** (e.g. `Engine/Physics/` yields
   `engine`, `physics`), so a bug mentioning any path segment matches that module.
5. Ties (equal score) are broken deterministically by `developer_email` ascending,
   so ordering is reproducible in tests.
6. A developer with zero relevant expertise is excluded from the result.

## Edge cases
- Empty `expertise_map` → return `[]`.
- No developer matches the bug's module/keywords → return `[]`.
- Bug with empty description and no module → return `[]` (nothing to match on).

## Out of scope
- Persisting the assignment / task state (see `04-assignment.md`).
- The TF-IDF implementation detail may evolve; the **contract above is fixed**.

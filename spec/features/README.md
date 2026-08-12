# Feature Spec Template

Every feature spec in this folder follows the structure below. Each numbered **Rule**
must be concrete enough to become at least one test (TDD red step).

```markdown
# Feature: <name>
## Purpose        (one sentence)
## Inputs         (types, shapes)
## Outputs        (exact return contract)
## Rules          (numbered, testable — each becomes >=1 test)
## Edge cases     (empty, malformed, boundary)
## Out of scope
```

## Build order (dependency order = TDD-friendly)

1. `01-git-analyzer.md`
2. `02-scoring.md`
3. `03-matcher.md`
4. `04-assignment.md`
5. `05-api.md`

## Traceability rule

- Every Rule maps to >=1 test.
- Every test traces back to a Rule.
- No production code without a failing test first. If you cannot write the test,
  the spec is not precise enough — fix the spec.

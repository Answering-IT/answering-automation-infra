# Backlog

Source of truth for the **auto-maintain** workflow. The workflow reads this
file, picks the next eligible item, hands it to Claude, and opens a PR.

Format spec: See [answering-automation-infra docs](https://github.com/Answering-IT/answering-automation-infra/blob/main/docs/BACKLOG_FORMAT.md)

---

## How items are picked

1. Filter to `status: ready`.
2. Sort by `priority` (P0 > P1 > P2), then by appearance order in this file.
3. Take the first one.
4. Skip the item if its `id` already has an open PR with label `automated`.

---

## Items

```yaml backlog
id: example-trial-task
title: "Add a basic smoke test"
status: ready
priority: P2
labels:
  - tests
  - good-first-task
context: >
  Trial item to validate the auto-maintain pipeline works end-to-end.
  Adds a simple smoke test that imports the main package and asserts
  something trivial passes.
acceptance_criteria:
  - "A new test file main_test.go exists"
  - "Test imports the main package successfully"
  - "Test passes when run with go test ./..."
  - "All existing tests still pass"
  - "golangci-lint run and go build ./... both pass"
files_to_touch:
  - main_test.go
tests_required:
  - "main_test.go contains at least one test function"
notes: >
  Keep this minimal. The goal is to validate the pipeline, not implement
  complex functionality.
```

```yaml backlog
id: example-template
title: "Template — replace with real items as you go"
status: blocked
priority: P2
labels:
  - example
context: >
  This is the canonical example of the format. Copy it, change the id,
  flip status to `ready`, and the next workflow run will pick it up.
acceptance_criteria:
  - "Clear, testable bullet 1"
  - "Clear, testable bullet 2"
files_to_touch:
  - path/to/likely/file.go
tests_required:
  - "path/to/likely/file_test.go covers the new branch"
notes: >
  Always blocked. Never picked. Just a reference.
```

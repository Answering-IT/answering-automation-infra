# Backlog format

The auto-maintain workflow (Fase 4) reads `BACKLOG.md` and picks the next
eligible feature to implement. This document defines the contract between the
backlog and the workflow.

---

## File location

- `BACKLOG.md` lives at the repo root.
- Items inside it are **fenced YAML blocks tagged `yaml backlog`**. The parser
  ignores any other content (prose, other code blocks, headings).
- Order in the file is preserved. Items at the top win ties.

## Item schema

Every item is one fenced block:

````markdown
```yaml backlog
id: short-kebab-case-id
title: "One line summary, sentence case"
status: ready
priority: P1
labels:
  - tag-1
  - tag-2
context: >
  One paragraph. Why does this matter? What's the motivation? The workflow
  passes this verbatim to Claude.
acceptance_criteria:
  - "Bullet 1, testable"
  - "Bullet 2, testable"
files_to_touch:
  - relative/path/to/file.py
tests_required:
  - "tests/unit/test_x.py covers the new branch"
notes: >
  Anything else Claude should know. Optional.
```
````

### Required fields

| Field | Type | Notes |
|---|---|---|
| `id` | string | Unique across the file. Kebab-case. Becomes the branch name (`auto/<id>`). |
| `title` | string | Becomes the PR title. |
| `status` | enum | One of: `ready`, `blocked`, `in_progress`, `done`. |
| `priority` | enum | `P0` (urgent), `P1`, `P2`. |
| `context` | string | What and why. Multi-line OK (use `>` YAML scalar). |
| `acceptance_criteria` | list of strings | Testable bullets. |

### Optional fields

| Field | Type | Notes |
|---|---|---|
| `labels` | list of strings | Applied to the resulting PR. |
| `files_to_touch` | list of strings | Hints to Claude about scope. |
| `tests_required` | list of strings | Specific test files to add or update. |
| `notes` | string | Anything else. |

## Status lifecycle

```
ready ──► in_progress ──► done
            │
            └──► (back to ready if PR is closed without merge)
```

- `ready`: eligible to be picked by the next workflow run.
- `in_progress`: the workflow has opened a PR for it. Updated by the workflow,
  not by humans.
- `done`: the PR was merged. Updated by the workflow.
- `blocked`: skip this item (e.g. depends on another, needs design input).

## Selection rules

1. Filter to `status: ready`.
2. Sort by priority (`P0` > `P1` > `P2`).
3. Within the same priority, top-of-file wins.
4. Skip if a PR with label `automated` already exists for this `id`.
5. Skip if `priority` is missing or invalid.

## Validation

`scripts/parse_backlog.py` validates every item on every CI run. Invalid items
fail the lint job. To check locally:

```bash
python scripts/parse_backlog.py --validate
```

To preview which item the workflow would pick next:

```bash
python scripts/parse_backlog.py --next
```

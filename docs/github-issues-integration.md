# GitHub Issues Integration

This document describes how to use GitHub Issues (created by the documentation repo workflow) as the work queue for `answering-automation-infra`, replacing BACKLOG.md files.

## Overview

Instead of maintaining a BACKLOG.md file in each consumer repo, work items are now created as GitHub Issues by the central documentation repo's `generate-backlog.yml` workflow. The automation-infra workflow can consume these issues and implement them automatically.

## How it works

### 1. Documentation workflow creates issues

The documentation repo reads feature specs and generates structured issues with metadata:

```markdown
**Target repo:** `Answering-IT/kb-rag-agent-fe`
**Effort:** medium | **Priority:** high
**Dependencies:** Setup API client, Create types

## Acceptance Criteria
- [ ] Component renders without errors
- [ ] Props are properly typed
- [ ] Unit tests pass
```

Issues are grouped by milestone (acts as epic) and labeled (feature/spike/bug, frontend/backend).

### 2. Consumer repo queries its issues

The reusable workflow uses `scripts/parse_github_issues.py` to:
- Query open issues in the consumer repo via `gh issue list`
- Parse the `**Target repo:**` field from issue body
- Filter for issues matching the consumer repo
- Map issue metadata to BacklogItem structure
- Select the next eligible item (by priority and issue number)

### 3. Claude implements the issue

Same flow as BACKLOG.md mode:
- Build prompt from issue metadata (title, acceptance criteria, labels)
- Invoke Claude Code Action via Bedrock
- Create PR with branch `auto/{issue-id}`, labels `automated` + `backlog-driven`

## Usage

### Enable GitHub Issues mode

In your consumer repo's workflow (`.github/workflows/auto-maintain.yml`):

```yaml
name: Auto Maintain

on:
  schedule:
    - cron: '0 */6 * * *'  # Every 6 hours
  workflow_dispatch:
    inputs:
      milestone:
        description: 'Filter by milestone'
        required: false
        type: string
      issue_label:
        description: 'Filter by label (e.g., feature, backend)'
        required: false
        type: string

jobs:
  auto-maintain:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@main
    with:
      use_github_issues: true           # Enable GitHub Issues mode
      milestone: ${{ inputs.milestone }}  # Optional: filter by milestone
      issue_label: ${{ inputs.issue_label }}  # Optional: filter by label
      language: typescript                # Your stack
    secrets:
      AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
      AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

### Filter options

- **No filters**: Process all open issues in the repo (filtered by `**Target repo:**` field)
- **`milestone`**: Only process issues in a specific milestone (e.g., "Multi-conversation Support v1")
- **`issue_label`**: Only process issues with a specific label (e.g., "backend", "feature")

### Priority ordering

Issues are selected by:
1. Priority (critical/high → P0, medium → P1, low → P2)
2. Issue number (lower = older = higher priority)

## Metadata format

### Required in issue body

```markdown
**Target repo:** `Answering-IT/your-repo`
```

This is the identifier that allows the workflow to discover which issues belong to a specific repo.

### Optional but recommended

```markdown
**Effort:** small|medium|large
**Priority:** critical|high|medium|low
**Dependencies:** Issue title 1, Issue title 2
```

### Acceptance criteria

Must be present in issue body:

```markdown
## Acceptance Criteria
- [ ] Item 1
- [ ] Item 2
```

These are parsed and used as acceptance criteria in the Claude prompt.

## Migration from BACKLOG.md

### Hybrid mode (during transition)

You can keep both modes available:

```yaml
jobs:
  # Use GitHub Issues by default
  auto-maintain-issues:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@main
    with:
      use_github_issues: true
      language: typescript
    secrets: inherit

  # Fallback to BACKLOG.md if issues are empty
  auto-maintain-backlog:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@main
    with:
      use_github_issues: false  # Legacy mode
      language: typescript
    secrets: inherit
```

### Full migration steps

1. Create issues in your repo using the documentation workflow
2. Update your auto-maintain workflow to set `use_github_issues: true`
3. Test with `workflow_dispatch` (set `dry_run: true` to see what would be picked)
4. Archive BACKLOG.md → `docs/archive/BACKLOG.md` (keep for reference)
5. Enable scheduled runs

## Testing

### Test the parser locally

```bash
cd scripts
python parse_github_issues.py \
  --repo Answering-IT/kb-rag-agent-fe \
  --list | jq '.[] | {id, title, priority}'
```

### Test the workflow (dry run)

```bash
gh workflow run auto-maintain.yml \
  -f use_github_issues=true \
  -f dry_run=true \
  -f milestone="Multi-conversation Support v1"
```

Check the job output to see what item would be picked and the generated prompt.

## Troubleshooting

### No eligible items found

- Check that issues exist in your repo: `gh issue list --state open`
- Verify the `**Target repo:**` field matches exactly (copy from issue body)
- Check milestone/label filters are correct

### Validation errors

The parser validates:
- Target repo field must match the consumer repo
- Acceptance criteria section must be present in issue body

Run validation manually:

```bash
python scripts/parse_github_issues.py \
  --repo Answering-IT/your-repo \
  --validate
```

### gh CLI authentication

The workflow uses `GITHUB_TOKEN` (automatically available in GitHub Actions). For local testing, authenticate with:

```bash
gh auth login
```

## Architecture

### parse_github_issues.py

Replaces `parse_backlog.py` when `use_github_issues=true`.

**Input**: GitHub Issues (via `gh issue list`)

**Output**: BacklogItem JSON (compatible with existing workflow)

**Key functions**:
- `query_issues()`: Call `gh issue list` with filters
- `parse_issue_metadata()`: Extract `**Target repo:**`, `**Effort:**`, `**Priority:**` from body
- `extract_acceptance_criteria()`: Parse `## Acceptance Criteria` section
- `issue_to_backlog_item()`: Map issue → BacklogItem structure
- `select_next()`: Priority-based selection (same logic as BACKLOG.md mode)

### Compatibility

The BacklogItem structure is identical to BACKLOG.md mode, so:
- Prompt generation (unchanged)
- Claude invocation (unchanged)
- PR creation (unchanged)

The only difference is the source: GitHub Issues API instead of parsing BACKLOG.md.

## Benefits

1. **Single source of truth**: Documentation repo → Issues → Automation
2. **Better visibility**: Issues are visible in GitHub UI, can be commented on, assigned, etc.
3. **Native GitHub features**: Milestones, labels, dependencies, mentions
4. **No merge conflicts**: BACKLOG.md often caused conflicts in active repos
5. **Automatic creation**: Feature specs → Issues (AI-generated, consistent format)

## Next steps

See [Open Design Questions](project_next_steps_automation.md) in the documentation repo's memory for planned enhancements:
- Worktree isolation for parallel work
- Cost tracking per Claude session
- Alerts for long sessions
- Dev agent for testing before opening PR

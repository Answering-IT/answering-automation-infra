# Answering Automation Infrastructure

Central repository for self-maintaining workflows across all Answering-IT repositories.

## Overview

This repo provides reusable GitHub Actions workflows that enable repositories to:
- Maintain a `BACKLOG.md` file with feature/task items
- Automatically implement items using Claude Code (via AWS Bedrock)
- Open PRs with quality gates enforced

**Key principle:** Write once, use everywhere. Minimize duplication, maximize reusability.

---

## Architecture

### Components

1. **Reusable Workflows** (`.github/workflows/`)
   - `auto-maintain-reusable.yml` - Core auto-implementation workflow
   - `build-python-reusable.yml` - Python quality gates
   - `build-typescript-reusable.yml` - TypeScript quality gates
   - `build-go-reusable.yml` - Go quality gates

2. **Shared Scripts** (`scripts/`)
   - `parse_backlog.py` - BACKLOG.md parser (validates, selects next item)

3. **Templates** (`templates/`)
   - Language-specific starter packs (pyproject.toml, BACKLOG.md, etc.)
   - Copy to new repo during onboarding

4. **Documentation** (`docs/`)
   - Onboarding guide
   - BACKLOG format specification
   - Troubleshooting

---

## Quick Start

### Add Auto-Maintain to Your Repo (5 steps, ~15 min)

#### Step 1: Copy template for your stack

```bash
# From answering-automation-infra root
cp -r templates/python/* /path/to/your-repo/
# or templates/typescript/ or templates/go/
```

#### Step 2: Create caller workflow

Create `.github/workflows/AutoMaintain.yml` in your repo:

```yaml
name: Auto Maintain
on:
  workflow_dispatch:
    inputs:
      backlog_id:
        description: 'Override item ID (leave blank for --next)'
        required: false
      dry_run:
        description: 'Print prompt without invoking Claude'
        type: boolean
        default: false

permissions:
  id-token: write       # AWS OIDC
  contents: write       # commit + push
  pull-requests: write  # open PR

jobs:
  run:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.0
    with:
      backlog_id: ${{ inputs.backlog_id }}
      dry_run: ${{ inputs.dry_run }}
      language: python    # python | typescript | go
      bedrock_model: us.anthropic.claude-sonnet-4-6
    secrets:
      AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
      AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

#### Step 3: Create gates workflow

Create `.github/workflows/Build.yml`:

```yaml
name: Build & Gates
on:
  pull_request:
    paths:
      - 'src/**'
      - 'agents/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'BACKLOG.md'

jobs:
  gates:
    uses: Answering-IT/answering-automation-infra/.github/workflows/build-python-reusable.yml@v1.0.0
```

#### Step 4: Add branch protection

Create `.github/settings.yml` (requires Probot Settings app):

```yaml
repository:
  name: your-repo
  description: Your repo description
  
branches:
  - name: main
    protection:
      required_pull_request_reviews:
        required_approving_review_count: 1
      required_status_checks:
        strict: true
        contexts:
          - "Lint & Format"
          - "Unit Tests"
      enforce_admins: false
```

#### Step 5: Add first backlog item

Edit `BACKLOG.md` (copied from template), add a trial item with `status: ready`.

Trigger manually: Actions → Auto Maintain → Run workflow

---

## Prerequisites

### Organization-Level Setup (One-Time)

#### 1. GitHub App

Install `answering-auto-maintain` (App ID: 3964884) org-wide:
- Settings → Developer settings → GitHub Apps → answering-auto-maintain
- Install App → Answering-IT → All repositories

Store secrets at org level:
- `AUTO_MAINTAIN_APP_ID` = `3964884`
- `AUTO_MAINTAIN_APP_PRIVATE_KEY` = (private key from app)

#### 2. AWS IAM Role

Ensure `GitHubActions-Answering-IT-SharedRole` trust policy allows all org repos:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::708819485463:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringLike": {
          "token.actions.githubusercontent.com:sub": "repo:Answering-IT/*:*"
        }
      }
    }
  ]
}
```

Role ARN: `arn:aws:iam::708819485463:role/GitHubActions-Answering-IT-SharedRole`

#### 3. GitHub Actions Permissions

Organization Settings → Actions → General:
- ✅ Allow GitHub Actions to create and approve pull requests

---

## Supported Stacks

| Language   | Linter/Formatter | Test Framework | Template |
|------------|------------------|----------------|----------|
| Python     | ruff + black     | pytest         | `templates/python/` |
| TypeScript | eslint + prettier | vitest        | `templates/typescript/` |
| Go         | golangci-lint    | go test        | `templates/go/` |

---

## Maintenance

### Update Reusable Workflow

1. Edit workflow in this repo
2. Tag new version: `git tag v1.1.0 && git push --tags`
3. Update consumer repos: bump `@v1.0.0` → `@v1.1.0` in their caller workflows

### Update Parser

1. Edit `scripts/parse_backlog.py`
2. Tag new version
3. Consumers automatically fetch latest via raw URL

### Update Templates

1. Edit templates (e.g., `templates/python/pyproject.toml`)
2. Tag new version
3. Consumer repos are NOT auto-updated (templates are point-in-time)
4. Optional: Add backlog item to each repo: "Update tooling to v1.x.x standard"

---

## Versioning Strategy

- `v1.x.x` - Backward-compatible changes (repos inherit automatically)
- `v2.x.x` - Breaking changes (repos must update manually)
- Test in 1-2 pilot repos before tagging major versions

---

## Cost Estimation

**Per repo per month:**
- 1 execution/day × 30 days ≈ $15-20
- On-demand only (no cron) ≈ $5-10

**Organization-wide:**
- 10 repos × $10/month = $100/month
- 50 repos × $10/month = $500/month

**Mitigation:**
- Only run when items have `status: ready`
- Use `dry_run: true` to validate prompts without invoking Claude
- AWS Budget alerts at org level

---

## Rollout Status

| Phase | Repos | Status |
|-------|-------|--------|
| Fase 0: Setup | answering-automation-infra | ✅ Done |
| Fase 1: Pilot | kb-rag-agent + 2 more | 🚧 In Progress |
| Fase 2: Python | ~10 Python repos | 📋 Planned |
| Fase 3: Multi-stack | TypeScript, Go repos | 📋 Planned |
| Fase 4: Org-wide | All repos | 📋 Planned |

---

## Documentation

- [Onboarding Guide](docs/ONBOARDING.md) - Step-by-step with screenshots
- [BACKLOG Format](docs/BACKLOG_FORMAT.md) - Schema specification
- [Troubleshooting](docs/TROUBLESHOOTING.md) - Common issues and fixes

---

## Support

Issues? Open an issue in this repo or contact the platform team.

**Last Updated:** 2026-06-04  
**Version:** v1.0.0

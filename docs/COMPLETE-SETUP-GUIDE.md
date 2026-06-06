# Complete Auto-Maintain Setup Guide

**Goal:** Set up the auto-maintain workflow in any repository with zero ambiguity.

**Time required:** 15-20 minutes for first-time setup (once you've done it once, subsequent repos take ~5 minutes)

---

## Overview

This guide covers:
1. ✅ Prerequisites you need before starting
2. ✅ GitHub App setup (one-time, if not already done)
3. ✅ Repository-specific setup (files, secrets, settings)
4. ✅ Validation and testing
5. ✅ Common issues and fixes

---

## Prerequisites Checklist

Before you start, verify you have:

- [ ] **Admin access** to the target repository
- [ ] **GitHub App credentials** (see section below if creating new)
  - App ID (a number like `123456`)
  - Private key (`.pem` file)
- [ ] **AWS access configured** with the shared IAM role trusting `repo:Answering-IT/*:*`
- [ ] **Bedrock model access** enabled for `us.anthropic.claude-sonnet-4-6` in `us-east-1`

### Getting GitHub App credentials

If the GitHub App `answering-auto-maintain` already exists:
1. App ID: Go to `https://github.com/settings/apps/answering-auto-maintain` (top of page shows "App ID: <number>")
2. Private key: If you have it saved, use it. If not:
   - Go to the same URL
   - Scroll to "Private keys" section
   - Click **Generate a private key**
   - Save the downloaded `.pem` file securely (password manager, etc.)

If the GitHub App doesn't exist yet, see [Appendix: Creating the GitHub App](#appendix-creating-the-github-app).

---

## Part 1: GitHub App Permissions (Critical)

**This is the #1 source of mysterious failures.** The GitHub App needs specific permissions.

### 1.1 Verify/Update App Permissions

1. Go to `https://github.com/settings/apps/answering-auto-maintain/permissions`
2. Under **Repository permissions**, ensure these are set:
   - **Contents**: `Read and write`
   - **Issues**: `Read and write`  
   - **Pull requests**: `Read and write`
   - **Workflows**: `Read and write` ⚠️ **CRITICAL for modifying `.github/workflows/` files**
   - **Metadata**: `Read-only` (this is automatic)
3. Click **Save changes**
4. If you changed anything, you'll need to accept the permission update in each installed repository (GitHub will prompt you)

**Why Workflows permission matters:**
- Without it, Claude can make changes to workflow files but **cannot push them**
- Error message: `refusing to allow a GitHub App to create or update workflow...`
- The branch exists locally but never reaches GitHub, so no PR is created
- This permission is safe — it only allows modifying workflows in repos where the app is explicitly installed

### 1.2 Install App on Target Repository

1. Go to `https://github.com/apps/answering-auto-maintain`
2. Click **Install** (or **Configure** if already installed)
3. Choose `Answering-IT` as the account
4. Select installation scope:
   - **All repositories** (recommended — auto-covers future repos)
   - **Only select repositories** → check your target repo
5. Click **Install** or **Save**

Verify installation: Go to `https://github.com/Answering-IT/<your-repo>/settings/installations` and confirm `answering-auto-maintain` appears.

---

## Part 2: Repository Files

### 2.1 Add Workflow Files

Create `.github/workflows/AutoMaintain.yml`:

```yaml
name: Auto Maintain
on:
  workflow_dispatch:
    inputs:
      issue_number:
        description: 'Specific issue number to implement (leave blank for --next)'
        required: false
      dry_run:
        description: 'Print prompt without invoking Claude'
        type: boolean
        default: false

permissions:
  id-token: write       # AWS OIDC
  contents: write       # commit + push
  pull-requests: write  # open PR
  issues: write         # claude-code-action may comment

jobs:
  run:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.4
    with:
      issue_number: ${{ inputs.issue_number }}
      dry_run: ${{ inputs.dry_run }}
      language: python                              # python | typescript | go
      bedrock_model: us.anthropic.claude-sonnet-4-6
      # use_github_issues defaults to true
      # For legacy BACKLOG.md mode: use_github_issues: false
    secrets:
      AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
      AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

Create `.github/workflows/Build.yml`:

```yaml
name: Build
on:
  pull_request:
    branches: [main]

permissions:
  id-token: write
  contents: read
  pull-requests: write

jobs:
  python-gates:
    name: Python Lint & Tests
    uses: Answering-IT/answering-automation-infra/.github/workflows/build-python-reusable.yml@v1.0.4
```

### 2.2 Add Development Configuration (Python repos)

If this is a Python repo and doesn't already have these files, copy from templates:

```bash
# From answering-automation-infra repo
cp templates/python/pyproject.toml /path/to/your-repo/
cp templates/python/requirements-dev.txt /path/to/your-repo/
cp templates/python/.python-version /path/to/your-repo/
```

**If files already exist**, merge carefully (don't overwrite existing config).

### 2.3 Create Initial Backlog (BACKLOG.md mode only)

If using legacy BACKLOG.md mode (not recommended for new repos):

```bash
cp templates/python/BACKLOG.md /path/to/your-repo/
```

Edit it to add a simple test item with `status: ready`.

**Recommended approach for new repos:** Use GitHub Issues mode instead (no BACKLOG.md needed). See [docs/github-issues-integration.md](github-issues-integration.md).

### 2.4 Commit and Create Setup PR

```bash
git checkout -b setup-auto-maintain
git add .github/workflows/ pyproject.toml requirements-dev.txt .python-version
git commit -m "chore: setup auto-maintain pipeline"
git push -u origin setup-auto-maintain
gh pr create --title "Setup auto-maintain pipeline" --fill
```

**Verify this PR triggers Build.yml and passes all checks before merging.** This validates your base setup.

---

## Part 3: Repository Secrets

The workflow needs two secrets. These MUST be set at the repository level (not inherited) because `Answering-IT` is a User account, not an Organization.

### 3.1 Set Secrets via CLI (Recommended)

```bash
# App ID (it's a number, but stored as a secret)
gh secret set AUTO_MAINTAIN_APP_ID \
  --body "YOUR_APP_ID_NUMBER" \
  -R Answering-IT/<your-repo>

# Private key (paste PEM contents or pipe from file)
gh secret set AUTO_MAINTAIN_APP_PRIVATE_KEY \
  -R Answering-IT/<your-repo> \
  < /path/to/answering-auto-maintain.private-key.pem
```

Verify:
```bash
gh secret list -R Answering-IT/<your-repo>
# Should show both:
#   AUTO_MAINTAIN_APP_ID
#   AUTO_MAINTAIN_APP_PRIVATE_KEY
```

### 3.2 Set Secrets via GitHub UI (Alternative)

1. Go to `https://github.com/Answering-IT/<your-repo>/settings/secrets/actions`
2. Click **New repository secret**
3. Name: `AUTO_MAINTAIN_APP_ID`, Value: the App ID number
4. Click **Add secret**
5. Click **New repository secret** again
6. Name: `AUTO_MAINTAIN_APP_PRIVATE_KEY`, Value: paste entire PEM file contents
7. Click **Add secret**

---

## Part 4: Repository Settings

### 4.1 Enable GitHub Actions to Create PRs

**This is required** or the workflow will fail with "GitHub Actions is not permitted to create or approve pull requests."

1. Go to `https://github.com/Answering-IT/<your-repo>/settings/actions`
2. Scroll to **Workflow permissions**
3. Check ✅ **Allow GitHub Actions to create and approve pull requests**
4. Click **Save**

### 4.2 Configure Branch Protection (Recommended)

Protect `main` to ensure auto-opened PRs go through the same gates as human PRs:

1. Go to `https://github.com/Answering-IT/<your-repo>/settings/branches`
2. Click **Add classic branch protection rule**
3. **Branch name pattern:** `main`
4. Configure:
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: `1`
     - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging
     - Add required checks (these appear after first PR runs):
       - `Python Lint & Tests / Lint & Format`
       - `Python Lint & Tests / Unit Tests`
       - (Add others as defined in your Build.yml)
   - ✅ **Do not allow bypassing the above settings**
5. Click **Create**

---

## Part 5: Testing and Validation

### 5.1 Dry Run Test (No Claude invocation)

First, test that item selection works without spending Bedrock tokens:

```bash
gh workflow run AutoMaintain.yml -f dry_run=true -R Answering-IT/<your-repo>
```

Watch it:
```bash
gh run watch $(gh run list --workflow=AutoMaintain.yml --limit 1 --json databaseId --jq '.[0].databaseId') -R Answering-IT/<your-repo>
```

**Expected result:**
- ✅ "Pick next work item" job passes
- ✅ Logs show which item would be picked
- ✅ Prompt is printed
- ✅ "Implement with Claude" job skipped (dry run mode)

If this fails, see [Common Issues](#common-issues) below.

### 5.2 Full Test Run

Now run for real with a simple backlog item:

```bash
gh workflow run AutoMaintain.yml -R Answering-IT/<your-repo>
```

**Expected result:**
- ✅ Both jobs pass
- ✅ A new PR appears with:
  - Title: `auto(<item-id>): <item title>`
  - Branch: `auto/<item-id>`
  - Labels: `automated`, `backlog-driven`
- ✅ Build.yml triggers automatically on the PR
- ✅ Checks pass (or fail with useful error messages if item needs work)

### 5.3 Validation Checklist

- [ ] Setup PR merged successfully
- [ ] Dry run completes without errors
- [ ] Full run creates a PR
- [ ] PR has correct labels
- [ ] Build.yml runs on the auto-PR
- [ ] Status checks appear in the PR

---

## Common Issues

### "App ID option is required"
- **Fix:** Repository secrets not set → [Part 3](#part-3-repository-secrets)

### "Resource not accessible by integration"
- **Fix:** GitHub App not installed on repo → [Part 1.2](#12-install-app-on-target-repository)

### "Refusing to allow a GitHub App to create or update workflow"
- **Fix:** Missing Workflows permission → [Part 1.1](#11-verifyupdate-app-permissions)

### "Not authorized to perform sts:AssumeRoleWithWebIdentity"
- **Fix:** IAM role doesn't trust this repo → Verify trust policy includes `repo:Answering-IT/*:*`

### "No eligible backlog item found"
- **Fix:** No item with `status: ready` in BACKLOG.md, or using GitHub Issues mode without issues

### Build.yml doesn't run on auto-PR
- **Fix:** "Allow GitHub Actions to create and approve pull requests" not enabled → [Part 4.1](#41-enable-github-actions-to-create-prs)

### Claude runs but no PR created
- **Possible causes:**
  1. Claude's gates failed (check logs) — item too complex, needs simplification
  2. Missing Workflows permission — see above
  3. Push failed for other reasons — check `Run Claude Code` step logs

For more troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## Appendix: Creating the GitHub App

**Only do this if the GitHub App doesn't already exist.** Skip if `answering-auto-maintain` is already created.

1. Go to `https://github.com/settings/apps/new` (logged in as `Answering-IT`)
2. **GitHub App name:** `answering-auto-maintain`
3. **Homepage URL:** `https://github.com/Answering-IT/answering-automation-infra`
4. **Webhook:** Uncheck **Active**
5. **Repository permissions:**
   - Contents: `Read and write`
   - Issues: `Read and write`
   - Pull requests: `Read and write`
   - Workflows: `Read and write` ⚠️
   - Metadata: `Read-only` (automatic)
6. **Where can this GitHub App be installed?:** `Only on this account`
7. Click **Create GitHub App**
8. Scroll to **Private keys** → **Generate a private key** → save `.pem` file
9. Note the **App ID** (shown at top of page)

---

## Quick Reference Card

Print this for each new repo setup:

```
□ Part 1.1: GitHub App permissions (Contents, Issues, PRs, Workflows: all Read+Write)
□ Part 1.2: App installed on target repo
□ Part 2.1: .github/workflows/AutoMaintain.yml created
□ Part 2.1: .github/workflows/Build.yml created
□ Part 2.4: Setup PR merged
□ Part 3: AUTO_MAINTAIN_APP_ID secret set
□ Part 3: AUTO_MAINTAIN_APP_PRIVATE_KEY secret set
□ Part 4.1: "Allow GitHub Actions to create PRs" enabled
□ Part 4.2: Branch protection on main (optional but recommended)
□ Part 5.1: Dry run passes
□ Part 5.2: Full run creates PR successfully
```

---

## Related Documentation

- [ONBOARDING.md](ONBOARDING.md) — Original detailed guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Comprehensive error reference
- [github-issues-integration.md](github-issues-integration.md) — GitHub Issues mode (recommended over BACKLOG.md)
- [BACKLOG_FORMAT.md](BACKLOG_FORMAT.md) — BACKLOG.md schema reference

---

**Last updated:** 2026-06-06

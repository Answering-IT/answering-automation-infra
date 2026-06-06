# Auto-Maintain Setup Guide

**Complete guide to set up auto-maintain in any repository.**

**Time:** 15-20 minutes first time, 5-10 minutes for subsequent repos

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [GitHub App Setup (One-time)](#github-app-setup-one-time)
3. [Per-Repository Setup](#per-repository-setup)
4. [Validation & Testing](#validation--testing)
5. [Troubleshooting](#troubleshooting)
6. [Quick Reference](#quick-reference)

---

## Prerequisites

Before starting, ensure you have:

- [ ] **Admin access** to the target repository
- [ ] **GitHub CLI** (`gh`) installed and authenticated
- [ ] **AWS access** with the shared IAM role configured
- [ ] **Bedrock access** to `us.anthropic.claude-sonnet-4-6` in `us-east-1`

---

## GitHub App Setup (One-time)

If the GitHub App `answering-auto-maintain` **already exists**, skip to [Configure Permissions](#step-1-configure-app-permissions).

If you need to **create** the app:

### Create the GitHub App

1. Go to https://github.com/settings/apps/new (logged in as `Answering-IT`)
2. Fill in:
   - **GitHub App name:** `answering-auto-maintain`
   - **Homepage URL:** `https://github.com/Answering-IT/answering-automation-infra`
   - **Webhook:** Uncheck "Active"
   - **Where can this GitHub App be installed?:** "Only on this account"
3. Click **Create GitHub App**
4. Save the **App ID** (shown at top of page)
5. Generate a **Private Key**:
   - Scroll to "Private keys" section
   - Click **Generate a private key**
   - Save the downloaded `.pem` file securely

### Step 1: Configure App Permissions

**This is critical - most setup failures are due to missing permissions.**

1. Go to https://github.com/settings/apps/answering-auto-maintain/permissions
2. Under **Repository permissions**, set these to **Read and write**:
   - ✅ **Contents**
   - ✅ **Issues**
   - ✅ **Pull requests**
   - ✅ **Workflows** ⚠️ **CRITICAL - Required to modify `.github/workflows/` files**
3. **Metadata** will automatically be "Read-only" (this is correct)
4. Click **Save changes**

#### Why Workflows Permission?

GitHub has a **security restriction**: modifying files in `.github/workflows/` requires an explicit `Workflows: Read and write` permission, **separate** from `Contents` permission.

**Without this permission:**
- Claude can make changes and commit them locally
- Push fails with: `refusing to allow a GitHub App to create or update workflow...`
- Branch exists locally but never reaches GitHub
- No PR is created

**With this permission:**
- Claude can modify workflow files
- Changes are pushed successfully
- PRs are created normally

**Security:** This permission is scoped to repositories where the app is explicitly installed. All changes appear in PRs with full audit trail.

### Step 2: Accept Permission Updates

After changing permissions, GitHub requires each installed repository to accept the update:

1. Go to https://github.com/settings/installations
2. Click **Configure** next to `answering-auto-maintain`
3. If you see "This app has requested additional permissions":
   - Review the changes
   - Click **Accept new permissions**

---

## Per-Repository Setup

### Automated Setup (Recommended)

Run this workflow from the `answering-automation-infra` repo:

```bash
gh workflow run setup-repo.yml \
  --repo Answering-IT/answering-automation-infra \
  -f target_repo=Answering-IT/YOUR-REPO-NAME \
  -f language=python \
  -f copy_templates=true \
  -f use_github_issues=true
```

This creates a PR with all files and instructions for manual steps. Skip to [Manual Configuration](#manual-configuration) after the PR is created.

### Manual Setup

If you prefer manual setup or the automated workflow isn't available:

#### 1. Create Workflow Files

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
      use_github_issues: true                       # or false for BACKLOG.md mode
    secrets:
      AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
      AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

Create `.github/workflows/Build.yml` (for Python repos):

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

For TypeScript or Go repos, adjust accordingly (see `templates/` directory).

#### 2. Copy Language Templates (Optional)

For Python repos without existing config:

```bash
# From answering-automation-infra repo
cp templates/python/pyproject.toml /path/to/your-repo/
cp templates/python/requirements-dev.txt /path/to/your-repo/
cp templates/python/.python-version /path/to/your-repo/
```

**If files exist**, merge carefully - don't overwrite.

#### 3. Commit Setup PR

```bash
git checkout -b setup-auto-maintain
git add .github/workflows/
git commit -m "chore: setup auto-maintain pipeline"
git push -u origin setup-auto-maintain
gh pr create --title "Setup auto-maintain pipeline" --fill
```

**Merge this PR only after Build.yml passes.** This validates your base configuration.

### Manual Configuration

These steps **cannot** be automated and must be done via GitHub UI or CLI:

#### 1. Set Repository Secrets

The workflow needs two secrets at the **repository level** (not inherited, since `Answering-IT` is a User account):

**Via CLI:**
```bash
# Get App ID from: https://github.com/settings/apps/answering-auto-maintain
gh secret set AUTO_MAINTAIN_APP_ID \
  --body "YOUR_APP_ID_NUMBER" \
  -R Answering-IT/YOUR-REPO-NAME

# Use the .pem file you saved earlier
gh secret set AUTO_MAINTAIN_APP_PRIVATE_KEY \
  -R Answering-IT/YOUR-REPO-NAME \
  < /path/to/answering-auto-maintain.private-key.pem
```

**Via GitHub UI:**
1. Go to `https://github.com/Answering-IT/YOUR-REPO-NAME/settings/secrets/actions`
2. Click **New repository secret**
3. Add `AUTO_MAINTAIN_APP_ID` with the App ID value
4. Add `AUTO_MAINTAIN_APP_PRIVATE_KEY` with the entire PEM file contents

**Verify:**
```bash
gh secret list -R Answering-IT/YOUR-REPO-NAME
# Should show both secrets
```

#### 2. Install GitHub App on Repository

1. Go to https://github.com/apps/answering-auto-maintain
2. Click **Install** (or **Configure** if already installed elsewhere)
3. Select installation scope:
   - **All repositories** (recommended - auto-covers future repos)
   - **Only select repositories** → check your repo
4. Click **Install** or **Save**

**Verify:**
```bash
# Check installations page
open https://github.com/Answering-IT/YOUR-REPO-NAME/settings/installations
# Should show: answering-auto-maintain
```

#### 3. Enable Actions to Create PRs

**Required** or workflow fails with "GitHub Actions is not permitted to create or approve pull requests."

1. Go to `https://github.com/Answering-IT/YOUR-REPO-NAME/settings/actions`
2. Scroll to **Workflow permissions**
3. Check ✅ **Allow GitHub Actions to create and approve pull requests**
4. Click **Save**

#### 4. Configure Branch Protection (Recommended)

Ensure auto-opened PRs go through the same review process as human PRs:

1. Go to `https://github.com/Answering-IT/YOUR-REPO-NAME/settings/branches`
2. Click **Add classic branch protection rule**
3. **Branch name pattern:** `main`
4. Configure:
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: `1`
   - ✅ **Require status checks to pass before merging**
     - Add checks that appear after first PR: `Python Lint & Tests / Lint & Format`, etc.
   - ✅ **Do not allow bypassing the above settings**
5. Click **Create**

---

## Validation & Testing

### Step 1: Validate Setup

Run the validation script:

```bash
./scripts/validate-setup.sh Answering-IT/YOUR-REPO-NAME
```

This checks:
- Workflow files exist
- Repository secrets are set
- GitHub App is installed
- Required permissions are configured

Fix any errors before proceeding.

### Step 2: Dry Run Test

Test item selection **without** invoking Claude (free, no Bedrock costs):

```bash
gh workflow run AutoMaintain.yml -f dry_run=true -R Answering-IT/YOUR-REPO-NAME
```

Watch it run:
```bash
gh run watch $(gh run list --workflow=AutoMaintain.yml --limit 1 --json databaseId --jq '.[0].databaseId') -R Answering-IT/YOUR-REPO-NAME
```

**Expected result:**
- ✅ "Pick next work item" job passes
- ✅ Prompt is printed in logs
- ✅ "Implement with Claude" job skipped

### Step 3: Full Test Run

Run with a simple backlog item or GitHub issue:

```bash
gh workflow run AutoMaintain.yml -R Answering-IT/YOUR-REPO-NAME
```

**Expected result:**
- ✅ Both jobs pass
- ✅ New PR created with:
  - Title: `auto(<item-id>): <title>`
  - Branch: `auto/<item-id>`
  - Labels: `automated`, `backlog-driven`
- ✅ Build.yml triggers on the PR
- ✅ Status checks run

### Setup Complete ✅

If all three tests pass, setup is complete!

---

## Troubleshooting

### "App ID option is required"
**Cause:** Repository secrets not set  
**Fix:** Complete [Manual Configuration Step 1](#1-set-repository-secrets)

### "Resource not accessible by integration"
**Cause:** GitHub App not installed on repo  
**Fix:** Complete [Manual Configuration Step 2](#2-install-github-app-on-repository)

### "Refusing to allow a GitHub App to create or update workflow"
**Cause:** Missing Workflows permission  
**Fix:** 
1. Go to https://github.com/settings/apps/answering-auto-maintain/permissions
2. Set **Workflows** to "Read and write"
3. Save and accept permission updates in installed repos

### "Not authorized to perform sts:AssumeRoleWithWebIdentity"
**Cause:** IAM role doesn't trust this repo  
**Fix:** Verify trust policy includes `repo:Answering-IT/*:*`

```bash
aws iam get-role \
  --role-name GitHubActions-Answering-IT-SharedRole \
  --query 'Role.AssumeRolePolicyDocument'
```

### "No eligible backlog item found"
**Cause:** No ready items (BACKLOG.md mode) or no open issues (GitHub Issues mode)  
**Fix:** 
- BACKLOG.md mode: Add item with `status: ready`
- GitHub Issues mode: Create issues with appropriate labels/milestone

### Build.yml doesn't run on auto-PR
**Cause:** "Allow GitHub Actions to create PRs" not enabled  
**Fix:** Complete [Manual Configuration Step 3](#3-enable-actions-to-create-prs)

### Claude runs but no PR created
**Possible causes:**
1. **Gates failed** - Check `Run Claude Code` step logs for ruff/black/pytest failures
2. **Missing Workflows permission** - See fix above
3. **Complex item** - Item too large, needs splitting

**Debug:**
```bash
# Run with dry_run to see the prompt
gh workflow run AutoMaintain.yml -f dry_run=true -R Answering-IT/YOUR-REPO-NAME

# Check the failed run logs
gh run view <RUN_ID> -R Answering-IT/YOUR-REPO-NAME
```

### Common Permission Issues

Your GitHub App permissions should show:
```
✅ Read and write access to code, issues, and pull requests
✅ Read and write access to workflows
```

If "workflows" is missing, the app cannot push changes to `.github/workflows/` files.

---

## Quick Reference

### Per-Repo Setup Checklist

```
□ GitHub App permissions verified (includes Workflows: Read+Write)
□ GitHub App installed on target repo
□ .github/workflows/AutoMaintain.yml created
□ .github/workflows/Build.yml created
□ Setup PR merged successfully
□ AUTO_MAINTAIN_APP_ID secret set
□ AUTO_MAINTAIN_APP_PRIVATE_KEY secret set
□ "Allow Actions to create PRs" enabled
□ Branch protection configured (optional)
□ Dry run test passes
□ Full run test creates PR
```

### Common Commands

```bash
# Validate setup
./scripts/validate-setup.sh Answering-IT/REPO-NAME

# Dry run (no Claude invocation)
gh workflow run AutoMaintain.yml -f dry_run=true -R Answering-IT/REPO-NAME

# Full run
gh workflow run AutoMaintain.yml -R Answering-IT/REPO-NAME

# Run specific issue
gh workflow run AutoMaintain.yml -f issue_number=42 -R Answering-IT/REPO-NAME

# Watch latest run
gh run watch $(gh run list --workflow=AutoMaintain.yml --limit 1 --json databaseId --jq '.[0].databaseId') -R Answering-IT/REPO-NAME

# List auto-opened PRs
gh pr list --label automated --state open -R Answering-IT/REPO-NAME

# Check secrets
gh secret list -R Answering-IT/REPO-NAME
```

### Key URLs

- **GitHub App Settings:** https://github.com/settings/apps/answering-auto-maintain
- **GitHub App Permissions:** https://github.com/settings/apps/answering-auto-maintain/permissions
- **GitHub App Installations:** https://github.com/settings/installations
- **Install App:** https://github.com/apps/answering-auto-maintain

### Workflow Versions

| Version  | Status  | Notes |
|----------|---------|-------|
| `v1.0.4` | Current | Latest stable, includes PR verification |
| `v1`     | Floating | Points to latest v1.x, prototyping only |

Update workflow references in `AutoMaintain.yml` and `Build.yml` when new versions are released.

---

## AWS Prerequisites (One-time per Account)

If not already configured:

### IAM Role Trust Policy

The role `GitHubActions-Answering-IT-SharedRole` must trust GitHub OIDC:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "Federated": "arn:aws:iam::708819485463:oidc-provider/token.actions.githubusercontent.com"
    },
    "Action": "sts:AssumeRoleWithWebIdentity",
    "Condition": {
      "StringLike": {
        "token.actions.githubusercontent.com:sub": "repo:Answering-IT/*:*"
      },
      "StringEquals": {
        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
      }
    }
  }]
}
```

### Bedrock Model Access

Enable cross-region inference profile `us.anthropic.claude-sonnet-4-6`:

```bash
aws bedrock list-inference-profiles \
  --region us-east-1 \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `claude-sonnet-4-6`)]'
```

If empty, request access via Bedrock console.

---

## GitHub Issues Mode (Recommended)

**Default mode** - uses GitHub Issues instead of BACKLOG.md.

### Setup

1. In `AutoMaintain.yml`, ensure: `use_github_issues: true` (this is the default)
2. Create issues in your repository with:
   - Label: `ready` (or configure via `issue_label` input)
   - Milestone: optional, filter via `milestone` input
   - Title and description following your team's format

### Advantages over BACKLOG.md

- ✅ Better tracking and assignment
- ✅ Comments and discussion inline
- ✅ Automatic linking (PRs close issues)
- ✅ No merge conflicts on backlog file
- ✅ Integrates with project boards

See `docs/github-issues-integration.md` for details.

---

## Support

- **Full documentation:** https://github.com/Answering-IT/answering-automation-infra
- **Troubleshooting reference:** `docs/TROUBLESHOOTING.md`
- **Report issues:** https://github.com/Answering-IT/answering-automation-infra/issues

---

**Last updated:** 2026-06-06  
**Workflow version:** v1.0.4

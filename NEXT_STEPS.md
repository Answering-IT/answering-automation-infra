# Next Steps - Rollout Plan

Repository created locally at: `/Users/qohatpretel/Answering/answering-automation-infra`

Current status: ✅ Local setup complete, ready to push to GitHub

---

## Phase 0: Setup Central Repo (YOU ARE HERE)

### Step 1: Create GitHub Repository

**Manual action required** (you need org admin permissions):

1. Go to: https://github.com/organizations/Answering-IT/repositories/new
2. Settings:
   - **Repository name:** `answering-automation-infra`
   - **Description:** `Central repository for self-maintaining workflows across all Answering-IT repos`
   - **Visibility:** Public (or Private if you prefer)
   - **Initialize:** Do NOT add README, .gitignore, or license (we have them locally)
3. Click "Create repository"

### Step 2: Push Local Repo

Once the GitHub repo exists:

```bash
cd ~/Answering/answering-automation-infra

# Add remote (replace if URL is different)
git remote add origin https://github.com/Answering-IT/answering-automation-infra.git

# Push main branch
git push -u origin main

# Push tag
git push origin v1.0.0
```

### Step 3: Verify

Check that these are visible on GitHub:
- ✅ 24 files committed
- ✅ Tag `v1.0.0` exists
- ✅ README.md renders correctly
- ✅ Workflows visible in `.github/workflows/`

---

## Phase 1: Pilot - Migrate kb-rag-agent

### Step 1: Update kb-rag-agent to use reusable workflow

**Goal:** Convert kb-rag-agent from standalone AutoMaintain.yml to using the reusable workflow.

```bash
cd ~/Answering/kb-rag-agent
git checkout -b migrate-to-reusable-workflow
```

**Edit `.github/workflows/AutoMaintain.yml`:**

Replace the entire content with:

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
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.0
    with:
      issue_number: ${{ inputs.issue_number }}
      dry_run: ${{ inputs.dry_run }}
      language: python
      bedrock_model: us.anthropic.claude-sonnet-4-6
      # use_github_issues defaults to true
    secrets:
      AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
      AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

**What changed:**
- Removed all the implementation (pick-item, implement jobs)
- Now just calls the reusable workflow
- Passes language: python
- Uses @v1.0.0 tag

**Similarly, edit `.github/workflows/Build.yml`:**

Replace quality gate jobs with:

```yaml
name: Build & Gates
on:
  pull_request:
    paths:
      - 'agents/**'
      - 'tests/**'
      - 'scripts/**'
      - 'infrastructure/**'
      - 'pyproject.toml'
      - 'requirements*.txt'
      - 'BACKLOG.md'

jobs:
  python-gates:
    uses: Answering-IT/answering-automation-infra/.github/workflows/build-python-reusable.yml@v1.0.0

  cdk-build:
    name: CDK Build & Synth
    runs-on: ubuntu-latest
    # ... keep existing CDK job as-is (it's repo-specific)
```

**Note:** Keep the CDK job because it's specific to kb-rag-agent. Only move the Python gates (lint, unit tests) to reusable.

### Step 2: Commit and Push

```bash
git add .github/workflows/
git commit -m "refactor: migrate to reusable workflows from answering-automation-infra

- AutoMaintain.yml now uses reusable workflow @v1.0.0
- Build.yml uses build-python-reusable.yml for gates
- Keeps repo-specific CDK job

Reduces duplication and centralizes maintenance."

git push origin migrate-to-reusable-workflow
```

### Step 3: Open PR and Test

```bash
gh pr create --title "Migrate to reusable auto-maintain workflows" \
  --body "Test PR to validate that reusable workflows from answering-automation-infra work correctly.

## Changes
- AutoMaintain.yml → calls reusable workflow
- Build.yml → calls build-python-reusable.yml

## Testing
After merge, will trigger AutoMaintain.yml manually to verify end-to-end."
```

**Merge the PR** after checks pass.

### Step 4: Trigger Auto-Maintain

```bash
# Ensure you're on main and up-to-date
git checkout main
git pull

# Trigger workflow
gh workflow run AutoMaintain.yml
```

**Expected:**
- Workflow runs, calls reusable workflow from central repo
- Picks next item from BACKLOG.md
- Opens PR with label `automated`
- Build.yml runs, calls reusable build-python workflow
- All gates pass

**Success criteria:**
- ✅ Reusable workflow executes without errors
- ✅ Auto-opened PR has correct format
- ✅ Build gates pass
- ✅ You can merge the PR manually

---

## Phase 2: Onboard 2 More Pilot Repos

**Pick 2 repos:**
- One Python repo (easy, uses same template as kb-rag-agent)
- One TypeScript repo (validates multi-stack support)

**For each repo:**

### Step 1: Copy Template

```bash
# From answering-automation-infra
cd ~/Answering/answering-automation-infra
cp -r templates/python/* ~/Answering/<target-repo>/
# or templates/typescript/ for TS repo
```

### Step 2: Create Workflows

Create `.github/workflows/AutoMaintain.yml` and `.github/workflows/Build.yml` (see ONBOARDING.md for exact content).

### Step 3: Commit and Test

```bash
cd ~/Answering/<target-repo>
git checkout -b setup-auto-maintain
git add .github/workflows/ pyproject.toml requirements-dev.txt BACKLOG.md
git commit -m "chore: add auto-maintain setup"
git push origin setup-auto-maintain

# Open PR
gh pr create --title "Setup auto-maintain pipeline" --body "First PR to validate gates"
```

### Step 4: Merge and Trigger

```bash
git checkout main
git pull
gh workflow run AutoMaintain.yml
```

---

## Phase 3: Scale to All Python Repos

Once pilots succeed:

1. Identify all Python repos in org:
   ```bash
   gh repo list Answering-IT --json name,primaryLanguage --jq '.[] | select(.primaryLanguage.name == "Python") | .name'
   ```

2. For each repo, repeat Phase 2 steps

3. Optional: Create script to automate onboarding:
   ```bash
   # scripts/onboard-repo.sh <repo-name> <language>
   ```

---

## Phase 4: Multi-Stack (TypeScript, Go)

1. Onboard TypeScript repos (use templates/typescript/)
2. Onboard Go repos (use templates/go/)
3. Validate gates work for each stack

---

## Phase 5: Org-Wide Rollout

Once you have 10+ repos successfully using the system:

1. **Announce in Slack:**
   ```
   🎉 Self-maintaining repos now available org-wide!
   
   Any repo can now auto-implement features from a BACKLOG.md file.
   See: https://github.com/Answering-IT/answering-automation-infra
   
   Onboarding takes ~15 min. Ping @platform-team for help.
   ```

2. **Create dashboard (optional):**
   - Weekly workflow that aggregates all BACKLOG.md files
   - Shows which repos are using auto-maintain
   - Shows total items ready/done org-wide

3. **Set budget alerts:**
   - CloudWatch alarm for Bedrock costs
   - Alert if monthly cost > expected threshold

---

## Monitoring and Maintenance

### Weekly Review

Check these metrics:
- How many PRs auto-opened this week?
- What's the merge rate? (should be >80%)
- Any workflow failures? (check reasons)
- Bedrock costs vs. budget

### Monthly

- Review pilot repos for feedback
- Update docs based on issues encountered
- Consider bumping to v1.1.0 if improvements ready

---

## Success Metrics

### Phase 1 (Pilot) - Week 1
- ✅ kb-rag-agent migrated to reusable workflows
- ✅ 1 auto-PR opened and merged successfully
- ✅ 2 additional pilot repos onboarded

### Phase 2 (Python Expansion) - Week 2-3
- ✅ 10 Python repos using auto-maintain
- ✅ At least 5 PRs auto-opened across repos
- ✅ No critical issues reported

### Phase 3 (Multi-Stack) - Week 4-5
- ✅ TypeScript template validated (3+ repos)
- ✅ Go template validated (2+ repos)
- ✅ Docs updated with learnings

### Phase 4 (Org-Wide) - Week 6+
- ✅ 80%+ of repos have auto-maintain enabled
- ✅ Dashboard showing org-wide backlog status
- ✅ Budget alerts configured
- ✅ <2 hours/week maintenance overhead

---

## Current Status Summary

**Done:**
- ✅ Central repo created locally
- ✅ 4 reusable workflows (auto-maintain + 3 stack gates)
- ✅ 3 language templates (Python, TypeScript, Go)
- ✅ Complete documentation (4 docs)
- ✅ Parser script (from kb-rag-agent)
- ✅ v1.0.0 tagged

**Next (YOU):**
- 📋 Create GitHub repo: `Answering-IT/answering-automation-infra`
- 📋 Push local repo + tag
- 📋 Migrate kb-rag-agent to reusable workflow
- 📋 Test end-to-end (trigger AutoMaintain manually)

**Then:**
- 📋 Onboard 2 pilot repos
- 📋 Expand to all Python repos
- 📋 Multi-stack rollout
- 📋 Org-wide announcement

---

## Questions?

If anything is unclear or you hit issues:

1. Check `docs/TROUBLESHOOTING.md`
2. Check `docs/ONBOARDING.md`
3. Open issue in answering-automation-infra repo (once created)

---

**Repository Location:** `/Users/qohatpretel/Answering/answering-automation-infra`  
**Version:** v1.0.0  
**Date:** 2026-06-04  
**Status:** Ready to push to GitHub

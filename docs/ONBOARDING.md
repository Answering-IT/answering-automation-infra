# Onboarding Guide

Add auto-maintain capabilities to any repository in 5 steps (~15 minutes).

---

## Prerequisites

Before starting, ensure these are configured at the organization level:

### 1. GitHub App

The `answering-auto-maintain` app (App ID: 3964884) should be installed org-wide.

**Verify:**
- Go to: https://github.com/organizations/Answering-IT/settings/installations
- Check that `answering-auto-maintain` is installed
- If not, contact org admin

**Secrets (already configured org-level):**
- `AUTO_MAINTAIN_APP_ID` = `3964884`
- `AUTO_MAINTAIN_APP_PRIVATE_KEY` = (private key)

### 2. AWS IAM Role

The shared role must trust all org repos:
- Role: `arn:aws:iam::708819485463:role/GitHubActions-Answering-IT-SharedRole`
- Trust policy must include: `"token.actions.githubusercontent.com:sub": "repo:Answering-IT/*:*"`

**Verify:**
```bash
aws iam get-role --role-name GitHubActions-Answering-IT-SharedRole --profile ans-super
```

### 3. GitHub Actions Permissions

Org-level setting must allow Actions to create PRs:
- Settings → Actions → General
- ✅ "Allow GitHub Actions to create and approve pull requests"

---

## Step-by-Step

### Step 1: Identify Your Stack

Determine which template to use:
- **Python** - Uses ruff, black, pytest
- **TypeScript** - Uses eslint, prettier, vitest
- **Go** - Uses golangci-lint, go test

For this guide, we'll use Python as an example.

---

### Step 2: Copy Template Files

From this repo's root:

```bash
# Clone this repo if you haven't
git clone https://github.com/Answering-IT/answering-automation-infra.git
cd answering-automation-infra

# Copy template to your repo
cp -r templates/python/* /path/to/your-repo/

# Navigate to your repo
cd /path/to/your-repo

# Review what was copied
ls -la
# Should see: pyproject.toml, requirements-dev.txt, .python-version, BACKLOG.md
```

**What you get:**
- `pyproject.toml` - ruff, black, mypy, pytest config
- `requirements-dev.txt` - Pinned dev dependencies
- `.python-version` - Python 3.11
- `BACKLOG.md` - Pre-populated with example items

---

### Step 3: Create Workflows

#### A) Auto-Maintain Workflow

Create `.github/workflows/AutoMaintain.yml`:

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
      language: python    # ⚠️ Change this for your stack: python | typescript | go
      bedrock_model: us.anthropic.claude-sonnet-4-6
    secrets:
      AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
      AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

**For TypeScript repos:** Change `language: typescript`  
**For Go repos:** Change `language: go`

#### B) Build & Gates Workflow

Create `.github/workflows/Build.yml`:

```yaml
name: Build & Gates
on:
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'
      - 'pyproject.toml'
      - 'requirements*.txt'
      - 'BACKLOG.md'

jobs:
  gates:
    uses: Answering-IT/answering-automation-infra/.github/workflows/build-python-reusable.yml@v1.0.0
```

**For TypeScript repos:**
```yaml
jobs:
  gates:
    uses: Answering-IT/answering-automation-infra/.github/workflows/build-typescript-reusable.yml@v1.0.0
```

**For Go repos:**
```yaml
jobs:
  gates:
    uses: Answering-IT/answering-automation-infra/.github/workflows/build-go-reusable.yml@v1.0.0
```

---

### Step 4: Configure Branch Protection

Create `.github/settings.yml` (requires [Probot Settings](https://github.com/apps/settings) app):

```yaml
repository:
  name: your-repo-name
  description: Your repo description
  
branches:
  - name: main
    protection:
      required_pull_request_reviews:
        required_approving_review_count: 1
      required_status_checks:
        strict: true
        contexts:
          - "Lint & Format"       # Must match job name in Build.yml
          - "Unit Tests"          # Must match job name in Build.yml
      enforce_admins: false
      allow_force_pushes: false
      allow_deletions: false
```

**Note:** If Probot Settings is not installed, configure branch protection manually:
- Repo → Settings → Branches → Add rule
- Branch name pattern: `main`
- Enable: "Require a pull request before merging"
- Enable: "Require status checks to pass before merging"
- Select: "Lint & Format" and "Unit Tests"

---

### Step 5: Commit and Test

```bash
# Stage files
git checkout -b setup-auto-maintain
git add .github/workflows/ pyproject.toml requirements-dev.txt .python-version BACKLOG.md

# Commit
git commit -m "chore: add auto-maintain setup

- Add AutoMaintain.yml and Build.yml workflows
- Add Python tooling config (ruff, black, pytest)
- Add BACKLOG.md with trial item"

# Push
git push origin setup-auto-maintain

# Open PR manually (this PR validates Build.yml works)
gh pr create --title "Setup auto-maintain pipeline" --body "First PR to validate gates"
```

**Wait for PR checks to pass**, then merge.

---

### Step 6: First Auto-Maintain Run

Now test the auto-maintain workflow:

```bash
# Ensure you're on main and up-to-date
git checkout main
git pull

# Edit BACKLOG.md - ensure the trial item has status: ready
# (Template already has one ready)

# Trigger workflow manually
gh workflow run AutoMaintain.yml
```

**Or via GitHub UI:**
1. Go to: Actions → Auto Maintain
2. Click "Run workflow"
3. Leave inputs blank (uses --next selection)
4. Click "Run workflow"

**Expected result:**
- Workflow runs for ~5-10 minutes
- Opens a PR with branch `auto/example-trial-task`
- PR has labels `automated` and `backlog-driven`
- Build.yml checks run automatically
- All gates should pass

**Review the PR:**
- Check the code changes match acceptance criteria
- Check that tests pass
- Merge if looks good

---

## Validation Checklist

After completing all steps:

- [ ] Template files copied to repo root
- [ ] `.github/workflows/AutoMaintain.yml` created
- [ ] `.github/workflows/Build.yml` created
- [ ] `.github/settings.yml` created (or branch protection configured manually)
- [ ] All files committed to main branch
- [ ] First manual PR opened and merged (validates Build.yml)
- [ ] First auto-maintain run triggered
- [ ] Auto-opened PR has correct branch name (`auto/<item-id>`)
- [ ] Auto-opened PR triggers Build.yml checks
- [ ] All checks pass on auto-opened PR

---

## Troubleshooting

### "No eligible backlog item found"

**Cause:** No items in BACKLOG.md have `status: ready`.

**Fix:**
```bash
# Edit BACKLOG.md
# Change an item's status from blocked to ready
status: ready
```

### "An open automated PR already exists for {id}"

**Cause:** You already have an open PR for this backlog item.

**Fix:**
- Merge or close the existing PR first
- Or override with a different item: Run workflow → backlog_id: `other-item-id`

### Build.yml checks don't run on auto-opened PR

**Cause:** GitHub App token not configured correctly, or org setting disabled.

**Fix:**
1. Verify org setting: Settings → Actions → General → ✅ "Allow GitHub Actions to create and approve pull requests"
2. Verify secrets are set: Settings → Secrets → Actions → Check `AUTO_MAINTAIN_APP_ID` and `AUTO_MAINTAIN_APP_PRIVATE_KEY`

### "Role is not authorized to perform: sts:AssumeRoleWithWebIdentity"

**Cause:** IAM role trust policy doesn't include your repo.

**Fix:** Contact platform team to update the trust policy with wildcard:
```json
"token.actions.githubusercontent.com:sub": "repo:Answering-IT/*:*"
```

### Tests fail locally but not in CI

**Cause:** Local env has different Python version or cached dependencies.

**Fix:**
```bash
# Reset local env
deactivate
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r requirements.txt  # or agents/requirements.txt

# Re-run tests
pytest -m "unit or smoke"
```

---

## Next Steps

Once your first auto-opened PR merges successfully:

1. **Add real backlog items**
   - Edit `BACKLOG.md`
   - Add items with `status: ready`
   - Follow the [BACKLOG_FORMAT.md](BACKLOG_FORMAT.md) spec

2. **Schedule regular runs (optional)**
   - Edit `AutoMaintain.yml`
   - Add a `schedule:` trigger:
     ```yaml
     on:
       schedule:
         - cron: '0 10 * * MON'  # Every Monday at 10am UTC
       workflow_dispatch:
         # ... existing inputs
     ```

3. **Customize quality gates**
   - Adjust `pyproject.toml` for stricter rules
   - Add more pytest markers
   - Add security checks (e.g., bandit for Python)

4. **Monitor costs**
   - Review AWS billing for Bedrock usage
   - Set CloudWatch budget alerts
   - Use `dry_run: true` to test prompts without invoking Claude

---

## Support

Questions or issues?
- Open an issue in [answering-automation-infra](https://github.com/Answering-IT/answering-automation-infra/issues)
- Contact platform team in Slack

---

**Last Updated:** 2026-06-04  
**Template Version:** v1.0.0

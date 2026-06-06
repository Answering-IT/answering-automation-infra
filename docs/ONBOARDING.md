# Onboarding a Repo to Auto-Maintain

This guide takes a repository from zero to a working auto-maintain pipeline. It covers **everything**, including the steps that must be done manually in the GitHub UI (because they can't be scripted with the `gh` CLI).

**Estimated time:** 30 minutes for the first repo, ~10 minutes for subsequent repos once you've done it once.

---

## What you'll have at the end

- `Build.yml` running on every PR (lint, format, test, optional CDK build)
- `AutoMaintain.yml` triggerable from the Actions tab
- Triggering it picks the next item from `BACKLOG.md`, hands it to Claude (via Bedrock), and Claude opens a PR
- That PR runs through `Build.yml` automatically — same gates as a human PR

---

## Prerequisites checklist

Before you start, make sure these are true:

- [ ] You have **admin** access to the consumer repo (you'll add secrets and configure Actions)
- [ ] You have the GitHub App private key (`.pem` file) for `answering-auto-maintain` saved somewhere
- [ ] You know the GitHub App ID (a number, not a secret — it's public on the App's settings page)
- [ ] The AWS IAM role `arn:aws:iam::708819485463:role/GitHubActions-Answering-IT-SharedRole` already trusts `repo:Answering-IT/*:*` (check with the platform team if unsure)
- [ ] The repo is on `main` as default branch (the workflows assume this)

If any of these are missing, see the [Foundation setup](#foundation-setup-one-time-per-account) section at the bottom.

---

## Part 1: Repo file changes

This part is all standard git — copy files, edit, commit, PR, merge.

### 1.1 Copy template files

From a clone of this repo:

```bash
cd /path/to/answering-automation-infra

# Copy template into the consumer repo
cp templates/python/pyproject.toml         /path/to/your-repo/
cp templates/python/requirements-dev.txt   /path/to/your-repo/
cp templates/python/.python-version        /path/to/your-repo/
cp templates/python/BACKLOG.md             /path/to/your-repo/
```

If the consumer repo already has a `pyproject.toml` or `requirements-dev.txt`, **don't blindly overwrite** — merge by hand. The template's ruff config is intentionally pragmatic (only `E,F,W,I` selected, see CHANGELOG for why).

### 1.2 Create the caller workflows

#### `.github/workflows/AutoMaintain.yml`

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
  issues: write         # claude-code-action may comment

jobs:
  run:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.4
    with:
      backlog_id: ${{ inputs.backlog_id }}
      dry_run: ${{ inputs.dry_run }}
      language: python                              # python | typescript | go
      bedrock_model: us.anthropic.claude-sonnet-4-6
    secrets:
      AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
      AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

#### `.github/workflows/Build.yml`

Minimal version:

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

If your repo has CDK or other extra build steps, add them as additional jobs after `python-gates`. Look at `external-ingester-consumer-lambda/.github/workflows/Build.yml` for an example.

### 1.3 Add a trial backlog item

Edit the copied `BACKLOG.md` and make sure it has at least one item with `status: ready`. The template already includes one — leave it for now to validate the pipeline.

### 1.4 Open a regular PR with these changes

```bash
git checkout -b setup-auto-maintain
git add .github/workflows/ pyproject.toml requirements-dev.txt .python-version BACKLOG.md
git commit -m "chore: setup auto-maintain pipeline"
git push -u origin setup-auto-maintain
gh pr create --title "Setup auto-maintain pipeline" --fill
```

This first PR validates that `Build.yml` works on a normal human-authored PR. **Merge it once green.** If it fails, fix it on this branch — easier to debug now than later.

---

## Part 2: Repository secrets (manual, GitHub UI or CLI)

The `AutoMaintain.yml` workflow needs two secrets at the repo level. These cannot be inherited from anywhere else because `Answering-IT` is a User account, not an Organization (see [README.md](../README.md#important-this-is-not-a-github-organization)).

### Option A: CLI (faster, requires `gh` admin auth)

```bash
# App ID is a public identifier (a number) — not actually secret, but stored as one.
# Look it up at: https://github.com/settings/apps/answering-auto-maintain
gh secret set AUTO_MAINTAIN_APP_ID \
  --body "<APP_ID_NUMBER>" \
  -R Answering-IT/<your-repo>

# Private key: paste the PEM contents, or pipe from file
gh secret set AUTO_MAINTAIN_APP_PRIVATE_KEY \
  < /path/to/answering-auto-maintain.private-key.pem \
  -R Answering-IT/<your-repo>
```

Verify:

```bash
gh secret list -R Answering-IT/<your-repo>
# Should show:
#   AUTO_MAINTAIN_APP_ID
#   AUTO_MAINTAIN_APP_PRIVATE_KEY
```

### Option B: GitHub UI (manual, click-by-click)

1. Go to `https://github.com/Answering-IT/<your-repo>/settings/secrets/actions`
2. Click **New repository secret**
3. Name: `AUTO_MAINTAIN_APP_ID`
   Value: the App ID number (visible at `https://github.com/settings/apps/answering-auto-maintain`)
4. Click **Add secret**
5. Click **New repository secret** again
6. Name: `AUTO_MAINTAIN_APP_PRIVATE_KEY`
   Value: paste the entire PEM contents (including `-----BEGIN RSA PRIVATE KEY-----` and `-----END RSA PRIVATE KEY-----` lines)
7. Click **Add secret**

### Where do these values come from?

**App ID:** Public, found at `https://github.com/settings/apps/answering-auto-maintain` (top of the page, "App ID: <number>"). You can copy this from another repo that already has it set, or from the App settings page.

**Private key:** This is the `.pem` file you downloaded when the GitHub App was first created. If you lost it:

1. Go to `https://github.com/settings/apps/answering-auto-maintain`
2. Scroll to "Private keys" section
3. Click **Generate a private key** → downloads a new `.pem` file
4. Old keys keep working until you revoke them, so it's safe to generate a new one
5. Use the new file in step A or B above
6. **Save it somewhere persistent** (password manager, etc.) so you don't have to regenerate every time

---

## Part 3: GitHub App installation (manual, GitHub UI)

The GitHub App must be **installed** on each consumer repo (or installed on "All repositories" once and forgotten). Without this, the App can't open PRs in the repo even with valid credentials.

### Verify if already installed

Go to: `https://github.com/Answering-IT/<your-repo>/settings/installations`

If you see `answering-auto-maintain` listed → ✅ already installed, skip to Part 4.

### Install on this repo

1. Go to `https://github.com/apps/answering-auto-maintain` (the public App page)
2. Click **Install** (or **Configure** if already installed elsewhere)
3. Choose `Answering-IT` as the account
4. Select either:
   - **All repositories** (recommended — covers future repos automatically)
   - **Only select repositories** → check the consumer repo
5. Click **Install** (or **Save**)

### Required App permissions

The App needs these permissions (already configured if it was set up correctly):

- **Repository permissions:**
  - Contents: Read & write
  - Issues: Read & write
  - Pull requests: Read & write
  - Metadata: Read

If permissions are wrong, you'll see errors like "Resource not accessible by integration" when Claude tries to push or open a PR. Fix at `https://github.com/settings/apps/answering-auto-maintain/permissions`.

---

## Part 4: GitHub Actions setting (manual, GitHub UI, repo-level)

By default, GitHub Actions cannot create or approve pull requests. You must enable this **per repo**.

1. Go to `https://github.com/Answering-IT/<your-repo>/settings/actions`
2. Scroll to **Workflow permissions**
3. Check ✅ **Allow GitHub Actions to create and approve pull requests**
4. Click **Save**

Without this, the auto-maintain run will fail with `GitHub Actions is not permitted to create or approve pull requests`. The error is misleading because Claude is using a GitHub App token, not the `GITHUB_TOKEN` — but the setting still applies.

---

## Part 5: Branch protection (recommended, GitHub UI)

You want auto-opened PRs to require the same gates a human PR would. Without branch protection, Claude could merge its own PRs (since the App has write access).

1. Go to `https://github.com/Answering-IT/<your-repo>/settings/branches`
2. Click **Add classic branch protection rule** (or edit existing rule for `main`)
3. **Branch name pattern:** `main`
4. Check the following:
   - ✅ **Require a pull request before merging**
     - ✅ Require approvals: **1**
     - ✅ Dismiss stale pull request approvals when new commits are pushed
   - ✅ **Require status checks to pass before merging**
     - ✅ Require branches to be up to date before merging
     - In the search box, type and add:
       - `Python Lint & Tests / Lint & Format`
       - `Python Lint & Tests / Unit Tests`
       - (Add other checks as your `Build.yml` defines them, e.g. `CDK Build & Synth`)
   - ✅ **Do not allow bypassing the above settings**
5. Click **Create** (or **Save changes**)

**Note on status check names:** They must match exactly. The names are `<workflow-job-name> / <reusable-job-name>`. After your first PR runs, GitHub auto-suggests them in the dropdown — easier than typing.

---

## Part 6: First test run

Now validate the full pipeline.

### 6.1 Trigger the workflow

```bash
gh workflow run AutoMaintain.yml -R Answering-IT/<your-repo>
```

Or via UI: `https://github.com/Answering-IT/<your-repo>/actions/workflows/AutoMaintain.yml` → **Run workflow**.

### 6.2 Watch it run

```bash
gh run list --workflow=AutoMaintain.yml -R Answering-IT/<your-repo> --limit 1
gh run watch <RUN_ID> -R Answering-IT/<your-repo>
```

Expected duration: 1–3 minutes for a trivial item.

### 6.3 Expected outcome

- ✅ Job `Pick next backlog item` passes
- ✅ Job `Implement with Claude` passes
- A new PR appears at `https://github.com/Answering-IT/<your-repo>/pulls`
- PR title: `auto(<item-id>): <item title>`
- Branch name: `auto/<item-id>`
- Labels: `automated` and `backlog-driven`
- The PR triggers `Build.yml` automatically — wait for those checks too

### 6.4 If something failed

See [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md). The most common issues for fresh onboardings are:

| Symptom                                  | Cause                                      | Fix                                                       |
|------------------------------------------|--------------------------------------------|-----------------------------------------------------------|
| `appId option is required`               | Repo secrets not set                       | Part 2                                                    |
| `not authorized to perform sts:Assume…`  | IAM trust policy doesn't include this repo | Part 7 (foundation), or contact platform team             |
| `Resource not accessible by integration` | App not installed on this repo             | Part 3                                                    |
| Auto-PR has no checks running            | Repo Actions setting disabled              | Part 4                                                    |
| `No eligible backlog item found`         | No item with `status: ready`               | Edit `BACKLOG.md`                                         |
| `Backlog file not found`                 | Old reusable workflow tag                  | Bump caller to `@v1.0.4` or later                         |

---

## Foundation setup (one-time per account)

These are infrastructure things that should be set up once for the entire `Answering-IT` account, not per repo. If they're already done, skip this section.

### F.1 Create the GitHub App

1. Go to `https://github.com/settings/apps/new` (logged in as `Answering-IT`)
2. **GitHub App name:** `answering-auto-maintain`
3. **Homepage URL:** `https://github.com/Answering-IT/answering-automation-infra`
4. **Webhook:** uncheck **Active** (we don't need webhooks)
5. **Repository permissions:**
   - Contents: **Read & write**
   - Issues: **Read & write**
   - Pull requests: **Read & write**
   - Metadata: **Read**
6. **Where can this GitHub App be installed?:** **Only on this account**
7. Click **Create GitHub App**
8. On the next page, scroll to **Private keys** → **Generate a private key** → save the `.pem` file
9. Note the **App ID** at the top of the page

### F.2 AWS IAM role trust policy

The role `GitHubActions-Answering-IT-SharedRole` must trust GitHub OIDC for all repos in the account.

```bash
aws iam get-role \
  --role-name GitHubActions-Answering-IT-SharedRole \
  --query 'Role.AssumeRolePolicyDocument' \
  --profile ans-super
```

The trust policy should include:

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

If the wildcard `repo:Answering-IT/*:*` is missing, update with:

```bash
aws iam update-assume-role-policy \
  --role-name GitHubActions-Answering-IT-SharedRole \
  --policy-document file://trust-policy.json \
  --profile ans-super
```

### F.3 AWS Bedrock model access

Make sure cross-region inference profile `us.anthropic.claude-sonnet-4-6` is enabled in `us-east-1`.

```bash
aws bedrock list-inference-profiles \
  --region us-east-1 \
  --profile ans-super \
  --query 'inferenceProfileSummaries[?contains(inferenceProfileId, `claude-sonnet-4-6`)]'
```

If empty, request access via the Bedrock console: Console → Bedrock → Model access → Manage model access → request `anthropic.claude-sonnet-4-6`.

---

## Per-repo onboarding checklist (printable)

Use this for each new repo:

- [ ] **Part 1.1** Copy `templates/python/*` into the repo
- [ ] **Part 1.2** Create `.github/workflows/AutoMaintain.yml`
- [ ] **Part 1.2** Create `.github/workflows/Build.yml`
- [ ] **Part 1.3** Trial item with `status: ready` exists in `BACKLOG.md`
- [ ] **Part 1.4** Setup PR opened, checks green, merged
- [ ] **Part 2** `AUTO_MAINTAIN_APP_ID` repo secret set
- [ ] **Part 2** `AUTO_MAINTAIN_APP_PRIVATE_KEY` repo secret set
- [ ] **Part 3** GitHub App installed on this repo (or "All repositories")
- [ ] **Part 4** Repo Actions setting allows creating PRs
- [ ] **Part 5** Branch protection on `main` requires Build.yml checks
- [ ] **Part 6** First Auto Maintain run produced a PR successfully

---

## Bumping to a newer reusable workflow version

When this repo releases a new tag (e.g. `v1.0.5`):

1. Read [CHANGELOG.md](../CHANGELOG.md) to see if the bump is needed.
2. In each consumer repo, update `@v1.0.4` → `@v1.0.5` in `AutoMaintain.yml` and `Build.yml`.
3. Open a PR with that change. Build.yml runs against the new tag and validates the bump.
4. Merge once green.

There is no auto-bump mechanism today. A small future improvement would be a script in `scripts/` that opens version-bump PRs across all consumer repos.

# Troubleshooting

Common failures and their fixes. Issues are grouped by where in the pipeline they appear.

---

## Pick item step fails

### `Backlog file not found: /home/runner/work/<repo>/BACKLOG.md`

**Cause:** Caller workflow is pinned to an old tag (`@v1.0.0` or `@v1.0.1`) of the reusable workflow. Those versions had a bug in `parse_backlog.py` where `Path(__file__).parents[1]` resolved to the wrong directory in CI.

**Fix:** Bump the caller in `AutoMaintain.yml` and `Build.yml` to `@v1.0.4` or newer:

```yaml
uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.4
```

### `No eligible backlog item found`

**Cause:** No item in `BACKLOG.md` has `status: ready`, OR all ready items already have an open PR with label `automated`.

**Fix:**

```bash
# What's in the backlog?
gh pr list --label automated --state open

# Validate format
curl -sSL https://raw.githubusercontent.com/Answering-IT/answering-automation-infra/main/scripts/parse_backlog.py -o /tmp/parse_backlog.py
python /tmp/parse_backlog.py --validate

# What would be picked next?
python /tmp/parse_backlog.py --next
```

If the parser shows `null`, no item is eligible. Edit `BACKLOG.md` to set at least one item to `status: ready`.

### YAML parse errors

**Cause:** Common mistakes in `BACKLOG.md`:
- Tabs instead of spaces
- Missing colon after a field name
- Unescaped colons in unquoted strings (e.g. `context: Fix: the bug`)

**Fix:** Run the validator locally to see line numbers:

```bash
python /tmp/parse_backlog.py --validate
```

Quote strings that contain colons or use the `>` block style:

```yaml
# WRONG
context: Fix: the bug

# OK
context: "Fix: the bug"

# OK
context: >
  Fix: the bug
```

---

## Implement with Claude job fails

### `[@octokit/auth-app] appId option is required`

**Cause:** Repository secrets `AUTO_MAINTAIN_APP_ID` and/or `AUTO_MAINTAIN_APP_PRIVATE_KEY` are not set on the consumer repo.

**Fix:** Set them per [`ONBOARDING.md` Part 2](ONBOARDING.md#part-2-repository-secrets-manual-github-ui-or-cli). Verify:

```bash
gh secret list -R Answering-IT/<your-repo>
```

Both names must appear. Note: `Answering-IT` is a User account, not an Organization, so secrets must be at repo level — there's no org-level inheritance.

### `Not authorized to perform: sts:AssumeRoleWithWebIdentity`

**Cause:** The IAM role `GitHubActions-Answering-IT-SharedRole` doesn't trust this repo, or doesn't have the wildcard pattern.

**Fix:**

```bash
aws iam get-role \
  --role-name GitHubActions-Answering-IT-SharedRole \
  --query 'Role.AssumeRolePolicyDocument' \
  --profile ans-super
```

The condition should include `"repo:Answering-IT/*:*"`. If it lists specific repos instead, ask the platform team to update the trust policy. See [`ONBOARDING.md` Part F.2](ONBOARDING.md#f2-aws-iam-role-trust-policy).

### `Resource not accessible by integration`

**Cause:** The GitHub App `answering-auto-maintain` is not installed on this repo, or has insufficient permissions.

**Fix:** See [`ONBOARDING.md` Part 3](ONBOARDING.md#part-3-github-app-installation-manual-github-ui).

### Claude runs but exits without opening a PR

**Cause:** Most often, Claude's gates (`ruff`, `black`, `pytest`) failed and it correctly stopped instead of pushing broken code, OR the changes Claude made don't match the path filters in `Build.yml` so no checks run.

**Fix:**
1. Check the workflow run's `Run Claude Code (Bedrock)` step — Claude logs why it stopped.
2. If gates failed, the backlog item is likely too ambitious. Make it more specific or break it up.
3. If checks aren't running on the auto-PR, broaden `Build.yml` path filters to match what Claude touches.

### `refusing to allow a GitHub App to create or update workflow` when pushing to `.github/workflows/`

**Cause:** The GitHub App `answering-auto-maintain` doesn't have the `Workflows: Read & write` permission. This permission is required to push changes to files in the `.github/workflows/` directory.

**Symptoms:**
- Claude successfully makes changes and commits them locally
- Push fails with error: `refusing to allow a GitHub App to create or update workflow...`
- The branch exists locally but was never pushed to remote
- No PR is created

**Fix:**
1. Go to `https://github.com/settings/apps/answering-auto-maintain/permissions`
2. Under **Repository permissions**, find **Workflows**
3. Change it from `No access` to `Read and write`
4. Click **Save changes**
5. You may need to accept the permission change in each installed repository:
   - Go to `https://github.com/settings/installations`
   - Click **Configure** next to `answering-auto-maintain`
   - Review and accept the new permission request

**Note:** This permission is required ONLY if your backlog items include changes to workflow files. If you never need to modify `.github/workflows/`, you can skip this permission.

### Claude times out (30 min default)

**Cause:** Item too complex, or Claude stuck in a loop (tests failing, retries indefinitely).

**Fix:**
1. Run with `dry_run: true` to inspect the prompt without invoking Claude:
   ```bash
   gh workflow run AutoMaintain.yml -f dry_run=true
   ```
2. If the prompt looks right but the item is genuinely complex, split it into smaller backlog items.
3. As a last resort, increase timeout in your caller:
   ```yaml
   jobs:
     run:
       uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.4
       timeout-minutes: 60
   ```

---

## Auto-PR opens but no checks run

### `Build.yml` doesn't trigger on the auto-PR

**Cause:** One of:
1. Repo setting **Allow GitHub Actions to create and approve pull requests** is disabled
2. The workflow is using `GITHUB_TOKEN` instead of the GitHub App token (PRs from `GITHUB_TOKEN` don't dispatch downstream workflows — this is GitHub's anti-loop protection)
3. `Build.yml` path filters don't match the files Claude changed

**Fix:**

1. Repo settings → Actions → General → Workflow permissions → ✅ **Allow GitHub Actions to create and approve pull requests**. See [`ONBOARDING.md` Part 4](ONBOARDING.md#part-4-github-actions-setting-manual-github-ui-repo-level).

2. Verify `AutoMaintain.yml` passes both secrets to the reusable workflow:
   ```yaml
   secrets:
     AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
     AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
   ```

3. Broaden path filters or remove them entirely while debugging:
   ```yaml
   on:
     pull_request:
       branches: [main]
   ```

---

## Build.yml gate failures

### `pytest` fails with exit code 5 — and it shouldn't

If you're on `@v1.0.3` or older, exit code 5 (no tests collected) is treated as a failure. It's been fixed in `@v1.0.4`. Bump.

### `pytest` fails with exit code 2 — collection error

**Cause:** Test files import a module that isn't installed. Most common: `moto`, `boto3`, or another runtime/dev dep missing from `requirements-dev.txt` and not in any auto-discovered location.

**Fix:** Add the missing package to `requirements-dev.txt`. The reusable workflow auto-installs from:
- `requirements-dev.txt`
- `requirements.txt` (if present)
- `agents/requirements.txt` (if present)
- `infrastructure/lambdas/*/requirements.txt` (CDK Lambda pattern)

If your project has a different layout, you may need to add a custom install step in your repo's `Build.yml` instead of relying on the reusable workflow alone.

### `ruff check .` fails with rules you don't care about

**Cause:** The template `pyproject.toml` enables a pragmatic ruleset (`E,F,W,I` only). If you've inherited a stricter ruleset from somewhere else (`N,UP,B,SIM,C4,A`), it may flag a lot of style preferences.

**Fix:** Decide deliberately. Either:
1. Fix the violations (Claude can do this — make a backlog item).
2. Relax the ruleset by editing your repo's `pyproject.toml`:
   ```toml
   [tool.ruff.lint]
   select = ["E", "F", "W", "I"]
   ```
3. Add per-file ignores for legitimate cases (e.g. boto3 mock signatures use PascalCase):
   ```toml
   [tool.ruff.lint.per-file-ignores]
   "tests/**/*.py" = ["N803", "N806"]
   ```

### `black --check .` fails

**Fix:** Run `black .` locally and commit. Or let Claude do it as a backlog item: `acceptance_criteria: ["black --check . passes"]`.

---

## Repo-specific environment issues

### `Answering-IT` is not an Organization

`https://github.com/organizations/Answering-IT/settings/...` URLs return 404 or "page not found".

**Cause:** `Answering-IT` is a User account. Organization-only features (org secrets, teams, audit logs) don't apply.

**Implications:**
- Each consumer repo needs its own copies of `AUTO_MAINTAIN_APP_ID` and `AUTO_MAINTAIN_APP_PRIVATE_KEY`
- There's no `gh secret set --org` equivalent — only `--repo`
- If you want true central management, the User account would have to be converted to an Organization (irreversible)

This is documented in [README.md](../README.md#important-this-is-not-a-github-organization).

### Build.yml works but the auto-PR's Build.yml doesn't run

This is the same issue as [Auto-PR opens but no checks run](#auto-pr-opens-but-no-checks-run) — see that section.

---

## Versioning and updates

### I bumped the central workflow but consumers still use the old behavior

**Cause:** Consumers pin to an explicit version tag, e.g. `@v1.0.3`. Editing the workflow in this repo's main doesn't affect them until they explicitly bump the reference.

**Fix:** In each consumer repo's `AutoMaintain.yml` and `Build.yml`, update the tag:

```yaml
uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.5
```

Open a PR with that change in the consumer; the PR itself validates the bump.

The `@v1` floating tag exists but is **not recommended for production use** — pinning to a specific version makes upgrades deliberate and auditable.

### I updated `parse_backlog.py` but consumers still use the old version

**Cause:** Wait — did you update both the parser **and** the URL it's downloaded from?

The reusable workflow downloads the parser at runtime from:
```
https://raw.githubusercontent.com/Answering-IT/answering-automation-infra/main/scripts/parse_backlog.py
```

Pinned to `main`, deliberately, so parser fixes propagate without needing to bump the workflow tag. If you tagged the parser inside a workflow tag instead, that's an older bug — make sure your workflow uses `main` for the parser URL.

---

## Cost surprises

### Bedrock costs higher than expected

**Cause:** Either too many runs, or items too complex.

**Fix:**
- Don't enable a `schedule:` trigger until you've validated your backlog quality with manual runs
- Use `dry_run: true` to test prompt quality without paying for inference
- Review logs of completed runs — `--max-turns 40` is the cap; if Claude is consistently hitting it, the items are too big
- Set an AWS Budget alert: Console → Billing → Budgets → Create budget for Bedrock service

---

## When all else fails

1. Check the workflow run logs end-to-end. The actual error is usually in the last step that ran, not the step that says "completed with exit code N".
2. Compare against `external-ingester-consumer-lambda` — that's the reference working pilot. If something works there but not in your repo, the difference is the bug.
3. Open an issue in `Answering-IT/answering-automation-infra` with:
   - The failing run URL
   - The relevant `BACKLOG.md` item (if applicable)
   - What you've already tried

---

## Useful one-liners

```bash
# What version is each consumer using?
for repo in external-ingester-consumer-lambda kb-rag-agent; do
  echo "=== $repo ==="
  gh api "/repos/Answering-IT/$repo/contents/.github/workflows/AutoMaintain.yml" --jq '.content' | base64 -d | grep "uses:"
done

# Watch the latest AutoMaintain run live
gh run watch $(gh run list --workflow=AutoMaintain.yml --limit 1 --json databaseId --jq '.[0].databaseId') -R Answering-IT/<repo>

# List all open auto-opened PRs across repos
for repo in external-ingester-consumer-lambda kb-rag-agent; do
  gh pr list --label automated --state open -R "Answering-IT/$repo"
done
```

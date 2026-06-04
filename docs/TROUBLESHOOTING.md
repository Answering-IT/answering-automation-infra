# Troubleshooting

Common issues and solutions when using the auto-maintain workflow.

---

## Workflow Issues

### No eligible backlog item found

**Symptoms:**
- Workflow completes in <1 minute
- Log shows: "No eligible backlog item found."
- No PR opened

**Causes:**
1. No items in BACKLOG.md have `status: ready`
2. All ready items already have open PRs with label `automated`
3. BACKLOG.md is malformed (parser fails silently)

**Fixes:**

**Check 1: Validate BACKLOG.md locally**
```bash
# Download parser
curl -sSL https://raw.githubusercontent.com/Answering-IT/answering-automation-infra/v1.0.0/scripts/parse_backlog.py -o parse_backlog.py

# Validate format
python parse_backlog.py --validate

# See what would be picked
python parse_backlog.py --next
```

**Check 2: Look for open automated PRs**
```bash
gh pr list --label automated --state open
```

**Check 3: Edit BACKLOG.md**
- Ensure at least one item has `status: ready`
- Check YAML syntax (no tabs, proper indentation)

---

### Parser fails with "Invalid YAML"

**Symptoms:**
- Workflow fails in "Pick item" step
- Error mentions YAML parsing

**Causes:**
- Indentation uses tabs instead of spaces
- Missing colon after field name
- Unescaped special characters in strings

**Fixes:**

**Use the validator:**
```bash
python parse_backlog.py --validate
# Shows line numbers with errors
```

**Common mistakes:**
```yaml
# ❌ WRONG - tabs instead of spaces
	status: ready

# ✅ CORRECT - spaces
  status: ready

# ❌ WRONG - missing colon
status ready

# ✅ CORRECT
status: ready

# ❌ WRONG - unescaped colon in string
context: Fix: the bug

# ✅ CORRECT - quoted or use >
context: "Fix: the bug"
# or
context: >
  Fix: the bug
```

---

### Claude invocation times out

**Symptoms:**
- Workflow runs for 30 minutes then fails
- Last step shows "timeout"

**Causes:**
- Item is too complex (requires > 40 turns)
- Claude is stuck in a loop (tests failing repeatedly)
- External dependency unavailable (pip/npm registry down)

**Fixes:**

**1. Run dry-run first to validate prompt:**
```bash
gh workflow run AutoMaintain.yml -f dry_run=true
# Check logs for prompt quality
```

**2. Reduce item scope:**
- Split large items into smaller ones
- Make acceptance criteria more specific
- Pre-create files that Claude should edit (easier than creating from scratch)

**3. Override timeout (edit your AutoMaintain.yml caller):**
```yaml
jobs:
  run:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.0
    timeout-minutes: 60  # Increase from default 30
```

---

### Permission denied when invoking Claude

**Symptoms:**
- Workflow fails at "Run Claude Code (Bedrock)" step
- Error: "permission_denials_count: X"

**Causes:**
- `--allowedTools` list too restrictive
- New tool needed but not in allowed list

**Fixes:**

**Check claude-code-action logs:**
- Look for which tools were denied
- Add to `claude_args: --allowedTools` in `auto-maintain-reusable.yml`

**Example addition:**
```yaml
claude_args: |
  --allowedTools "Read,Write,...,Bash(your-new-command:*)"
```

**Then tag new version and update callers:**
```bash
cd answering-automation-infra
git add .github/workflows/auto-maintain-reusable.yml
git commit -m "feat: allow new tool"
git tag v1.1.0
git push --tags
```

---

## PR Issues

### Auto-opened PR doesn't trigger Build.yml

**Symptoms:**
- PR opened successfully
- No checks run
- PR shows "No checks have run"

**Causes:**
1. Org setting disabled
2. Using `GITHUB_TOKEN` instead of GitHub App token
3. Build.yml path filters exclude changed files

**Fixes:**

**Check 1: Org setting**
```
Settings → Actions → General
✅ "Allow GitHub Actions to create and approve pull requests"
```

**Check 2: GitHub App token configured**
In `AutoMaintain.yml` caller:
```yaml
secrets:
  AUTO_MAINTAIN_APP_ID: ${{ secrets.AUTO_MAINTAIN_APP_ID }}
  AUTO_MAINTAIN_APP_PRIVATE_KEY: ${{ secrets.AUTO_MAINTAIN_APP_PRIVATE_KEY }}
```

Verify secrets exist:
```bash
gh secret list
# Should show AUTO_MAINTAIN_APP_ID and AUTO_MAINTAIN_APP_PRIVATE_KEY
```

**Check 3: Path filters**
In `Build.yml`, ensure paths cover files Claude changed:
```yaml
on:
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'
      - '**/*.py'  # Add broad patterns if needed
```

---

### Build.yml checks fail on auto-opened PR

**Symptoms:**
- PR opened
- Checks run but fail
- Linter or tests report errors

**Causes:**
- Claude generated code doesn't pass gates
- Env mismatch (different Python/Node version)
- Missing dependencies

**Fixes:**

**1. Review PR changes:**
```bash
gh pr checkout <PR-number>
# Run gates locally
ruff check .
black --check .
pytest -m "unit or smoke"
```

**2. Add fixes to the PR:**
```bash
# Make fixes
git add .
git commit -m "fix: address gate failures"
git push
```

**3. Close PR and re-run with better prompt:**
If fixes are too complex, close PR and improve the backlog item:
- Add more context
- Specify edge cases to avoid
- Reference similar existing code

---

### PR has wrong branch name

**Symptoms:**
- Expected: `auto/item-id`
- Actual: Something else

**Cause:**
- `claude-code-action` branch_prefix misconfigured

**Fix:**
In `auto-maintain-reusable.yml`:
```yaml
- name: Run Claude Code (Bedrock)
  uses: anthropics/claude-code-action@v1
  with:
    branch_prefix: 'auto/'  # Must match
```

---

## AWS/Bedrock Issues

### Role not authorized to assume

**Symptoms:**
- Workflow fails at "Configure AWS credentials (OIDC)"
- Error: "Not authorized to perform: sts:AssumeRoleWithWebIdentity"

**Causes:**
- IAM role trust policy doesn't include this repo
- Role ARN incorrect

**Fixes:**

**Check trust policy:**
```bash
aws iam get-role --role-name GitHubActions-Answering-IT-SharedRole \
  --query 'Role.AssumeRolePolicyDocument' \
  --profile ans-super
```

**Should contain:**
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

**If missing wildcard, update policy:**
```bash
# Save policy to file, edit, then:
aws iam update-assume-role-policy \
  --role-name GitHubActions-Answering-IT-SharedRole \
  --policy-document file://trust-policy.json \
  --profile ans-super
```

---

### Bedrock throttling errors

**Symptoms:**
- Error: "ThrottlingException"
- Error: "Rate exceeded"

**Causes:**
- Too many concurrent invocations
- Model quota reached

**Fixes:**

**1. Check current quotas:**
```bash
aws service-quotas list-service-quotas \
  --service-code bedrock \
  --region us-east-1 \
  --profile ans-super
```

**2. Request quota increase:**
- Console → Service Quotas → AWS Bedrock
- Find "Invocations per minute"
- Request increase

**3. Add retry logic (advanced):**
Edit `auto-maintain-reusable.yml` to add exponential backoff (future enhancement).

---

### Wrong model invoked

**Symptoms:**
- Logs show different model than expected
- Costs higher than expected

**Cause:**
- `bedrock_model` input incorrect

**Fix:**
In your repo's `AutoMaintain.yml` caller:
```yaml
with:
  bedrock_model: us.anthropic.claude-sonnet-4-6  # Verify this
```

**Valid model IDs:**
- `us.anthropic.claude-sonnet-4-6` (cross-region inference profile)
- `anthropic.claude-sonnet-4-6` (single-region)
- `anthropic.claude-opus-4-7` (more expensive, more capable)

---

## Local Testing Issues

### parse_backlog.py not found

**Cause:**
- Parser not downloaded yet

**Fix:**
```bash
curl -sSL https://raw.githubusercontent.com/Answering-IT/answering-automation-infra/v1.0.0/scripts/parse_backlog.py -o parse_backlog.py
pip install pyyaml
python parse_backlog.py --validate
```

---

### Tests pass locally but fail in CI

**Causes:**
- Different Python/Node version
- Cached dependencies locally
- Absolute paths in test fixtures

**Fixes:**

**Check 1: Version mismatch**
```bash
# CI uses .python-version file
cat .python-version  # Should be 3.11
python --version     # Local should match
```

**Check 2: Reset local env**
```bash
deactivate
rm -rf .venv
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -r requirements.txt
pytest -m "unit or smoke"
```

**Check 3: Absolute paths**
```python
# ❌ WRONG
def test_load_file():
    data = load("/Users/me/project/data.json")

# ✅ CORRECT - relative to repo root
def test_load_file(tmp_path):
    data_file = tmp_path / "data.json"
    data_file.write_text('{"key": "value"}')
    data = load(data_file)
```

---

## Cost Issues

### Bedrock costs higher than expected

**Symptoms:**
- AWS bill shows high Bedrock charges
- Multiple items implemented in one day

**Causes:**
- Too many automatic runs (if cron enabled)
- Items too complex (require many turns)
- No budget alerts configured

**Fixes:**

**1. Disable cron, use workflow_dispatch only:**
```yaml
on:
  # Remove schedule block
  workflow_dispatch:
    # ... keep inputs
```

**2. Use dry-run first:**
```bash
gh workflow run AutoMaintain.yml -f dry_run=true
# Review prompt, then run for real
```

**3. Set AWS budget alert:**
```bash
# CloudWatch → Billing → Create budget
# Alert when Bedrock costs > $X/month
```

**4. Review item complexity:**
- Simplify acceptance criteria
- Pre-create stub files
- Split large items into smaller ones

---

## Updating Central Repo

### New workflow version doesn't apply

**Symptoms:**
- Updated `auto-maintain-reusable.yml` in central repo
- Consumer repos still use old behavior

**Cause:**
- Caller workflows pinned to old tag (`@v1.0.0`)

**Fix:**

**1. Tag new version in central repo:**
```bash
cd answering-automation-infra
git tag v1.1.0
git push --tags
```

**2. Update caller in each consumer repo:**
```yaml
jobs:
  run:
    uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.1.0
    #                                                                                           ^^^^^^^ bump
```

**3. Automate bump (future):**
Script to open PRs across all repos updating the tag.

---

### Parser changes break consumer repos

**Symptoms:**
- Parser updated in central repo
- Consumer workflows fail with "AttributeError"

**Cause:**
- Breaking change in parser API

**Fix:**

**Use semantic versioning:**
- `v1.x.x` - Backward-compatible (safe to bump)
- `v2.x.x` - Breaking change (requires consumer update)

**Consumer repos fetch via URL with version:**
```bash
curl -sSL https://raw.githubusercontent.com/Answering-IT/answering-automation-infra/v1.1.0/scripts/parse_backlog.py -o parse_backlog.py
#                                                                             ^^^^^^^ pin version
```

**Update URL in `auto-maintain-reusable.yml`:**
```yaml
- name: Download parser from central repo
  run: |
    curl -sSL https://raw.githubusercontent.com/Answering-IT/answering-automation-infra/v2.0.0/scripts/parse_backlog.py -o parse_backlog.py
```

Then bump tag and update all callers.

---

## Getting Help

If none of these solutions work:

1. **Check central repo issues:**
   https://github.com/Answering-IT/answering-automation-infra/issues

2. **Open a new issue:**
   - Title: Brief description
   - Include: Workflow run URL, error message, BACKLOG.md item
   - Tag: `help-wanted`

3. **Contact platform team:**
   - Slack: #platform-support

---

**Last Updated:** 2026-06-04  
**Version:** v1.0.0

#!/bin/bash
set -euo pipefail

# Validates auto-maintain setup for a repository
# Usage: ./validate-setup.sh Answering-IT/repo-name

if [ $# -ne 1 ]; then
  echo "Usage: $0 Answering-IT/repo-name"
  exit 1
fi

REPO="$1"

if [[ ! "${REPO}" =~ ^Answering-IT/.+ ]]; then
  echo "❌ Repository must be in format: Answering-IT/repo-name"
  exit 1
fi

echo "🔍 Validating auto-maintain setup for ${REPO}"
echo ""

ERRORS=0
WARNINGS=0

# Check 1: Required workflow files exist
echo "📁 Checking workflow files..."
if gh api "/repos/${REPO}/contents/.github/workflows/AutoMaintain.yml" &>/dev/null; then
  echo "  ✅ AutoMaintain.yml exists"
else
  echo "  ❌ AutoMaintain.yml missing"
  ((ERRORS++))
fi

if gh api "/repos/${REPO}/contents/.github/workflows/Build.yml" &>/dev/null; then
  echo "  ✅ Build.yml exists"
else
  echo "  ⚠️  Build.yml missing (optional but recommended)"
  ((WARNINGS++))
fi
echo ""

# Check 2: Repository secrets
echo "🔐 Checking repository secrets..."
SECRETS=$(gh secret list -R "${REPO}" --json name --jq '.[].name')

if echo "${SECRETS}" | grep -q "AUTO_MAINTAIN_APP_ID"; then
  echo "  ✅ AUTO_MAINTAIN_APP_ID is set"
else
  echo "  ❌ AUTO_MAINTAIN_APP_ID not set"
  echo "     Fix: gh secret set AUTO_MAINTAIN_APP_ID --body \"<APP_ID>\" -R ${REPO}"
  ((ERRORS++))
fi

if echo "${SECRETS}" | grep -q "AUTO_MAINTAIN_APP_PRIVATE_KEY"; then
  echo "  ✅ AUTO_MAINTAIN_APP_PRIVATE_KEY is set"
else
  echo "  ❌ AUTO_MAINTAIN_APP_PRIVATE_KEY not set"
  echo "     Fix: gh secret set AUTO_MAINTAIN_APP_PRIVATE_KEY -R ${REPO} < /path/to/key.pem"
  ((ERRORS++))
fi
echo ""

# Check 3: Actions permissions
echo "⚙️  Checking Actions permissions..."
# Note: This API doesn't expose the "Allow Actions to create PRs" setting
# User needs to verify manually
echo "  ℹ️  Cannot check via API - verify manually:"
echo "     Go to: https://github.com/${REPO}/settings/actions"
echo "     Ensure: ✅ Allow GitHub Actions to create and approve pull requests"
echo ""

# Check 4: GitHub App installation
echo "🤖 Checking GitHub App installation..."
INSTALLATIONS=$(gh api /user/installations --jq '.installations[] | select(.app_slug=="answering-auto-maintain") | .id')

if [ -n "${INSTALLATIONS}" ]; then
  echo "  ✅ GitHub App 'answering-auto-maintain' is installed"

  # Check if installed on this specific repo
  # Note: This requires checking each installation's repo list
  echo "  ℹ️  Verify it's installed on ${REPO}:"
  echo "     Go to: https://github.com/settings/installations"
  echo "     Or: https://github.com/${REPO}/settings/installations"
else
  echo "  ❌ GitHub App 'answering-auto-maintain' not found"
  echo "     Install at: https://github.com/apps/answering-auto-maintain"
  ((ERRORS++))
fi
echo ""

# Check 5: GitHub App permissions (check the app itself, not per-repo)
echo "🔑 Checking GitHub App permissions..."
echo "  ℹ️  Manually verify at: https://github.com/settings/apps/answering-auto-maintain/permissions"
echo ""
echo "  Required permissions (all Read and write):"
echo "    • Contents"
echo "    • Issues"
echo "    • Pull requests"
echo "    • Workflows ⚠️  CRITICAL - often missing!"
echo ""
echo "  If Workflows is missing:"
echo "    1. Go to the permissions URL above"
echo "    2. Set Workflows to 'Read and write'"
echo "    3. Save changes"
echo "    4. Accept the permission update in each installed repository"
echo ""

# Check 6: Branch protection (optional)
echo "🛡️  Checking branch protection..."
PROTECTION=$(gh api "/repos/${REPO}/branches/main/protection" 2>/dev/null || echo "none")

if [ "${PROTECTION}" = "none" ]; then
  echo "  ⚠️  No branch protection on 'main'"
  echo "     This is optional but recommended"
  echo "     Setup at: https://github.com/${REPO}/settings/branches"
  ((WARNINGS++))
else
  echo "  ✅ Branch protection configured on 'main'"
fi
echo ""

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ ${ERRORS} -eq 0 ]; then
  echo "✅ Validation passed (${WARNINGS} warnings)"
  echo ""
  echo "Next steps:"
  echo "  1. Manually verify the items marked with ℹ️  above"
  echo "  2. Test with dry run:"
  echo "     gh workflow run AutoMaintain.yml -f dry_run=true -R ${REPO}"
  echo "  3. Full test run:"
  echo "     gh workflow run AutoMaintain.yml -R ${REPO}"
  exit 0
else
  echo "❌ Validation failed: ${ERRORS} error(s), ${WARNINGS} warning(s)"
  echo ""
  echo "Fix the errors above before proceeding."
  echo "See: https://github.com/Answering-IT/answering-automation-infra/blob/main/docs/COMPLETE-SETUP-GUIDE.md"
  exit 1
fi

#!/usr/bin/env bash
# Quick test for parse_github_issues.py
# Requires: gh CLI authenticated, GH_TOKEN set if needed

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PARSER="${SCRIPT_DIR}/parse_github_issues.py"

# Test repo (use one with issues created by the documentation workflow)
TEST_REPO="${1:-Answering-IT/kb-rag-agent-fe}"

echo "Testing parse_github_issues.py against ${TEST_REPO}"
echo ""

echo "1. Listing all issues..."
python "${PARSER}" --repo "${TEST_REPO}" --list | jq -r '.[] | "  - [\(.priority)] \(.title)"'
echo ""

echo "2. Validating issues..."
python "${PARSER}" --repo "${TEST_REPO}" --validate
echo ""

echo "3. Selecting next item..."
NEXT=$(python "${PARSER}" --repo "${TEST_REPO}" --next)
if [ "${NEXT}" = "null" ]; then
  echo "  No eligible items"
else
  echo "${NEXT}" | jq -r '"  Picked: \(.id) — \(.title)"'
fi
echo ""

echo "✅ Test complete"

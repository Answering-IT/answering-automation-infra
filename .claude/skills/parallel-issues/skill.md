---
skill: parallel-issues
description: Orchestrate parallel issue development with worktrees and priority handling
---

# Parallel Issue Development Skill

You are orchestrating parallel issue development. Follow this workflow:

## Phase 1: Fetch & Organize Issues

1. Fetch open issues from GitHub:
   ```bash
   gh issue list --json number,title,body,labels --state open --limit 50 > /tmp/issues.json
   ```

2. Parse issues and organize by:
   - **Priority**: Extract from `**Priority:** high/medium/low` in issue body
   - **Dependencies**: Extract from `**Dependencies:** title1, title2` in issue body
   - **Status**: Check for `blocked` label

3. Build dependency graph and compute ready issues (dependencies satisfied)

4. Display organized issue list:
   ```
   === High Priority (2 issues) ===
   #24: Send Discord notification on workflow success
   #25: Send Discord notification on workflow failure
   
   === Medium Priority (1 issue) ===
   #27: Add long-running session monitor
   
   === Blocked (1 issue) ===
   #26: Validate notification flow (depends on #24, #25)
   ```

5. Ask user: "Ready to create worktrees for these issues?"

## Phase 2: Create Worktrees

For each ready issue (by priority order):

1. Create worktree:
   ```bash
   git worktree add .trees/auto-{issue_id} -b auto/issue-{issue_id}
   ```

2. Symlink .venv if exists:
   ```bash
   [ -d .venv ] && ln -s "$(pwd)/.venv" .trees/auto-{issue_id}/.venv
   ```

3. Track created worktrees in a list

4. Display summary:
   ```
   Created 3 worktrees:
   - .trees/auto-24 (high priority)
   - .trees/auto-25 (high priority)
   - .trees/auto-27 (medium priority)
   ```

## Phase 3: Implement Issues (Guided Workflow)

For each issue in priority order:

1. **Switch context**: 
   ```bash
   cd .trees/auto-{issue_id}
   ```

2. **Display issue details**:
   ```
   Working on: #{issue_id} - {title}
   Priority: {priority}
   
   ## Context
   {context from issue body}
   
   ## Acceptance Criteria
   {criteria from issue body}
   ```

3. **Implement the feature** following the issue requirements

4. **Create atomic commit**:
   ```bash
   git add .
   git commit -m "feat(issue-{issue_id}): {brief description}"
   ```

5. **Validate commit**:
   - Check message format: `feat(issue-N):` or `fix(issue-N):`
   - Check exactly one commit on branch: `git log main..HEAD --oneline`

6. **Return to root**:
   ```bash
   cd ../..
   ```

7. Ask: "Issue #{issue_id} complete. Continue to next issue?"

**Important**: Work through issues in priority order (high → medium → low) and respect dependencies.

## Phase 4: Create Pull Requests

After all issues are implemented:

1. For each completed worktree (in dependency order):
   
   ```bash
   cd .trees/auto-{issue_id}
   
   # Push branch
   git push origin auto/issue-{issue_id}
   
   # Create PR
   gh pr create \
     --title "$(git log -1 --pretty=%s)" \
     --body "Closes #{issue_id}" \
     --base main \
     --head auto/issue-{issue_id}
   
   cd ../..
   ```

2. Display PR summary:
   ```
   Created PRs:
   ✓ #24 → PR #45: https://github.com/owner/repo/pull/45
   ✓ #25 → PR #46: https://github.com/owner/repo/pull/46
   ✓ #27 → PR #47: https://github.com/owner/repo/pull/47
   ```

3. **Keep worktrees** (don't remove them) - useful for PR review fixes

## Phase 5: Summary & Cleanup Guide

Display final summary:
```
=== Parallel Development Summary ===
✓ 3 issues implemented
✓ 3 PRs created
✓ Worktrees kept for potential fixes

Next steps:
1. Review PRs in GitHub
2. Make fixes in worktrees if needed:
   cd .trees/auto-{id}
   # make changes
   git commit --amend --no-edit
   git push origin auto/issue-{id} --force
   
3. After PRs merged, clean up:
   git worktree remove .trees/auto-{id}
```

## Error Handling

**If issue has unsatisfied dependencies**:
- Skip for now
- Add to blocked list
- Process after dependencies are completed

**If worktree already exists**:
- Warn user
- Ask: "Worktree exists. Remove and recreate? (yes/no)"

**If commit format is wrong**:
- Show error
- Ask user to fix with: `git commit --amend`
- Validate again before proceeding

**If PR creation fails**:
- Log error
- Continue with other PRs
- Show failed issues at end for manual review

## Special Cases

**Single issue mode**: If user provides `--issue N`, only process that issue

**Dry run**: If user wants to see plan first, show organized list without creating worktrees

**Interactive mode**: Ask for confirmation between each phase

## Repository Detection

Auto-detect repository from:
1. `$GITHUB_REPOSITORY` env var
2. Git remote: `git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/'`
3. Ask user if not found

## Notes

- Always use `.trees/auto-{issue_id}` naming convention
- Always use `auto/issue-{issue_id}` branch names
- Enforce commit message format: `feat(issue-N):` or `fix(issue-N):`
- Include `Closes #{issue_id}` in PR body for auto-linking
- Process issues by priority: high → medium → low
- Respect dependencies: block dependent issues until dependencies complete
- Keep worktrees after PR creation for potential fixes

# Parallel Development System

Automated parallel issue development with intelligent conflict resolution.

## Overview

This system enables you to:
1. Work on multiple GitHub issues in parallel using git worktrees
2. Create PRs with proper dependency metadata
3. Get Discord notifications about conflicts
4. Automatically resolve conflicts with an autonomous agent

## Components

```
.claude/
├── skills/
│   └── parallel-issues/       # Main orchestration skill
│       └── skill.md
├── agents/
│   └── conflict-resolver/     # Autonomous conflict resolution
│       └── agent.md
└── lib/
    ├── discord_notify.sh      # Discord webhook helper
    ├── conflict_analyzer.sh   # PR conflict prediction
    └── smart_rebase.sh        # Intelligent conflict resolution
```

## Quick Start

### 1. Run the Parallel Issues Skill

In any Claude session in this repository:

```
/parallel-issues
```

This will:
- ✅ Fetch open GitHub issues
- ✅ Organize by priority (high/medium/low)
- ✅ Create worktrees in `.trees/auto-{issue-id}/`
- ✅ Guide you through implementing each issue
- ✅ Create PRs with dependency metadata
- ✅ Analyze conflicts and send Discord notification

### 2. Review the Discord Notification

You'll get a Discord message like:

```
🚀 Parallel Development Complete

✅ Ready to Merge (No Conflicts)
  PR #32

⚠️ Will Need Rebase (Conflicts Expected)
  PR #33 (conflicts with #32)
  PR #34 (conflicts with #32, #33)

📋 Merge Order
  #32 → #33 → #34

Next Steps:
1. Review PRs in GitHub
2. Spawn conflict-resolver agent if needed
3. Merge PRs in order
```

### 3. Spawn Conflict Resolver Agent

When you're ready to merge the PRs:

```
Tell Claude: "Spawn the conflict-resolver agent"
```

The agent will:
- ✅ Guide you through merging each PR in order
- ✅ Rebase dependent PRs after each merge
- ✅ Intelligently fix conflicts
- ✅ Wait for your confirmation at each step

## Workflow Example

### Scenario: 3 PRs that edit the same workflow file

```bash
# Phase 1: Create all PRs
/parallel-issues

# You implement:
# - PR #32: Add success notification (high priority)
# - PR #33: Add failure notification (high priority)  
# - PR #34: Add monitoring job (medium priority)

# All 3 PRs created! 🎉

# Phase 2: Conflict resolution
# Discord notifies: PR #33 and #34 will conflict

# Phase 3: Merge with agent assistance
User: "Spawn conflict-resolver"

Agent: "PR #32 ready to merge (no conflicts)"
Agent: "Please merge #32 in GitHub"

User: [merges PR #32 in GitHub UI]
User: "merged"

Agent: "Rebasing PR #33..."
Agent: "Conflict in workflow.yml detected"
Agent: "I see #33 adds failure notification after duration step"
Agent: "I see #32 added success notification in same section"
Agent: "Resolved: Placed both notifications in logical order"
Agent: "✅ PR #33 updated and ready"
Agent: "Please merge #33 in GitHub"

User: [merges PR #33 in GitHub UI]
User: "merged"

Agent: "Rebasing PR #34..."
Agent: "✅ PR #34 updated, all done!"
```

## How It Works

### Issue Metadata Format

Issues must include this metadata in the body:

```markdown
**Priority:** high
**Dependencies:** Issue title 1, Issue title 2

## Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
```

### Commit Message Format

Each PR must have an atomic commit matching:

```
feat(issue-N): Brief description

or

fix(issue-N): Brief description
```

### PR Metadata

Each worktree contains `PR_METADATA.json`:

```json
{
  "pr_number": 32,
  "issue_id": 24,
  "priority": "high",
  "dependencies": [22, 23],
  "created_at": "2026-06-07T14:30:00Z"
}
```

### Conflict Analysis

The system predicts conflicts by:
1. Checking which PRs edit the same files
2. Building a conflict matrix
3. Determining merge order
4. Notifying via Discord

### Smart Conflict Resolution

The agent resolves conflicts by:
1. Knowing what each PR originally changed
2. Understanding file types (YAML, code, config)
3. Keeping both PR's changes in logical order
4. Preserving each PR's intent

## Library Functions

### discord_notify.sh

```bash
source .claude/lib/discord_notify.sh

# Send embed
send_discord_embed "$webhook" "Title" "Description" "$COLOR" "$fields_json"

# Send simple message
send_discord_message "$webhook" "Message text"

# Colors
DISCORD_COLOR_SUCCESS=5763719   # Green
DISCORD_COLOR_WARNING=16776960  # Yellow
DISCORD_COLOR_ERROR=15158332    # Red
```

### conflict_analyzer.sh

```bash
source .claude/lib/conflict_analyzer.sh

# Get files changed in PR
get_pr_files 32

# Check if two PRs conflict
prs_conflict 32 33

# Build conflict matrix
build_conflict_matrix "32 33 34"

# Compute merge order
compute_merge_order "32 33 34" "33:32 34:32,33"
```

### smart_rebase.sh

```bash
source .claude/lib/smart_rebase.sh

# Rebase with smart conflict resolution
smart_rebase ".trees/auto-33" 33

# Push rebased branch
push_rebased_branch ".trees/auto-33" 33

# Full workflow
rebase_and_push ".trees/auto-33" 33
```

## File Structure

```
.trees/                      # Git worktrees (one per issue)
├── auto-24/
│   ├── PR_METADATA.json     # PR metadata
│   └── [source code]        # Isolated workspace
├── auto-25/
└── auto-27/

logs/                        # Execution logs (if needed)
```

## Configuration

### Discord Webhook

Currently hardcoded in `skills/parallel-issues/skill.md`:
```
https://discord.com/api/webhooks/1513268978670108744/JOSFHiPfLroRMy9KzcWqcwXSZdM02mJxWGlYjD4BBbd_N_jnZHxdKYEoPsAUAdQTCmiH
```

To change: Edit the webhook URL in the skill file.

### Priority Levels

- `high` - Processed first (parallel within tier)
- `medium` - Processed after high
- `low` - Processed last

## Cleanup

After all PRs are merged:

```bash
# Remove all worktrees
git worktree prune
rm -rf .trees/

# Or remove individually
git worktree remove .trees/auto-24
```

## Portability

To use this system in another repository:

1. Copy the entire `.claude/` directory
2. Update the Discord webhook URL (optional)
3. Add `.trees/` and `logs/` to `.gitignore`

That's it! The system is fully self-contained.

## Advanced Usage

### Single Issue Mode

Process only one issue:

```
Tell Claude: "Use parallel-issues skill for issue #27 only"
```

### Skip Conflict Resolution

Create PRs without running the agent:

```
/parallel-issues
# When asked to spawn agent, say "no"
# Merge PRs manually in GitHub
```

### Manual Rebase

Fix conflicts manually without the agent:

```bash
cd .trees/auto-33
git fetch origin main
git rebase origin/main
# Fix conflicts
git add .
git rebase --continue
git push origin auto/issue-33 --force
```

## Troubleshooting

### "Worktree already exists"

```bash
git worktree remove .trees/auto-24
# Or
git worktree remove --force .trees/auto-24
```

### "Invalid commit message"

```bash
cd .trees/auto-24
git commit --amend -m "feat(issue-24): your description"
cd ../..
```

### "PR creation failed"

Check if PR already exists:
```bash
gh pr list --head auto/issue-24
```

### "Rebase conflicts"

The agent should handle this, but if needed manually:
```bash
cd .trees/auto-33
git rebase --abort  # Start fresh
git fetch origin main
git rebase origin/main
# Resolve conflicts
git add .
git rebase --continue
```

## Design Decisions

### Why worktrees?

- Parallel work without branch switching
- Each issue has isolated workspace
- Easy to context-switch between issues

### Why not merge PRs automatically?

- User maintains control
- PR approvals and CI checks happen
- Clear audit trail in GitHub

### Why Discord notifications?

- Immediate visibility of conflicts
- Team awareness of parallel work
- Mobile notifications

### Why agent for conflicts?

- Autonomous operation
- Intelligent resolution
- Guides user through process

## Future Enhancements

- [ ] Multiple repository support
- [ ] Cost tracking per issue
- [ ] Auto-merge when CI passes
- [ ] Configurable webhook in settings
- [ ] Dry-run mode for testing

---

**Created**: 2026-06-07  
**Version**: 1.0 (Prototype)  
**Repository**: kb-rag-agent-fe

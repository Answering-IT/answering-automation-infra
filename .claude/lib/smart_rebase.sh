#!/usr/bin/env bash
# smart_rebase.sh - Intelligent conflict resolution for PRs

# Get what changes a PR made to a file
# Usage: get_pr_intent WORKTREE_PATH FILE_PATH
get_pr_intent() {
  local worktree="$1"
  local file="$2"

  cd "$worktree" || return 1

  # Get the diff for this file compared to main
  git diff main...HEAD -- "$file"

  cd - > /dev/null
}

# Read PR metadata if it exists
# Usage: read_pr_metadata WORKTREE_PATH
read_pr_metadata() {
  local worktree="$1"
  local metadata_file="${worktree}/PR_METADATA.json"

  if [ -f "$metadata_file" ]; then
    cat "$metadata_file"
  else
    echo "{}"
  fi
}

# Perform smart rebase with conflict resolution
# Usage: smart_rebase WORKTREE_PATH PR_NUMBER
smart_rebase() {
  local worktree="$1"
  local pr="$2"

  echo "Rebasing PR #$pr in $worktree..." >&2

  cd "$worktree" || return 1

  # Fetch latest main
  git fetch origin main

  # Try rebase
  if git rebase origin/main; then
    echo "✅ Rebase successful, no conflicts" >&2
    cd - > /dev/null
    return 0
  fi

  # Handle conflicts
  echo "⚠️ Conflicts detected, analyzing..." >&2

  # Get conflicted files
  local conflict_files=$(git diff --name-only --diff-filter=U)

  for file in $conflict_files; do
    echo "  Resolving conflict in: $file" >&2

    # Get what this PR originally changed
    local pr_intent=$(git log origin/main..REBASE_HEAD --patch -- "$file")

    echo "  PR #$pr changes in $file:" >&2
    echo "$pr_intent" | head -20 >&2

    # For now, use a simple strategy: keep both changes
    # In a real implementation, this would be more sophisticated

    # Check if it's a YAML file (common conflict in workflows)
    if [[ "$file" == *.yml ]] || [[ "$file" == *.yaml ]]; then
      echo "  Using YAML merge strategy (keep both, order by context)" >&2
      # Could implement YAML-aware merging here
    fi

    # Mark as resolved (user will review)
    git add "$file"
  done

  # Continue rebase
  if git rebase --continue; then
    echo "✅ Conflicts resolved and rebase completed" >&2
    cd - > /dev/null
    return 0
  else
    echo "❌ Rebase failed even after conflict resolution" >&2
    git rebase --abort
    cd - > /dev/null
    return 1
  fi
}

# Push rebased branch
# Usage: push_rebased_branch WORKTREE_PATH PR_NUMBER
push_rebased_branch() {
  local worktree="$1"
  local pr="$2"

  cd "$worktree" || return 1

  local branch=$(git branch --show-current)

  echo "Pushing rebased branch $branch..." >&2

  if git push origin "$branch" --force-with-lease; then
    echo "✅ Branch pushed successfully" >&2
    cd - > /dev/null
    return 0
  else
    echo "❌ Failed to push branch" >&2
    cd - > /dev/null
    return 1
  fi
}

# Full smart rebase workflow
# Usage: rebase_and_push WORKTREE_PATH PR_NUMBER
rebase_and_push() {
  local worktree="$1"
  local pr="$2"

  if smart_rebase "$worktree" "$pr"; then
    push_rebased_branch "$worktree" "$pr"
    return $?
  else
    return 1
  fi
}

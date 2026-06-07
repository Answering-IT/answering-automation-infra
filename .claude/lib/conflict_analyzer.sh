#!/usr/bin/env bash
# conflict_analyzer.sh - Analyze potential conflicts between PRs

# Get files changed in a PR
# Usage: get_pr_files PR_NUMBER
get_pr_files() {
  local pr="$1"
  gh pr view "$pr" --json files -q '.files[].path' 2>/dev/null
}

# Get line ranges changed in a file for a PR
# Usage: get_pr_file_changes PR_NUMBER FILE_PATH
get_pr_file_changes() {
  local pr="$1"
  local file="$2"

  # Get diff stat showing line numbers
  gh pr diff "$pr" --patch 2>/dev/null | \
    grep -A 50 "^diff --git.*${file}" | \
    grep "^@@" | \
    sed 's/@@ -[0-9,]* +\([0-9,]*\).*/\1/'
}

# Check if two PRs conflict (edit same files)
# Usage: prs_conflict PR1 PR2
prs_conflict() {
  local pr1="$1"
  local pr2="$2"

  local files1=$(get_pr_files "$pr1")
  local files2=$(get_pr_files "$pr2")

  # Check for common files
  local common=$(comm -12 <(echo "$files1" | sort) <(echo "$files2" | sort))

  [ -n "$common" ]
}

# Build conflict matrix for all PRs
# Usage: build_conflict_matrix PR_NUMBERS
# Output: JSON with conflicts
build_conflict_matrix() {
  local prs="$1"

  declare -A conflicts

  for pr1 in $prs; do
    local pr1_files=$(get_pr_files "$pr1")

    for pr2 in $prs; do
      # Skip same PR and already checked pairs
      [ "$pr1" -ge "$pr2" ] && continue

      local pr2_files=$(get_pr_files "$pr2")

      # Find common files
      local common=$(comm -12 <(echo "$pr1_files" | sort) <(echo "$pr2_files" | sort))

      if [ -n "$common" ]; then
        # Store conflict
        conflicts["$pr1"]="${conflicts[$pr1]} $pr2"
        conflicts["$pr2"]="${conflicts[$pr2]} $pr1"

        echo "Conflict: PR #$pr1 and PR #$pr2 both edit: $common" >&2
      fi
    done
  done

  # Output conflicts
  for pr in $prs; do
    if [ -n "${conflicts[$pr]}" ]; then
      echo "$pr:${conflicts[$pr]}"
    fi
  done
}

# Compute merge order respecting dependencies
# Usage: compute_merge_order PR_NUMBERS DEPENDENCY_MAP
# DEPENDENCY_MAP format: "PR:dep1,dep2,dep3 PR:dep1"
compute_merge_order() {
  local prs="$1"
  local dep_map="$2"

  local ordered=""
  local remaining="$prs"

  # Topological sort
  while [ -n "$remaining" ]; do
    local found_ready=false

    for pr in $remaining; do
      # Get dependencies for this PR
      local deps=$(echo "$dep_map" | grep "^${pr}:" | cut -d: -f2)

      # Check if all deps are in ordered list
      local all_satisfied=true
      if [ -n "$deps" ]; then
        for dep in ${deps//,/ }; do
          if ! echo "$ordered" | grep -q "\b$dep\b"; then
            all_satisfied=false
            break
          fi
        done
      fi

      # If all deps satisfied, add to ordered list
      if [ "$all_satisfied" = true ]; then
        ordered="$ordered $pr"
        remaining=$(echo "$remaining" | sed "s/\b$pr\b//g")
        found_ready=true
        break
      fi
    done

    # If no PR is ready, break (circular dependency or error)
    if [ "$found_ready" = false ]; then
      echo "Error: Circular dependency or missing dependency" >&2
      # Add remaining PRs anyway
      ordered="$ordered $remaining"
      break
    fi
  done

  echo "$ordered" | xargs
}

# Analyze all conflicts and generate report
# Usage: analyze_conflicts PR_NUMBERS
analyze_conflicts() {
  local prs="$1"

  echo "=== Conflict Analysis ===" >&2
  echo "" >&2

  local conflict_count=0
  local conflict_matrix=$(build_conflict_matrix "$prs")

  for pr in $prs; do
    local conflicts=$(echo "$conflict_matrix" | grep "^${pr}:" | cut -d: -f2)

    if [ -n "$conflicts" ]; then
      ((conflict_count++))
      echo "PR #$pr will conflict with: $conflicts" >&2
    else
      echo "PR #$pr: no conflicts" >&2
    fi
  done

  echo "" >&2
  echo "Total PRs with conflicts: $conflict_count" >&2

  # Return conflict matrix
  echo "$conflict_matrix"
}

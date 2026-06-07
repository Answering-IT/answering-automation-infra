Your task is to create a pull request from the worktree branch in the .trees/$ARGUMENTS folder. Follow these steps:

1. Check if the .trees/$ARGUMENTS worktree exists. If it doesn't, stop here and tell the user the worktree doesn't exist.

2. Change into the .trees/$ARGUMENTS directory

3. Verify that exactly one commit was made:
   - Run `git log main..HEAD --oneline` to see commits
   - If there are 0 commits, stop and tell the user no changes were made
   - If there are multiple commits, stop and tell the user to squash commits first

4. Verify the commit message follows the pattern `feat(issue-N):` or `fix(issue-N):`:
   - Extract the commit message with `git log -1 --pretty=%B`
   - Check it matches the pattern (where N is an issue number)
   - If not, stop and tell the user to fix the commit message

5. Push the branch to remote:
   - Run `git push origin HEAD` (HEAD refers to the current branch)
   - If push fails, stop and report the error

6. Create the pull request:
   - Extract the issue number from the branch name (auto/issue-N format)
   - Use `gh pr create` with:
     - Title: the commit message subject line
     - Body: "Closes #N" (where N is the issue number)
     - Base: main
     - Head: current branch
   - Example: `gh pr create --title "feat(issue-27): add monitoring" --body "Closes #27" --base main --head auto/issue-27`

7. Report the PR number and URL to the user

8. Change back to the root directory

9. Keep the worktree (DO NOT remove it) so the user can make fixes if needed

**Important notes:**
- The worktree name should match pattern: auto-{issue_id}
- The branch name should match pattern: auto/issue-{issue_id}
- The commit message should match pattern: feat(issue-{n}): description
- Always include "Closes #N" in the PR body to auto-link the issue
- The worktree persists after PR creation for potential fixes

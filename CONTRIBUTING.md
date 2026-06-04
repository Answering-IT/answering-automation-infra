# Contributing

This repo provides shared workflows and templates for the entire organization.
Changes here impact multiple repos, so follow these guidelines.

---

## Making Changes

### 1. Branch Strategy

- `main` is protected
- Branch naming:
  - `feat/<name>` - New workflow or template
  - `fix/<name>` - Bug fix
  - `docs/<name>` - Documentation only

### 2. Testing Changes

**Before opening a PR:**

1. **Test in a consumer repo first** (use kb-rag-agent as test bed):
   ```bash
   # In kb-rag-agent, update caller workflow to use your branch
   uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@your-branch
   
   # Run workflow
   gh workflow run AutoMaintain.yml
   
   # Verify it works end-to-end
   ```

2. **Validate parser changes:**
   ```bash
   # If you modified scripts/parse_backlog.py
   python scripts/parse_backlog.py --validate
   python scripts/parse_backlog.py --next
   ```

3. **Check all templates:**
   ```bash
   # Ensure templates are still valid
   cd templates/python && ruff check . || echo "Expected (no actual code)"
   cd ../typescript && npm install && npm run lint || echo "Expected"
   ```

### 3. Versioning

**Semantic versioning:**
- `v1.x.x` - Backward-compatible changes (bug fixes, new features that don't break existing)
- `v2.x.x` - Breaking changes (API changes, removed features)

**When to bump:**
- Workflow changes → bump version
- Parser changes → bump version
- Template changes → don't bump (templates are point-in-time)
- Documentation only → don't bump

**How to tag:**
```bash
git tag v1.1.0
git push --tags
```

### 4. PR Requirements

**Title format:**
- `feat: add Go template support`
- `fix: parser handles empty notes field`
- `docs: update troubleshooting guide`

**PR description must include:**
- What changed
- Why (what problem does it solve)
- Testing done (which consumer repo you tested in)
- Breaking change? (yes/no)
- If breaking: migration guide for consumer repos

**Example:**
```markdown
## What
Add support for Go projects with golangci-lint gates.

## Why
Several repos in the org use Go and want auto-maintain.

## Testing
- Created templates/go/ with .golangci.yml and BACKLOG.md
- Created .github/workflows/build-go-reusable.yml
- Tested in test-go-service repo (branch: test-auto-maintain)
- Workflow ran successfully, opened PR, gates passed

## Breaking Change?
No. Existing Python/TypeScript repos unaffected.

## Migration Guide
N/A
```

---

## Rollout Process

When merging changes that affect consumer repos:

### Phase 1: Pilot (1-2 repos)
```bash
# Merge to main
git checkout main
git pull

# Tag
git tag v1.1.0
git push --tags

# Test in 1-2 pilot repos
# Update their caller workflow: @v1.0.0 → @v1.1.0
# Trigger workflow, verify success
```

### Phase 2: Expand
```bash
# If pilots succeed, roll out to more repos
# Open PRs in each repo bumping version tag
# Or: script it (future enhancement)
```

### Phase 3: Announce
```bash
# Post in Slack #engineering
# Update CHANGELOG.md in this repo
# Update README.md if user-facing behavior changed
```

---

## What Needs Review

**Changes requiring extra scrutiny:**

1. **Workflow changes** - Impact all consumer repos
   - Reviewer: Platform team lead
   - Test: Run in 2+ consumer repos

2. **Parser changes** - Could break all workflows
   - Reviewer: Original parser author
   - Test: Run against all known BACKLOG.md files

3. **IAM/AWS changes** - Security implications
   - Reviewer: Security team
   - Test: Verify least-privilege principle

4. **Template changes** - New repos will use them
   - Reviewer: Stack expert (Python/TS/Go)
   - Test: Create a new repo from template, verify gates pass

---

## Adding a New Stack

To add support for a new language (e.g., Rust):

### 1. Create template directory
```bash
mkdir templates/rust
cd templates/rust
```

### 2. Add config files
- Linter/formatter config (e.g., `rustfmt.toml`, `clippy.toml`)
- `BACKLOG.md` (copy from another template, adjust)
- Any other standard files (e.g., `Cargo.toml` starter)

### 3. Create reusable workflow
```bash
# .github/workflows/build-rust-reusable.yml
# Should have jobs: lint, build, test
```

### 4. Update auto-maintain-reusable.yml
Add rust to the language-specific gate commands:
```python
gates = {
    "python": [...],
    "typescript": [...],
    "go": [...],
    "rust": ["cargo fmt --check", "cargo clippy", "cargo test"]  # Add this
}
```

### 5. Document
- Update README.md "Supported Stacks" table
- Update ONBOARDING.md with rust-specific steps
- Add troubleshooting entries if needed

### 6. Test
- Create a test repo with the new template
- Run auto-maintain workflow
- Verify gates pass

---

## Documentation Standards

When updating docs:

1. **Keep it concise** - No fluff, just facts
2. **Include examples** - Show, don't just tell
3. **Update dates** - "Last Updated: YYYY-MM-DD" at bottom
4. **Cross-reference** - Link to related docs
5. **Test commands** - All bash commands should actually work

---

## Support

Questions?
- Open a discussion in this repo
- Ping @platform-team in Slack

---

**Last Updated:** 2026-06-04

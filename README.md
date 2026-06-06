# Answering Automation Infrastructure

Central repository for self-maintaining workflows across Answering-IT repos.

## What this provides

Reusable GitHub Actions workflows so any repo can:

- Consume work items from GitHub Issues (created by documentation workflow) or `BACKLOG.md` files
- Trigger Claude Code (via AWS Bedrock) to implement items end-to-end
- Open PRs that go through the same quality gates as human-authored code

**Key principle:** Write the workflow once, version it, consumers reference it by tag.

**Two modes:**
- **GitHub Issues mode** (recommended): Issues are created by the central documentation repo, grouped by milestone, automatically formatted
- **BACKLOG.md mode** (legacy): Manual maintenance of BACKLOG.md in each consumer repo

---

## Repo layout

```
.github/workflows/
├── auto-maintain-reusable.yml      # Picks work item → invokes Claude → opens PR
└── build-python-reusable.yml       # Python lint/test gates (ruff, black, pytest)

scripts/
├── parse_backlog.py                # Parses BACKLOG.md (validates, picks --next)
└── parse_github_issues.py          # Queries GitHub Issues (validates, picks --next)

templates/
└── python/                         # Starter pack: pyproject.toml, BACKLOG.md, etc.

docs/
├── ONBOARDING.md                   # Add auto-maintain to a new repo
├── BACKLOG_FORMAT.md               # Schema for backlog items (BACKLOG.md mode)
├── github-issues-integration.md    # GitHub Issues mode (recommended)
└── TROUBLESHOOTING.md              # Common failures and fixes
```

---

## Quick start (for a new consumer repo)

1. Read [`docs/ONBOARDING.md`](docs/ONBOARDING.md) — full step-by-step including manual GitHub config.
2. Copy `templates/python/*` to your repo.
3. Add `.github/workflows/AutoMaintain.yml` and `.github/workflows/Build.yml` (slim callers — see ONBOARDING).
4. Configure repository secrets `AUTO_MAINTAIN_APP_ID` and `AUTO_MAINTAIN_APP_PRIVATE_KEY` (see ONBOARDING for exact values).
5. Trigger `Auto Maintain` from the Actions tab.

---

## Versioning

| Tag      | What it points to                                                |
|----------|------------------------------------------------------------------|
| `v1.0.4` | Latest stable (current)                                          |
| `v1`     | Floating tag — always points to the latest `v1.x.x`              |

Consumers should pin to a specific minor (`@v1.0.4`) and bump deliberately. The `@v1` floating tag exists for prototyping only.

### Release process

```bash
# After merging changes to main:
git tag -a vX.Y.Z -m "vX.Y.Z: <one-liner>"
git tag -d v1                              # delete old floating
git tag -a v1 -m "v1: latest stable v1.x"
git push origin vX.Y.Z
git push origin v1 --force
```

Then bump consumer repos: edit their `AutoMaintain.yml` and `Build.yml` to reference the new tag.

---

## Important: this is NOT a GitHub Organization

`Answering-IT` is a **User account**, not an Organization. This means:

- ❌ No organization-level secrets (the `/organizations/Answering-IT/settings/...` URLs do not exist)
- ❌ No organization-level `gh` CLI commands work
- ✅ Each consumer repo must have its own copies of `AUTO_MAINTAIN_APP_ID` and `AUTO_MAINTAIN_APP_PRIVATE_KEY` as **repository secrets**

Onboarding a new repo therefore requires setting two secrets per repo. See `docs/ONBOARDING.md` for the exact commands.

If you ever convert `Answering-IT` to an Organization, you can move these to org-level secrets and remove the per-repo duplication. Until then, keep using repo-level secrets.

---

## Current status

| Repo                                | Status     | Notes                                  |
|-------------------------------------|------------|----------------------------------------|
| `external-ingester-consumer-lambda` | ✅ Live    | Pilot — first PR opened by Claude #19  |
| `kb-rag-agent`                      | 🚧 Migrating | Moving from inline workflow to reusable |
| Other Python repos                  | 📋 Planned | After kb-rag-agent stabilizes          |

---

## Architecture decisions worth knowing

**Why GitHub App (not `GITHUB_TOKEN`) for opening PRs?**
PRs opened with the default `GITHUB_TOKEN` do not trigger downstream workflows like `Build.yml`. Using a GitHub App identity dispatches them normally, so the same gates a human PR would face apply to Claude's PR.

**Why reusable workflows (not a custom action)?**
Reusable workflows can declare `secrets:` and full `permissions:` blocks, which custom actions can't. They also live as YAML, which is easier to diff than a packaged action.

**Why download `parse_backlog.py` per run instead of vendoring it?**
Consumers stay zero-maintenance: parser fixes take effect on the next run without any consumer-side bump. The download URL is pinned to `main` of this repo (intentional — pinning to a tag was the source of the v1.0.0→v1.0.1 bug).

**Why pytest exit code 5 = success?**
Projects adopting the workflow shouldn't need to backfill `@pytest.mark.unit`/`smoke` across their existing suite before they can use the gate. Exit code 5 means "no tests collected" — we treat that as a clean pass with a notice. Exit code 2 (real collection error) still fails the build.

---

## Documentation

- [`docs/ONBOARDING.md`](docs/ONBOARDING.md) — Add auto-maintain to a new repo, with all manual GitHub steps
- [`docs/BACKLOG_FORMAT.md`](docs/BACKLOG_FORMAT.md) — Schema for `BACKLOG.md` items
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) — Common failures and fixes
- [`CHANGELOG.md`](CHANGELOG.md) — Version history

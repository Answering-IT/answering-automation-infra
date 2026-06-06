# Changelog

All notable changes to the reusable workflows and parser. Consumer repos pin to a specific version, so every change here is potentially a coordinated bump across the organization.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.4] - 2026-06-04

### Fixed
- `build-python-reusable.yml`: pytest exit code 5 (no tests collected) now treated as success with a notice instead of a failure. Lets projects adopt the gate without needing to backfill `@pytest.mark.unit`/`smoke` across an existing test suite. Real collection errors (exit 2) still fail the build correctly.

---

## [1.0.3] - 2026-06-04

### Added
- `build-python-reusable.yml`: auto-installs `infrastructure/lambdas/*/requirements.txt` to support CDK Lambda projects whose runtime deps live under that path.

### Changed
- `build-python-reusable.yml`: pytest skip logic switched from a `--collect-only | grep` heuristic to checking the actual exit code (will be finalized in 1.0.4).

---

## [1.0.2] - 2026-06-04

### Fixed
- `auto-maintain-reusable.yml`: parser download URL changed from a hardcoded `v1.0.0` tag to `main`. Earlier versions downloaded the buggy parser even when the consumer's caller was on a newer tag, because the URL inside the workflow was version-pinned.

---

## [1.0.1] - 2026-06-04

### Fixed
- `parse_backlog.py`: `DEFAULT_BACKLOG` changed from `Path(__file__).parents[1] / "BACKLOG.md"` to `Path("BACKLOG.md")`. The old approach resolved to the wrong directory when the parser was downloaded into a consumer repo (`/home/runner/work/<repo>/BACKLOG.md` instead of `/home/runner/work/<repo>/<repo>/BACKLOG.md`).

---

## [1.0.0] - 2026-06-04

### Added
- `auto-maintain-reusable.yml` — picks next backlog item, builds prompt, invokes Claude via Bedrock, opens a PR. Concurrency-controlled per consumer repo. Validates caller is in `Answering-IT`.
- `build-python-reusable.yml` — Python lint (ruff), format (black), tests (pytest with `unit or smoke` markers).
- `scripts/parse_backlog.py` — parses fenced YAML blocks tagged `yaml backlog`. Modes: `--validate`, `--next`, `--list`.
- `templates/python/` — starter pyproject.toml, requirements-dev.txt, .python-version, BACKLOG.md.

### Architecture decisions
- Uses GitHub App (App ID stored as repo secret) for PR creation, not `GITHUB_TOKEN`. Required because `GITHUB_TOKEN`-opened PRs do not dispatch downstream workflows like `Build.yml`.
- AWS auth via OIDC to a shared IAM role (`GitHubActions-Answering-IT-SharedRole`), not long-lived keys.
- Cross-region inference profile `us.anthropic.claude-sonnet-4-6`, region `us-east-1`.
- `workflow_dispatch` only — no `schedule:` until the pipeline has been validated in production.

### Known constraint
- `Answering-IT` is a User account, not an Organization. Org-level secrets/settings don't apply. Each consumer repo must have `AUTO_MAINTAIN_APP_ID` and `AUTO_MAINTAIN_APP_PRIVATE_KEY` as repository secrets. Documented in `README.md`.

---

## Versioning policy

| Bump  | Meaning                                                                          | Action required                                                                |
|-------|----------------------------------------------------------------------------------|--------------------------------------------------------------------------------|
| Patch | Bug fix, doc-only, no behavior change for callers using documented features      | Optional — bump when convenient                                                |
| Minor | Backward-compatible additions (new optional inputs, new tools allowed)           | Recommended — bump to pick up new capabilities                                 |
| Major | Removed input, changed default that might affect callers, dependency change      | Required — coordinate across all consumers, with migration notes in this file  |

The `@v1` floating tag tracks the latest `v1.x.x`. **Don't use it in production** — pinning to a specific patch version makes upgrades deliberate and audit-friendly.

### Release process

```bash
# After PR merged to main:
git pull origin main
git tag -a v1.0.X -m "v1.0.X: <one-liner>"
git tag -d v1
git tag -a v1 -m "v1: latest stable v1.x"
git push origin v1.0.X
git push origin v1 --force
```

Then update consumer repos by editing the `@v1.0.X` reference in their `AutoMaintain.yml` and `Build.yml`.

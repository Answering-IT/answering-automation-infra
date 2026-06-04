# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added
- Initial setup of answering-automation-infra repository
- Reusable workflows for auto-maintain pipeline
- Templates for Python, TypeScript, and Go projects
- Comprehensive documentation (onboarding, troubleshooting, format spec)
- Shared parser script (parse_backlog.py)

---

## [1.0.0] - 2026-06-04

### Added
- **Reusable Workflows:**
  - `auto-maintain-reusable.yml` - Core auto-implement workflow
  - `build-python-reusable.yml` - Python quality gates (ruff, black, pytest)
  - `build-typescript-reusable.yml` - TypeScript gates (eslint, prettier, vitest)
  - `build-go-reusable.yml` - Go gates (golangci-lint, go test)

- **Templates:**
  - `templates/python/` - pyproject.toml, requirements-dev.txt, .python-version, BACKLOG.md
  - `templates/typescript/` - package.json, tsconfig.json, eslint/prettier config, BACKLOG.md
  - `templates/go/` - .golangci.yml, BACKLOG.md

- **Scripts:**
  - `scripts/parse_backlog.py` - BACKLOG.md parser with --validate, --next, --list modes

- **Documentation:**
  - `README.md` - Overview and quick start
  - `docs/ONBOARDING.md` - Step-by-step guide for adding auto-maintain to a repo
  - `docs/TROUBLESHOOTING.md` - Common issues and solutions
  - `docs/BACKLOG_FORMAT.md` - YAML schema specification
  - `CONTRIBUTING.md` - Guidelines for maintaining this repo

### Technical Details
- Uses GitHub App authentication (App ID: 3964884) for PR creation
- AWS Bedrock OIDC integration with shared IAM role
- Cross-region inference profile: `us.anthropic.claude-sonnet-4-6`
- Supports workflow_dispatch with backlog_id override and dry_run mode
- Concurrency control per repository to prevent duplicate PRs

### Prerequisites
- GitHub App `answering-auto-maintain` installed org-wide
- AWS IAM role `GitHubActions-Answering-IT-SharedRole` with wildcard trust policy
- Org setting enabled: "Allow GitHub Actions to create and approve pull requests"

---

## Versioning Strategy

- **Major (v2.x.x):** Breaking changes requiring consumer repo updates
- **Minor (v1.x.x):** New features, backward-compatible improvements
- **Patch (v1.0.x):** Bug fixes, documentation updates

Consumer repos pin to specific versions:
```yaml
uses: Answering-IT/answering-automation-infra/.github/workflows/auto-maintain-reusable.yml@v1.0.0
```

---

**Legend:**
- `Added` - New features
- `Changed` - Changes to existing functionality
- `Deprecated` - Soon-to-be removed features
- `Removed` - Removed features
- `Fixed` - Bug fixes
- `Security` - Vulnerability fixes

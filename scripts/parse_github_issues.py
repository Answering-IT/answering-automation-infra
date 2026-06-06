#!/usr/bin/env python3
"""
Parse GitHub Issues (created by documentation workflow) for the auto-maintain workflow.

Replaces parse_backlog.py by querying issues in the consumer repo instead of reading BACKLOG.md.

Modes:
  --validate    Validate every issue. Exit non-zero on invalid issues.
  --next        Print the next eligible issue as JSON and exit 0.
                If nothing is eligible, exit 0 with `null`.
  --list        Print all parsed issues as JSON.

Issue discovery:
  - Queries issues in the current repository (via GITHUB_REPOSITORY env var)
  - Filters by milestone (if --milestone provided) or by label (if --label provided)
  - Parses issue body metadata: Target repo, Effort, Priority, Dependencies
  - Maps to BacklogItem structure expected by the workflow
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field

# Priority mapping: Issue priority → Backlog priority
PRIORITY_MAP = {
    "critical": "P0",
    "high": "P0",
    "medium": "P1",
    "low": "P2",
}

PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


@dataclass
class BacklogItem:
    """Structure expected by auto-maintain workflow"""

    id: str
    title: str
    status: str
    priority: str
    context: str
    acceptance_criteria: list[str]
    labels: list[str] = field(default_factory=list)
    files_to_touch: list[str] = field(default_factory=list)
    tests_required: list[str] = field(default_factory=list)
    notes: str = ""
    # Extra fields for GitHub Issues mode
    issue_number: int = 0
    issue_url: str = ""
    github_issue_ref: str = ""  # e.g., "#123" for linking in PR body


@dataclass
class ValidationError:
    issue_number: int
    title: str
    message: str


def gh(args: list[str], check: bool = True) -> str:
    """Run gh CLI command and return stdout"""
    cmd = ["gh"] + args
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=check, timeout=60)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"gh command failed: {' '.join(cmd[:6])}...", file=sys.stderr)
        print(f"  stderr: {e.stderr[:500]}", file=sys.stderr)
        if check:
            raise
        return ""
    except subprocess.TimeoutExpired:
        print(f"gh command timed out: {' '.join(cmd[:6])}...", file=sys.stderr)
        raise


def query_issues(
    repo: str,
    milestone: str | None = None,
    label: str | None = None,
) -> list[dict]:
    """Query open issues from GitHub"""
    args = [
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "open",
        "--json",
        "number,title,body,labels,milestone,url",
        "--limit",
        "500",
    ]

    if milestone:
        args.extend(["--milestone", milestone])

    if label:
        args.extend(["--label", label])

    output = gh(args, check=True)
    if not output:
        return []

    return json.loads(output)


def parse_issue_metadata(body: str) -> dict:
    """Extract metadata from issue body.

    Expected format:
    ---
    **Target repo:** `Answering-IT/kb-rag-agent-fe`
    **Effort:** medium | **Priority:** high
    **Dependencies:** issue title 1, issue title 2
    """
    metadata = {
        "target_repo": "",
        "effort": "medium",
        "priority": "medium",
        "dependencies": [],
    }

    # Target repo
    target_match = re.search(r"\*\*Target repo:\*\*\s*`([^`]+)`", body)
    if target_match:
        metadata["target_repo"] = target_match.group(1)

    # Effort and Priority (on same line)
    effort_prio_match = re.search(r"\*\*Effort:\*\*\s*(\w+)\s*\|\s*\*\*Priority:\*\*\s*(\w+)", body)
    if effort_prio_match:
        metadata["effort"] = effort_prio_match.group(1).lower()
        metadata["priority"] = effort_prio_match.group(2).lower()

    # Dependencies
    deps_match = re.search(r"\*\*Dependencies:\*\*\s*([^\n]+)", body)
    if deps_match:
        deps_str = deps_match.group(1).strip()
        if deps_str and deps_str.lower() != "none":
            metadata["dependencies"] = [d.strip() for d in deps_str.split(",") if d.strip()]

    return metadata


def extract_acceptance_criteria(body: str) -> list[str]:
    """Extract acceptance criteria from issue body.

    Looks for sections like:
    ## Acceptance Criteria
    - [ ] item 1
    - [ ] item 2
    """
    criteria = []

    # Find acceptance criteria section
    ac_match = re.search(
        r"##\s+Acceptance Criteria\s*\n(.*?)(?=\n##|\n---|\Z)",
        body,
        re.DOTALL | re.IGNORECASE,
    )

    if ac_match:
        section = ac_match.group(1)
        # Extract list items
        for line in section.split("\n"):
            line = line.strip()
            # Match checkbox items or bullet points
            item_match = re.match(r"^[-*]\s*\[[ x]\]\s*(.+)$", line)
            if item_match:
                criteria.append(item_match.group(1).strip())
            elif line.startswith("- ") or line.startswith("* "):
                criteria.append(line[2:].strip())

    return criteria


def issue_to_backlog_item(
    issue: dict,
    target_repo: str,
) -> tuple[BacklogItem | None, ValidationError | None]:
    """Convert GitHub issue to BacklogItem.

    Returns (item, error). One will be None.
    """
    number = issue["number"]
    title = issue["title"]
    body = issue.get("body", "")
    url = issue.get("url", "")

    # Parse metadata
    metadata = parse_issue_metadata(body)

    # Validate target repo matches (if present)
    # If target_repo is not set, assume the issue belongs to the current repo (legacy issues)
    if metadata["target_repo"] and metadata["target_repo"] != target_repo:
        return None, ValidationError(
            number,
            title,
            f"Target repo mismatch: expected {target_repo}, got {metadata['target_repo']}",
        )

    # Extract acceptance criteria
    criteria = extract_acceptance_criteria(body)
    if not criteria:
        return None, ValidationError(number, title, "No acceptance criteria found in issue body")

    # Map priority
    priority = PRIORITY_MAP.get(metadata["priority"], "P1")

    # Extract labels
    label_names = [lbl["name"] for lbl in issue.get("labels", [])]

    # Generate id from issue number and title
    item_id = f"issue-{number}-{title[:30].lower().replace(' ', '-').replace('/', '-')}"
    item_id = re.sub(r"[^a-z0-9-]", "", item_id)

    # Extract context (first paragraph of body, before metadata)
    context_match = re.match(r"^(.*?)(?=\n##|\n---|\Z)", body, re.DOTALL)
    context = context_match.group(1).strip() if context_match else title

    # Build item
    item = BacklogItem(
        id=item_id,
        title=title,
        status="ready",  # All open issues are considered ready
        priority=priority,
        context=context,
        acceptance_criteria=criteria,
        labels=label_names,
        files_to_touch=[],  # Issues don't have this metadata yet
        tests_required=[],  # Issues don't have this metadata yet
        notes=f"Generated from GitHub issue #{number}",
        issue_number=number,
        issue_url=url,
        github_issue_ref=f"#{number}",
    )

    return item, None


def parse(
    repo: str,
    milestone: str | None = None,
    label: str | None = None,
) -> tuple[list[BacklogItem], list[ValidationError]]:
    """Query issues and parse them. Returns (items, errors)."""
    issues = query_issues(repo, milestone, label)

    items: list[BacklogItem] = []
    errors: list[ValidationError] = []

    for issue in issues:
        item, error = issue_to_backlog_item(issue, repo)
        if item:
            items.append(item)
        elif error:
            errors.append(error)

    return items, errors


def select_next(items: list[BacklogItem]) -> BacklogItem | None:
    """Pick the next eligible item.

    Rules: status == 'ready', sorted by priority (P0 > P1 > P2), then issue number.
    """
    eligible = [item for item in items if item.status == "ready"]
    if not eligible:
        return None

    # Sort by priority first, then by issue number (lower = older = higher priority)
    eligible.sort(key=lambda i: (PRIORITY_ORDER[i.priority], i.issue_number))
    return eligible[0]


def _print_errors(errors: list[ValidationError]) -> None:
    for err in errors:
        print(f"  - #{err.issue_number} ({err.title}): {err.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--repo",
        help="Target repository (e.g., Answering-IT/kb-rag-agent-fe). " "Defaults to GITHUB_REPOSITORY env var.",
    )
    parser.add_argument("--milestone", help="Filter by milestone title")
    parser.add_argument("--label", help="Filter by label (e.g., 'feature', 'bug')")

    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true", help="Validate issues")
    mode.add_argument("--next", dest="next_", action="store_true", help="Print next eligible issue")
    mode.add_argument("--list", dest="list_", action="store_true", help="Print all valid issues")

    args = parser.parse_args(argv)

    # Determine target repo
    repo = args.repo or os.environ.get("GITHUB_REPOSITORY")
    if not repo:
        print("ERROR: --repo or GITHUB_REPOSITORY env var required", file=sys.stderr)
        return 2

    try:
        items, errors = parse(repo, args.milestone, args.label)
    except subprocess.CalledProcessError:
        return 2

    if errors:
        print(f"Found {len(errors)} validation error(s):", file=sys.stderr)
        _print_errors(errors)
        if args.validate:
            return 1
        # For --next / --list, errors are warnings — proceed with valid items.

    if args.validate:
        print(f"OK: {len(items)} issue(s) valid", file=sys.stderr)
        return 0

    if args.next_:
        item = select_next(items)
        # Keep github_issue_ref for PR linking, remove internal tracking fields
        if item:
            item_dict = asdict(item)
            del item_dict["issue_number"]
            del item_dict["issue_url"]
            # github_issue_ref is kept for PR description
            print(json.dumps(item_dict, indent=2, ensure_ascii=False))
        else:
            print("null")
        return 0

    if args.list_:
        items_dicts = []
        for item in items:
            item_dict = asdict(item)
            del item_dict["issue_number"]
            del item_dict["issue_url"]
            # github_issue_ref is kept for PR linking
            items_dicts.append(item_dict)
        print(json.dumps(items_dicts, indent=2, ensure_ascii=False))
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())

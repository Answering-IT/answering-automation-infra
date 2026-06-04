#!/usr/bin/env python3
"""
Parse `BACKLOG.md` for the auto-maintain workflow (Fase 4).

Modes:
  --validate    Validate every item. Exit non-zero on invalid items.
  --next        Print the next eligible item as JSON and exit 0.
                If nothing is eligible, exit 0 with `null`.
  --list        Print all parsed items as JSON.

Format spec: docs/backlog-format.md
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

# When run from the repo root (most common case, including CI)
DEFAULT_BACKLOG = Path("BACKLOG.md")

VALID_STATUSES = {"ready", "blocked", "in_progress", "done"}
VALID_PRIORITIES = {"P0", "P1", "P2"}
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}
REQUIRED_FIELDS = {"id", "title", "status", "priority", "context", "acceptance_criteria"}

# Match fenced blocks tagged exactly `yaml backlog`. Other code blocks are ignored.
_BLOCK_RE = re.compile(r"^```yaml backlog\s*\n(.*?)^```", re.MULTILINE | re.DOTALL)


@dataclass
class BacklogItem:
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


@dataclass
class ValidationError:
    item_index: int  # 0-based, in document order
    item_id: str | None
    message: str


def parse(text: str) -> tuple[list[BacklogItem], list[ValidationError]]:
    """Parse backlog text. Returns (items, errors). Always returns both."""
    items: list[BacklogItem] = []
    errors: list[ValidationError] = []

    for index, match in enumerate(_BLOCK_RE.finditer(text)):
        raw = match.group(1)
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            errors.append(ValidationError(index, None, f"YAML parse error: {exc}"))
            continue

        if not isinstance(data, dict):
            errors.append(ValidationError(index, None, "Item is not a YAML mapping"))
            continue

        item_id = data.get("id")
        missing = REQUIRED_FIELDS - data.keys()
        if missing:
            errors.append(ValidationError(index, item_id, f"Missing required fields: {sorted(missing)}"))
            continue

        if data["status"] not in VALID_STATUSES:
            errors.append(
                ValidationError(
                    index, item_id, f"Invalid status {data['status']!r}; must be one of {sorted(VALID_STATUSES)}"
                )
            )
            continue

        if data["priority"] not in VALID_PRIORITIES:
            errors.append(
                ValidationError(
                    index, item_id, f"Invalid priority {data['priority']!r}; must be one of {sorted(VALID_PRIORITIES)}"
                )
            )
            continue

        if not isinstance(data["acceptance_criteria"], list) or not data["acceptance_criteria"]:
            errors.append(ValidationError(index, item_id, "acceptance_criteria must be a non-empty list"))
            continue

        try:
            item = BacklogItem(
                id=str(data["id"]),
                title=str(data["title"]),
                status=str(data["status"]),
                priority=str(data["priority"]),
                context=str(data["context"]).strip(),
                acceptance_criteria=[str(c) for c in data["acceptance_criteria"]],
                labels=[str(label) for label in data.get("labels", [])],
                files_to_touch=[str(p) for p in data.get("files_to_touch", [])],
                tests_required=[str(t) for t in data.get("tests_required", [])],
                notes=str(data.get("notes", "")).strip(),
            )
        except (TypeError, ValueError) as exc:
            errors.append(ValidationError(index, item_id, f"Failed to coerce fields: {exc}"))
            continue

        items.append(item)

    # Duplicate id check (only run if we have valid items)
    seen: dict[str, int] = {}
    for index, item in enumerate(items):
        if item.id in seen:
            errors.append(ValidationError(index, item.id, f"Duplicate id (also at item index {seen[item.id]})"))
        else:
            seen[item.id] = index

    return items, errors


def select_next(items: list[BacklogItem]) -> BacklogItem | None:
    """Pick the next eligible item.

    Rules: status == 'ready', sorted by priority (P0 > P1 > P2), then document order.
    """
    eligible = [item for item in items if item.status == "ready"]
    if not eligible:
        return None

    # Stable sort: items keep document order within the same priority bucket.
    eligible.sort(key=lambda i: PRIORITY_ORDER[i.priority])
    return eligible[0]


def _read_text(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"Backlog file not found: {path}")
    return path.read_text(encoding="utf-8")


def _print_errors(errors: list[ValidationError]) -> None:
    for err in errors:
        ident = err.item_id or f"<item index {err.item_index}>"
        print(f"  - {ident}: {err.message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--file", type=Path, default=DEFAULT_BACKLOG, help="Path to BACKLOG.md")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--validate", action="store_true", help="Validate items; exit non-zero on errors")
    mode.add_argument("--next", dest="next_", action="store_true", help="Print next eligible item as JSON")
    mode.add_argument("--list", dest="list_", action="store_true", help="Print all valid items as JSON")
    args = parser.parse_args(argv)

    try:
        text = _read_text(args.file)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    items, errors = parse(text)

    if errors:
        print(f"Found {len(errors)} validation error(s):", file=sys.stderr)
        _print_errors(errors)
        if args.validate:
            return 1
        # For --next / --list, errors are warnings — proceed with valid items.

    if args.validate:
        print(f"OK: {len(items)} item(s) valid")
        return 0

    if args.next_:
        item = select_next(items)
        print(json.dumps(asdict(item) if item else None, indent=2, ensure_ascii=False))
        return 0

    if args.list_:
        print(json.dumps([asdict(i) for i in items], indent=2, ensure_ascii=False))
        return 0

    return 0  # unreachable


if __name__ == "__main__":
    sys.exit(main())

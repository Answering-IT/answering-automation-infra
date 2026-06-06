import importlib.util
import pathlib

import pytest


@pytest.mark.smoke
def test_parse_github_issues_importable():
    spec = importlib.util.spec_from_file_location(
        "parse_github_issues",
        pathlib.Path(__file__).parent.parent / "scripts" / "parse_github_issues.py",
    )
    assert spec is not None


@pytest.mark.smoke
def test_parse_backlog_importable():
    spec = importlib.util.spec_from_file_location(
        "parse_backlog",
        pathlib.Path(__file__).parent.parent / "scripts" / "parse_backlog.py",
    )
    assert spec is not None

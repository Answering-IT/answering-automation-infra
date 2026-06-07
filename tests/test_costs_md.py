import os
import subprocess
import sys
import tempfile
import textwrap

import pytest

# The embedded Python script from the "Append COSTS.md entry" workflow step.
SCRIPT = textwrap.dedent("""\
    import os
    import datetime

    def fmt_int(val):
        try:
            return f"{int(val):,}"
        except Exception:
            return "0"

    input_tokens = fmt_int(os.environ.get("INPUT_TOKENS", "0"))
    output_tokens = fmt_int(os.environ.get("OUTPUT_TOKENS", "0"))
    cost = os.environ.get("COST", "$0.000")
    duration = os.environ.get("DURATION", "N/A")
    pr_number = os.environ.get("PR_NUMBER", "").strip()
    item_title = os.environ.get("ITEM_TITLE", "unknown")
    item_id = os.environ.get("ITEM_ID", "unknown")
    model = os.environ.get("MODEL", "unknown")
    job_status = os.environ.get("JOB_STATUS", "unknown")
    server_url = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo = os.environ.get("GITHUB_REPOSITORY", "")

    if pr_number:
        pr_link = f"[#{pr_number}]({server_url}/{repo}/pull/{pr_number})"
    else:
        pr_link = "N/A"

    date_str = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    entry_lines = [
        f"## {date_str} — {item_id} (auto)",
        "",
        f"| Field | Value |",
        f"|-------|-------|",
        f"| Title | {item_title} |",
        f"| Model | {model} |",
        f"| Input tokens | {input_tokens} |",
        f"| Output tokens | {output_tokens} |",
        f"| Cost | {cost} |",
        f"| Duration | {duration} |",
        f"| Status | {job_status} |",
        f"| PR | {pr_link} |",
        "",
    ]
    entry = "\\n".join(entry_lines)

    costs_path = os.environ.get("COSTS_PATH", "COSTS.md")
    header = "# Claude Session Costs\\n\\n"

    if not os.path.exists(costs_path):
        with open(costs_path, "w") as fh:
            fh.write(header)

    with open(costs_path, "a") as fh:
        fh.write(entry + "\\n")

    print(f"Appended cost entry to {costs_path}")
""")


def run_script(env_overrides: dict, costs_path: str) -> str:
    env = {
        "INPUT_TOKENS": "1000",
        "OUTPUT_TOKENS": "500",
        "COST": "$0.018",
        "DURATION": "1m 30s",
        "PR_NUMBER": "42",
        "ITEM_TITLE": "Test feature",
        "ITEM_ID": "issue-1-test",
        "MODEL": "us.anthropic.claude-sonnet-4-6",
        "JOB_STATUS": "success",
        "GITHUB_SERVER_URL": "https://github.com",
        "GITHUB_REPOSITORY": "Answering-IT/test-repo",
        "COSTS_PATH": costs_path,
    }
    env.update(env_overrides)
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    with open(costs_path) as fh:
        return fh.read()


@pytest.mark.unit
def test_costs_md_creates_header_if_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({}, path)
        assert content.startswith("# Claude Session Costs\n")


@pytest.mark.unit
def test_costs_md_entry_contains_auto_marker():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({}, path)
        assert "(auto)" in content


@pytest.mark.unit
def test_costs_md_entry_contains_model():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({"MODEL": "us.anthropic.claude-opus-4-8"}, path)
        assert "us.anthropic.claude-opus-4-8" in content


@pytest.mark.unit
def test_costs_md_entry_tokens_comma_formatted():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({"INPUT_TOKENS": "62333", "OUTPUT_TOKENS": "12490"}, path)
        assert "62,333" in content
        assert "12,490" in content


@pytest.mark.unit
def test_costs_md_entry_pr_link_when_present():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({"PR_NUMBER": "99"}, path)
        assert "[#99](https://github.com/Answering-IT/test-repo/pull/99)" in content


@pytest.mark.unit
def test_costs_md_entry_pr_na_when_missing():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({"PR_NUMBER": ""}, path)
        assert "| PR | N/A |" in content


@pytest.mark.unit
def test_costs_md_entry_status_failure():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({"JOB_STATUS": "failure"}, path)
        assert "failure" in content


@pytest.mark.unit
def test_costs_md_appends_to_existing_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        # Write two entries
        run_script({"ITEM_ID": "issue-1-first"}, path)
        run_script({"ITEM_ID": "issue-2-second"}, path)
        with open(path) as fh:
            content = fh.read()
        assert "issue-1-first" in content
        assert "issue-2-second" in content
        assert content.count("# Claude Session Costs") == 1


@pytest.mark.unit
def test_costs_md_does_not_duplicate_header():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        with open(path, "w") as fh:
            fh.write("# Claude Session Costs\n\n")
        run_script({}, path)
        with open(path) as fh:
            content = fh.read()
        assert content.count("# Claude Session Costs") == 1


@pytest.mark.unit
def test_costs_md_item_id_in_h2():
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "COSTS.md")
        content = run_script({"ITEM_ID": "issue-22-implement-costsmd"}, path)
        assert "## " in content
        assert "issue-22-implement-costsmd" in content

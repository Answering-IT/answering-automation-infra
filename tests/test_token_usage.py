import json
import subprocess
import sys
import textwrap

import pytest

# ---------------------------------------------------------------------------
# Shared helper: runs the embedded Python snippet from the workflow step and
# returns a dict of output key=value pairs.
# ---------------------------------------------------------------------------

SCRIPT = textwrap.dedent("""\
    import json
    import os
    import re
    import sys

    raw = os.environ.get("CLAUDE_OUTPUT", "")
    input_tokens = 0
    output_tokens = 0

    try:
        data = json.loads(raw)
        usage = data.get("usage", {})
        input_tokens = max(0, int(usage.get("input_tokens", 0)))
        output_tokens = max(0, int(usage.get("output_tokens", 0)))
    except Exception:
        try:
            m = re.search(r'"input_tokens"\\s*:\\s*(\\d+)', raw)
            if m:
                input_tokens = max(0, int(m.group(1)))
            m = re.search(r'"output_tokens"\\s*:\\s*(\\d+)', raw)
            if m:
                output_tokens = max(0, int(m.group(1)))
        except Exception:
            pass

    cost_raw = (input_tokens / 1_000_000 * 3.00) + (output_tokens / 1_000_000 * 15.00)
    cost = f"${cost_raw:.3f}"

    print(f"input_tokens={input_tokens}")
    print(f"output_tokens={output_tokens}")
    print(f"cost={cost}")
    print(f"cost_raw={cost_raw}")
""")


def run_script(claude_output: str) -> dict:
    result = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        capture_output=True,
        text=True,
        env={"CLAUDE_OUTPUT": claude_output, "GITHUB_OUTPUT": "/dev/null"},
    )
    assert result.returncode == 0, result.stderr
    out = {}
    for line in result.stdout.strip().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_token_usage_json_response():
    payload = json.dumps({"usage": {"input_tokens": 1000, "output_tokens": 500}})
    out = run_script(payload)
    assert out["input_tokens"] == "1000"
    assert out["output_tokens"] == "500"


@pytest.mark.unit
def test_token_usage_cost_formula():
    payload = json.dumps({"usage": {"input_tokens": 1_000_000, "output_tokens": 1_000_000}})
    out = run_script(payload)
    assert out["cost"] == "$18.000"
    assert float(out["cost_raw"]) == pytest.approx(18.0)


@pytest.mark.unit
def test_token_usage_cost_formatting():
    payload = json.dumps({"usage": {"input_tokens": 62333, "output_tokens": 12490}})
    out = run_script(payload)
    expected = (62333 / 1_000_000 * 3.00) + (12490 / 1_000_000 * 15.00)
    assert out["cost"] == f"${expected:.3f}"
    assert float(out["cost_raw"]) == pytest.approx(expected)


@pytest.mark.unit
def test_token_usage_empty_output_defaults_to_zero():
    out = run_script("")
    assert out["input_tokens"] == "0"
    assert out["output_tokens"] == "0"
    assert out["cost"] == "$0.000"
    assert float(out["cost_raw"]) == 0.0


@pytest.mark.unit
def test_token_usage_malformed_json_falls_back_to_regex():
    raw = 'some text {"input_tokens": 200, "output_tokens": 100} more text'
    out = run_script(raw)
    assert out["input_tokens"] == "200"
    assert out["output_tokens"] == "100"


@pytest.mark.unit
def test_token_usage_non_json_no_match_defaults_to_zero():
    out = run_script("totally unrelated output")
    assert out["input_tokens"] == "0"
    assert out["output_tokens"] == "0"


@pytest.mark.unit
def test_token_usage_missing_usage_key():
    payload = json.dumps({"model": "claude-sonnet-4-6", "id": "msg_abc"})
    out = run_script(payload)
    assert out["input_tokens"] == "0"
    assert out["output_tokens"] == "0"
    assert out["cost"] == "$0.000"


@pytest.mark.unit
def test_token_usage_cost_only_input():
    payload = json.dumps({"usage": {"input_tokens": 1_000_000, "output_tokens": 0}})
    out = run_script(payload)
    assert float(out["cost_raw"]) == pytest.approx(3.00)
    assert out["cost"] == "$3.000"


@pytest.mark.unit
def test_token_usage_cost_only_output():
    payload = json.dumps({"usage": {"input_tokens": 0, "output_tokens": 1_000_000}})
    out = run_script(payload)
    assert float(out["cost_raw"]) == pytest.approx(15.00)
    assert out["cost"] == "$15.000"

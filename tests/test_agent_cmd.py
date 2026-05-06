"""Tests for af agent command (FXA-2236)."""

from __future__ import annotations

import pytest


import json
import sys
from pathlib import Path

from click.testing import CliRunner

from fx_alfred.cli import cli


pytestmark = [pytest.mark.cli, pytest.mark.integration]


def _project_helper(root: Path, content: str) -> Path:
    helper_dir = root / ".alfred"
    helper_dir.mkdir(exist_ok=True)
    helper = helper_dir / "agent_helpers.py"
    helper.write_text(content)
    return helper


def _user_helper(content: str) -> Path:
    helper_dir = Path.home() / ".alfred"
    helper_dir.mkdir(exist_ok=True)
    helper = helper_dir / "agent_helpers.py"
    helper.write_text(content)
    return helper


def test_agent_call_without_gate_refuses_without_importing_project_helper(
    sample_project,
):
    _project_helper(sample_project, 'raise RuntimeError("helper imported")\n')

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "boom", "--json"],
    )

    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["error"]["type"] == "PermissionError"
    assert "helper imported" not in result.output


def test_agent_call_gate_requires_exact_one(sample_project):
    _project_helper(sample_project, 'def hello():\n    return "ok"\n')

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "hello", "--json"],
        env={"ALFRED_AGENT_TOOLS": "true"},
    )

    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["error"]["type"] == "PermissionError"


def test_agent_call_text_gate_disabled_errors_without_import(sample_project):
    _project_helper(sample_project, 'raise RuntimeError("helper imported")\n')

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "hello"],
    )

    assert result.exit_code != 0
    assert "ALFRED_AGENT_TOOLS=1" in result.output
    assert "helper imported" not in result.output


def test_agent_call_user_helper_json_success(sample_project):
    _user_helper('def hello(name):\n    return {"name": name}\n')

    result = CliRunner().invoke(
        cli,
        [
            "--root",
            str(sample_project),
            "agent",
            "call",
            "hello",
            "--arg",
            "name=Frank",
            "--json",
        ],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["schema_version"] == "1"
    assert data["status"] == "ok"
    assert data["result"] == {"name": "Frank"}
    assert data["source"]["layer"] == "USR"


def test_agent_call_project_overrides_user_without_importing_user(sample_project):
    _project_helper(sample_project, 'def who():\n    return "project"\n')
    _user_helper('raise RuntimeError("user helper imported")\n')

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "who", "--json"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["result"] == "project"
    assert data["source"]["layer"] == "PRJ"


def test_agent_call_project_import_failure_does_not_fallback_to_user(sample_project):
    _project_helper(sample_project, "def broken(:\n    pass\n")
    _user_helper('def broken():\n    return "user"\n')

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "broken", "--json"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["source"]["layer"] == "PRJ"
    assert data["error"]["type"] == "SyntaxError"
    assert "user" not in result.output


def test_agent_call_imported_callable_is_not_registered(sample_project):
    _project_helper(sample_project, "from pathlib import Path\n")

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "Path", "--json"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["error"]["type"] == "HelperNotFound"


def test_agent_call_text_missing_helper_errors(sample_project):
    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "missing"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code != 0
    assert "helper not found: missing" in result.output


def test_agent_call_async_helper_is_awaited(sample_project):
    _project_helper(
        sample_project,
        "async def async_hello(name):\n    return {'message': 'hello ' + name}\n",
    )

    result = CliRunner().invoke(
        cli,
        [
            "--root",
            str(sample_project),
            "agent",
            "call",
            "async_hello",
            "--arg",
            "name=Frank",
            "--json",
        ],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["result"] == {"message": "hello Frank"}


def test_agent_call_arg_splits_on_first_equals(sample_project):
    _project_helper(sample_project, "def echo(url):\n    return url\n")

    result = CliRunner().invoke(
        cli,
        [
            "--root",
            str(sample_project),
            "agent",
            "call",
            "echo",
            "--arg",
            "url=https://example.com?a=1",
            "--json",
        ],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code == 0
    assert json.loads(result.output)["result"] == "https://example.com?a=1"


def test_agent_call_duplicate_arg_is_usage_error(sample_project):
    _project_helper(sample_project, "def echo(name):\n    return name\n")

    result = CliRunner().invoke(
        cli,
        [
            "--root",
            str(sample_project),
            "agent",
            "call",
            "echo",
            "--arg",
            "name=one",
            "--arg",
            "name=two",
        ],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code != 0
    assert "duplicate" in result.output.lower()


def test_agent_call_json_serialization_failure_returns_error(sample_project):
    _project_helper(sample_project, "def bad():\n    return {1, 2, 3}\n")

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "call", "bad", "--json"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["error"]["type"] == "TypeError"


def test_agent_run_json_root_relative_script_uses_current_python(sample_project):
    script = sample_project / "show_executable.py"
    script.write_text(
        "import json, sys\nprint(json.dumps({'executable': sys.executable}))\n"
    )

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "run", "show_executable.py", "--json"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["status"] == "ok"
    assert data["source"]["layer"] == "explicit"
    assert json.loads(data["stdout"])["executable"] == sys.executable


def test_agent_run_missing_script_json_envelope(sample_project):
    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "run", "missing.py", "--json"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code != 0
    data = json.loads(result.output)
    assert data["status"] == "error"
    assert data["exit_code"] is None
    assert "script not found" in data["stderr"]


def test_agent_run_text_mode_replays_stdout_stderr_and_exit_code(sample_project):
    script = sample_project / "noisy.py"
    script.write_text(
        "import sys\n"
        "print('hello stdout')\n"
        "print('hello stderr', file=sys.stderr)\n"
        "raise SystemExit(3)\n"
    )

    result = CliRunner().invoke(
        cli,
        ["--root", str(sample_project), "agent", "run", "noisy.py"],
        env={"ALFRED_AGENT_TOOLS": "1"},
    )

    assert result.exit_code == 3
    assert "hello stdout" in result.output
    assert "hello stderr" in result.output

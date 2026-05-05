from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
import os
import subprocess
import sys
import uuid
from contextlib import contextmanager
from pathlib import Path
from types import ModuleType
from typing import Any, Iterator


SCHEMA_VERSION = "1"
AGENT_TOOLS_ENV = "ALFRED_AGENT_TOOLS"


class AgentArgError(ValueError):
    """Raised when helper arguments are malformed."""


def agent_tools_enabled() -> bool:
    """Return True only when agent tooling is explicitly enabled."""
    return os.environ.get(AGENT_TOOLS_ENV) == "1"


def parse_arg_pairs(arg_pairs: tuple[str, ...]) -> dict[str, str]:
    """Parse repeated key=value options, splitting only on the first equals."""
    result: dict[str, str] = {}
    for pair in arg_pairs:
        if "=" not in pair:
            raise AgentArgError(f"invalid --arg {pair!r}; expected key=value")
        key, value = pair.split("=", 1)
        if not key:
            raise AgentArgError("invalid --arg with empty key")
        if key in result:
            raise AgentArgError(f"duplicate --arg key: {key}")
        result[key] = value
    return result


def gate_error_envelope(kind: str, name: str) -> dict[str, Any]:
    """Build a JSON error envelope for disabled agent tooling."""
    envelope: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "status": "error",
        "source": None,
        "error": {
            "type": "PermissionError",
            "message": f"{AGENT_TOOLS_ENV}=1 is required to run agent {kind}",
        },
    }
    if kind == "helper":
        envelope["helper"] = name
    else:
        envelope["script"] = name
        envelope["exit_code"] = None
        envelope["stdout"] = ""
        envelope["stderr"] = envelope["error"]["message"]
    return envelope


def helper_candidates(root: Path) -> list[tuple[str, Path]]:
    """Return PRJ then USR helper locations."""
    return [
        ("PRJ", root / ".alfred" / "agent_helpers.py"),
        ("USR", Path.home() / ".alfred" / "agent_helpers.py"),
    ]


def _source(layer: str, path: Path) -> dict[str, str]:
    return {"layer": layer, "path": str(path)}


@contextmanager
def _loaded_module(path: Path, layer: str) -> Iterator[ModuleType]:
    """Load a helper module under a unique synthetic name, then remove it."""
    module_name = f"_alfred_agent_helpers_{layer.lower()}_{uuid.uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load helper module: {path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.modules.pop(module_name, None)


def _public_helpers(module: ModuleType) -> dict[str, Any]:
    helpers: dict[str, Any] = {}
    for name, value in vars(module).items():
        if name.startswith("_"):
            continue
        if inspect.isfunction(value) and value.__module__ == module.__name__:
            helpers[name] = value
    return helpers


def _error_envelope(
    helper: str,
    error_type: str,
    message: str,
    source: dict[str, str] | None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "helper": helper,
        "source": source,
        "status": "error",
        "error": {"type": error_type, "message": message},
    }


def _ok_envelope(
    helper: str,
    source: dict[str, str],
    result: Any,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "helper": helper,
        "source": source,
        "status": "ok",
        "result": result,
    }


def call_helper(root: Path, helper_name: str, kwargs: dict[str, str]) -> dict[str, Any]:
    """Find and execute a helper, returning a JSON-serializable envelope."""
    for layer, path in helper_candidates(root):
        if not path.exists():
            continue
        source = _source(layer, path)
        try:
            with _loaded_module(path, layer) as module:
                helpers = _public_helpers(module)
                helper = helpers.get(helper_name)
                if helper is None:
                    continue

                try:
                    if inspect.iscoroutinefunction(helper):
                        result = asyncio.run(helper(**kwargs))
                    else:
                        result = helper(**kwargs)
                except Exception as exc:
                    return _error_envelope(
                        helper_name, type(exc).__name__, str(exc), source
                    )

                try:
                    json.dumps(result)
                except TypeError as exc:
                    return _error_envelope(
                        helper_name, type(exc).__name__, str(exc), source
                    )
                return _ok_envelope(helper_name, source, result)
        except Exception as exc:
            return _error_envelope(helper_name, type(exc).__name__, str(exc), source)

    return _error_envelope(
        helper_name,
        "HelperNotFound",
        f"helper not found: {helper_name}",
        None,
    )


def resolve_script_path(root: Path, script_path: str) -> Path:
    """Resolve script paths relative to the project root unless absolute."""
    path = Path(script_path)
    if not path.is_absolute():
        path = root / path
    return path


def run_script(root: Path, script_path: str) -> dict[str, Any]:
    """Execute a Python script through the current interpreter."""
    path = resolve_script_path(root, script_path)
    source = _source("explicit", path)
    if not path.is_file():
        message = f"script not found: {path}"
        return {
            "schema_version": SCHEMA_VERSION,
            "script": str(path),
            "source": source,
            "status": "error",
            "exit_code": None,
            "stdout": "",
            "stderr": message,
            "error": {"type": "FileNotFoundError", "message": message},
        }

    completed = subprocess.run(
        [sys.executable, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "script": str(path),
        "source": source,
        "status": "ok" if completed.returncode == 0 else "error",
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }

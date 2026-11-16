"""Builders for deterministic, POSIX-shell factory checks."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path

from factory.manifests import lint_check


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def _checked(command: str, reason: str) -> list[str]:
    return [
        "set +e",
        command,
        "status=$?",
        "set -e",
        'if [ "$status" -ne 0 ]; then',
        f"  echo {_quote(reason)} >&2",
        '  exit "$status"',
        "fi",
    ]


def _finish(lines: list[str]) -> str:
    script = "\n".join(lines).rstrip() + "\n"
    problems = lint_check(script)
    if problems:
        raise ValueError("invalid generated check: " + "; ".join(problems))
    return script


def pytest_check(tests: list[str], *, timeout_note: str = "") -> str:
    """Build a check that runs the requested pytest files."""

    command = (
        "PYTHONPATH=$PWD:$PWD/packages/worldkeeper/src TMPDIR=/tmp "
        ".venv/bin/python -m pytest -q -p no:cacheprovider -n 0 " + " ".join(_quote(test) for test in tests)
    )
    lines = ["set -e"]
    if timeout_note:
        lines.append(f"echo {_quote(timeout_note)}")
    lines.extend(_checked(command, "pytest failed"))
    return _finish(lines)


def ruff_check(paths: list[str]) -> str:
    """Build a check for Python lint and format compliance."""

    python_paths = [path for path in paths if path.endswith(".py")]
    quoted_paths = " ".join(_quote(path) for path in python_paths)
    lines = ["set -e"]
    if python_paths:
        lines.extend(_checked(f".venv/bin/python -m ruff check {quoted_paths}", "ruff check failed"))
        lines.extend(
            _checked(
                f".venv/bin/python -m ruff format --check {quoted_paths}",
                "ruff format check failed",
            )
        )
    else:
        lines.extend(["echo 'no Python paths to check'", ":"])
    return _finish(lines)


def json_check(paths: list[str]) -> str:
    """Build a check that validates each JSON file."""

    lines = ["set -e"]
    for path in paths:
        lines.extend(
            _checked(
                f"python -m json.tool {_quote(path)} >/dev/null 2>&1",
                f"invalid JSON: {path}",
            )
        )
    if not paths:
        lines.extend(["echo 'no JSON paths to check'", ":"])
    return _finish(lines)


def node_syntax_check(paths: list[str]) -> str:
    """Build a check that validates JavaScript syntax with Node."""

    lines = ["set -e"]
    for path in paths:
        lines.extend(_checked(f"node --check {_quote(path)}", f"node syntax check failed: {path}"))
    if not paths:
        lines.extend(["echo 'no Node paths to check'", ":"])
    return _finish(lines)


def ownership_check(owned: list[str], patch_path: str) -> str:
    """Build a check that stages only owned paths and records a non-empty patch."""

    if not owned:
        raise ValueError("ownership check requires at least one owned path")
    owned_paths = " ".join(_quote(path) for path in owned)
    case_patterns = "|".join(_quote(path) for path in owned)
    patch = _quote(patch_path)
    lines = [
        "set -e",
        f"git add -A -- {owned_paths}",
        "staged_paths=$(mktemp)",
        "set +e",
        'git diff --cached --name-only > "$staged_paths"',
        "status=$?",
        "set -e",
        'if [ "$status" -ne 0 ]; then',
        '  rm -f "$staged_paths"',
        '  echo "could not inspect staged paths" >&2',
        '  exit "$status"',
        "fi",
        "while IFS= read -r staged_path; do",
        '  case "$staged_path" in',
        f"    {case_patterns}) ;;",
        '    *) echo "staged file is outside task ownership: $staged_path" >&2; rm -f "$staged_paths"; exit 1 ;;',
        "  esac",
        'done < "$staged_paths"',
        'rm -f "$staged_paths"',
        f"git diff --cached > {patch}",
        f"[ -s {patch} ] || {{ echo 'staged patch is empty' >&2; exit 1; }}",
    ]
    return _finish(lines)


def gap_delta_check(root: str, baseline: str, anchors: list[str] | None = None) -> str:
    """Build a check that rejects newly reported story gap results."""

    command = f"python -m factory.checks.gap_delta compare --root {_quote(root)} --baseline {_quote(baseline)}"
    if anchors:
        command += " " + " ".join(f"--anchor {_quote(anchor)}" for anchor in anchors)
    return _finish(["set -e", *_checked(command, "gap delta check failed")])


def compose(*scripts: str) -> str:
    """Compose checks in order, preserving shell output and fail-fast behavior."""

    if not scripts:
        return _finish(["set -e", "echo 'no checks to compose' >&2", "false"])
    return _finish(["set -e", *scripts])


def probe_unsatisfiable(script: str, cwd: Path, *, timeout_s: int = 120) -> bool:
    """Return whether a check fails when run in the supplied directory."""

    try:
        completed = subprocess.run(
            ["/bin/sh", "-c", script],
            cwd=Path(cwd),
            check=False,
            timeout=timeout_s,
            text=True,
            capture_output=True,
        )
    except subprocess.TimeoutExpired:
        return True
    return completed.returncode != 0

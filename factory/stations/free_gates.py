"""Run the free deterministic gates, including the station-5 carry matrix."""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from factory.checks.carry_matrix import CarryMatrixTooLarge, carry_matrix
from factory.checks.gap_delta import DEFAULT_ROOT, load_baseline, new_results, snapshot
from factory.line import StationHandler, StationResult
from storygame.story_package.loader import load_story_package
from storygame.story_source import check_source_tree, compile_source_tree

from .tree import ticket_tree


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _resolve(root: Path, value: object, original_root: Path | None = None) -> Path:
    if not isinstance(value, (str, Path)):
        raise TypeError("path must be a string")
    path = Path(value)
    if path.is_absolute() and original_root is not None:
        with suppress(OSError, RuntimeError, ValueError):
            path = root / path.resolve().relative_to(original_root.resolve())
    return path if path.is_absolute() else root / path


def _command_path(value: str, root: Path, original_root: Path | None) -> str:
    if original_root is None:
        return value
    path = Path(value)
    if not path.is_absolute():
        return value
    try:
        return path.resolve().relative_to(original_root.resolve()).as_posix()
    except (OSError, RuntimeError, ValueError):
        return value


def _tail(output: str) -> str:
    return output[-4000:]


def _carry_failure_output(report) -> str:
    lines = report.lines()
    output = "\n".join(lines)
    if len(output) <= 4000:
        return output
    first_stuck = next((line for line in lines if line.startswith("STUCK ")), None)
    unreachable = [line for line in lines if line.startswith("UNREACHABLE ")]
    preserved = ([first_stuck] if first_stuck else []) + unreachable
    if preserved:
        return "\n".join(preserved)
    return _tail(output)


def _diagnostic_line(diagnostic: Any) -> str:
    return f"{diagnostic.name}: {diagnostic.file}:{diagnostic.address}.{diagnostic.field}: {diagnostic.message}"


def _process_output(completed: subprocess.CompletedProcess) -> str:
    parts = []
    for value in (completed.stdout, completed.stderr):
        if value:
            parts.append(str(value))
    return "".join(parts)


def _run_command(
    run: Callable[..., subprocess.CompletedProcess],
    command: list[str],
    root: Path,
    *,
    timeout: int | None = None,
    env: dict[str, str] | None = None,
) -> tuple[bool, str]:
    kwargs: dict[str, object] = {"cwd": root, "check": False, "capture_output": True, "text": True}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if env is not None:
        kwargs["env"] = env
    try:
        completed = run(command, **kwargs)
    except subprocess.TimeoutExpired:
        return False, "command timed out"
    output = _process_output(completed)
    return completed.returncode == 0, output


def _pytest_environment(root: Path) -> dict[str, str]:
    environment = os.environ.copy()
    paths = [str(root), str(root / "packages/worldkeeper/src")]
    if environment.get("PYTHONPATH"):
        paths.append(environment["PYTHONPATH"])
    environment["PYTHONPATH"] = os.pathsep.join(paths)
    environment["TMPDIR"] = "/tmp"
    return environment


def _pytest_command(tests: list[str]) -> list[str]:
    return [".venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-n", "0", *tests]


def _reason(prefix: str, error: BaseException) -> str:
    detail = str(error).replace("\n", " ").strip()
    return f"{prefix}: {detail}" if detail else prefix


def free_gates_handler(
    root: Path | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> StationHandler:
    """Return a fail-fast handler for the source, gap, Ruff, and test gates."""

    base_root = Path(root) if root is not None else _repository_root()

    def handle(ticket, now: datetime) -> StationResult:
        del now
        payload = ticket.payload
        original_root = base_root
        tree = ticket_tree(payload, ticket.id, original_root)
        repository_root = tree if tree is not None else original_root
        if "gap_baseline" not in payload:
            return StationResult(False, "gap_delta", "missing payload key: gap_baseline")

        source_value = payload.get("source_root")
        if source_value is not None:
            try:
                source_root = _resolve(repository_root, source_value, original_root if tree is not None else None)
                diagnostics = check_source_tree(source_root)
            except (OSError, TypeError, ValueError) as error:
                return StationResult(False, "source_tree", _tail(_reason("source tree check failed", error)))
            if diagnostics:
                return StationResult(
                    False, "source_tree", _tail("\n".join(_diagnostic_line(item) for item in diagnostics))
                )
            try:
                compile_source_tree(source_root)
            except Exception as error:
                return StationResult(False, "source_tree", _tail(str(error) or error.__class__.__name__))

        try:
            story_value = payload.get("story_root", DEFAULT_ROOT)
            story_root = _resolve(repository_root, story_value, original_root if tree is not None else None)
            anchors = payload.get("anchors")
            current = snapshot(story_root, anchors if isinstance(anchors, list) else None)
            baseline = load_baseline(
                _resolve(repository_root, payload["gap_baseline"], original_root if tree is not None else None)
            )
            additions = new_results(baseline, current)
        except (OSError, json.JSONDecodeError, TypeError, ValueError, KeyError) as error:
            return StationResult(False, "gap_delta", _tail(_reason("gap delta check failed", error)))

        gap_lines = [f"NEW {anchor} {result}" for anchor in sorted(additions) for result in additions[anchor]]
        gap_lines.extend(f"ERROR {error}" for error in current.get("__errors__", []))
        if gap_lines:
            return StationResult(False, "gap_delta", _tail("\n".join(gap_lines)))

        if payload.get("carry_matrix", True) is not False:
            try:
                package = load_story_package(story_root)
                carry_scenes = payload.get("carry_scenes")
                selected_scenes = carry_scenes if isinstance(carry_scenes, list) else None
                report = carry_matrix(package, scenes=selected_scenes, mode="one_branch")
            except CarryMatrixTooLarge as error:
                return StationResult(False, "carry_matrix", str(error))
            except Exception as error:
                return StationResult(False, "carry_matrix", str(error) or error.__class__.__name__)
            if report.stuck or report.unreachable:
                return StationResult(False, "carry_matrix", _carry_failure_output(report))

        python_paths = [
            _command_path(path, repository_root, original_root if tree is not None else None)
            for path in payload.get("paths", [])
            if isinstance(path, str) and path.endswith(".py")
        ]
        if python_paths:
            for command in (
                [".venv/bin/python", "-m", "ruff", "check", *python_paths],
                [".venv/bin/python", "-m", "ruff", "format", "--check", *python_paths],
            ):
                passed, output = _run_command(run, command, repository_root)
                if not passed:
                    detail = output or "ruff command failed"
                    return StationResult(False, "ruff", _tail(detail))

        tests = [
            _command_path(path, repository_root, original_root if tree is not None else None)
            for path in payload.get("tests", [])
            if isinstance(path, str)
        ]
        if tests:
            passed, output = _run_command(
                run,
                _pytest_command(tests),
                repository_root,
                timeout=1200,
                env=_pytest_environment(repository_root),
            )
            if not passed:
                detail = output or "pytest command failed"
                return StationResult(False, "tests", _tail(detail))

        return StationResult(True, "free_gates", "all free gates passed")

    return handle

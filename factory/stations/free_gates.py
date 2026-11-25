"""Run free deterministic gates, including story-data reachability and the station-5 carry matrix."""

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
from storygame.runtime.entry_snapshots import check_entry_snapshots, write_entry_snapshots
from storygame.story_cmds.cmd_fmt import format_source_tree
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


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _touches_story_data(
    payload: dict[str, Any],
    repository_root: Path,
    original_root: Path,
    tree: Path | None,
    story_root: Path,
) -> bool:
    if "source_root" in payload:
        return True
    paths = payload.get("paths")
    if not isinstance(paths, list):
        return False
    original = original_root if tree is not None else None
    return any(
        _inside(_resolve(repository_root, path, original), story_root) for path in paths if isinstance(path, str)
    )


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
    """Return a fail-fast handler for source, formatting, snapshot, gap, carry, reachability, Ruff, and test gates."""

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
            story_root = _resolve(
                repository_root,
                payload.get("story_root", DEFAULT_ROOT),
                original_root if tree is not None else None,
            )
        except (OSError, TypeError, ValueError) as error:
            return StationResult(False, "gap_delta", _tail(_reason("gap delta check failed", error)))

        if payload.get("story_format", True) is not False:
            format_root = source_root if source_value is not None else story_root / "source"
            if source_value is None and not format_root.is_dir():
                format_root = None
            if format_root is not None:
                check = not (tree is not None and _inside(format_root, tree))
                try:
                    changed, refused = format_source_tree(format_root, check=check)
                except Exception as error:
                    return StationResult(False, "story_format", _tail(_reason("story format check failed", error)))
                if refused:
                    detail = "\n".join(f"{path}: reformatting would change a value" for path in refused)
                    return StationResult(False, "story_format", _tail(detail))
                if check and changed:
                    detail = "\n".join(f"{path}: run story_cli fmt" for path in changed)
                    return StationResult(False, "story_format", _tail(detail))

        if payload.get("entry_snapshots", True) is not False:
            write_error: str | None = None
            if tree is not None and _inside(story_root, tree):
                try:
                    write_entry_snapshots(story_root)
                except Exception as error:
                    write_error = str(error) or error.__class__.__name__
            try:
                snapshot_problems = check_entry_snapshots(story_root)
            except Exception as error:
                check_error = str(error) or error.__class__.__name__
            else:
                check_error = None
            if write_error is not None:
                return StationResult(False, "entry_snapshots", _tail(write_error))
            if check_error is not None:
                return StationResult(False, "entry_snapshots", _tail(check_error))
            if snapshot_problems:
                return StationResult(False, "entry_snapshots", _tail("\n".join(snapshot_problems)))

        try:
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

        journey_reachability = payload.get("journey_reachability")
        run_journey = journey_reachability is True or (
            journey_reachability is not False
            and _touches_story_data(payload, repository_root, original_root, tree, story_root)
        )
        if run_journey:
            journey_command = [
                ".venv/bin/python",
                "-m",
                "pytest",
                "-q",
                "-p",
                "no:cacheprovider",
                "--run-nightly",
                "-n",
                "8",
                "tests/test_game_path_journeys.py",
                "tests/test_known_unreachable_ratchet.py",
            ]
            passed, output = _run_command(
                run,
                journey_command,
                repository_root,
                timeout=240,
                env=_pytest_environment(repository_root),
            )
            if not passed:
                if output == "command timed out":
                    return StationResult(False, "journey_reachability", output)
                detail = output or "journey reachability failed"
                return StationResult(
                    False,
                    "journey_reachability",
                    _tail("a story realization is unreachable or the ratchet was broken: " + detail),
                )

        paths = payload.get("paths") if isinstance(payload.get("paths"), list) else []
        python_paths = [
            _command_path(path, repository_root, original_root if tree is not None else None)
            for path in paths
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

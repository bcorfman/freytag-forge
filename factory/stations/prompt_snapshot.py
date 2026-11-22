"""Capture and validate deterministic narrator prompt snapshots."""

from __future__ import annotations

import argparse
import difflib
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

from factory.line import StationHandler, StationResult

from .tree import ticket_tree


class SnapshotError(RuntimeError):
    """Raised when the prompt CLI cannot produce a capture."""


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _tail(value: object, limit: int = 4000) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        value = value.decode(errors="replace")
    return str(value)[-limit:].strip()


def _command_error(command: list[str], stderr: object) -> SnapshotError:
    detail = _tail(stderr) or "no stderr"
    return SnapshotError(f"{' '.join(command)} failed: {detail}")


def _command(
    scene: str,
    *,
    package: str | None,
    beat: str | None = None,
    list_beats: bool = False,
) -> list[str]:
    command = [sys.executable, "-m", "bench", "prompt"]
    command.extend(["--scene", scene])
    if list_beats:
        command.append("--list-beats")
    elif beat is None:
        command.append("--text")
    else:
        command.extend(["--beat", beat, "--text"])
    if package is not None:
        command.extend(["--package", str(package)])
    return command


def _run_capture(
    run: Callable[..., subprocess.CompletedProcess],
    command: list[str],
    root: Path,
) -> str:
    try:
        completed = run(command, cwd=root, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired as error:
        stderr = getattr(error, "stderr", None) or getattr(error, "output", None)
        raise _command_error(command, stderr) from error
    if completed.returncode != 0:
        raise _command_error(command, completed.stderr)
    return completed.stdout or ""


def capture_scene(
    scene: str,
    out_dir: Path,
    *,
    root: Path,
    package: str | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> list[str]:
    """Capture the entry prompt and every authored beat prompt for a scene."""

    out_dir.mkdir(parents=True, exist_ok=True)
    listing = _run_capture(run, _command(scene, package=package, list_beats=True), root)
    beat_ids: list[str] = []
    for line in listing.splitlines():
        if not line.strip():
            break
        beat_ids.append(line.split()[0])

    written: list[str] = []
    entry_name = f"{scene}.entry.txt"
    (out_dir / entry_name).write_text(_run_capture(run, _command(scene, package=package), root), encoding="utf-8")
    written.append(entry_name)
    for beat_id in beat_ids:
        name = f"{scene}.beat-{beat_id}.txt"
        (out_dir / name).write_text(
            _run_capture(run, _command(scene, package=package, beat=beat_id), root), encoding="utf-8"
        )
        written.append(name)
    return sorted(written)


def _capture_files(directory: Path) -> dict[str, Path]:
    return {path.name: path for path in directory.iterdir() if path.is_file()}


def _changed_lines(before: str, after: str, name: str) -> list[str]:
    diff = difflib.unified_diff(before.splitlines(), after.splitlines(), fromfile=name, tofile=name, lineterm="")
    changes: list[str] = []
    for line in diff:
        if line.startswith(("---", "+++", "@@")):
            continue
        if not line.startswith(("+", "-")) or line[1:].strip() == "":
            continue
        changes.append(line)
    return changes


def _diff_capture_paths(baseline: dict[str, Path], current: dict[str, Path]) -> dict[str, list[str]]:
    changes: dict[str, list[str]] = {}
    for name in sorted(set(baseline) | set(current)):
        before = baseline[name].read_text(encoding="utf-8") if name in baseline else ""
        after = current[name].read_text(encoding="utf-8") if name in current else ""
        if name in baseline and name in current and before == after:
            continue
        lines = _changed_lines(before, after, name)
        if lines or name not in baseline or name not in current:
            changes[name] = lines
    return changes


def diff_captures(baseline_dir: Path, current_dir: Path) -> dict[str, list[str]]:
    """Return non-blank changed lines for every capture in either directory."""

    return _diff_capture_paths(_capture_files(baseline_dir), _capture_files(current_dir))


def _capture_aliases(capture: str) -> set[str]:
    name = Path(capture).name
    stem = Path(name).stem
    aliases = {name}
    suffix = stem.split(".", 1)[1] if "." in stem else stem
    aliases.add(suffix)
    if suffix.startswith("beat-"):
        aliases.add(suffix.removeprefix("beat-"))
    return aliases


def _matching_rules(capture: str, allowed: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    aliases = _capture_aliases(capture)
    matches: list[dict[str, Any]] = []
    for rule in allowed:
        if not isinstance(rule, dict):
            continue
        rule_capture = rule.get("capture")
        if rule_capture == "*" or (isinstance(rule_capture, str) and rule_capture in aliases):
            matches.append(rule)
    return matches


def _line_is_allowed(capture: str, line: str, allowed: Iterable[dict[str, Any]]) -> bool:
    payload_line = line[1:]
    for rule in _matching_rules(capture, allowed):
        contains = rule.get("contains", [])
        if isinstance(contains, list) and any(isinstance(value, str) and value in payload_line for value in contains):
            return True
    return False


def _capture_is_allowed(capture: str, allowed: Iterable[dict[str, Any]]) -> bool:
    return any(rule.get("new_capture") is True for rule in _matching_rules(capture, allowed))


def _capture_exists(directory: Path, capture: str) -> bool:
    return (directory / capture).is_file()


def unintended(
    changes: dict[str, list[str]],
    allowed: list[dict],
    baseline_dir: Path,
    current_dir: Path,
) -> list[str]:
    """Return changed capture lines that are not covered by the ticket payload."""

    result: list[str] = []
    for capture in sorted(changes):
        baseline_exists = _capture_exists(baseline_dir, capture)
        current_exists = _capture_exists(current_dir, capture)
        if not baseline_exists or not current_exists:
            if not _capture_is_allowed(capture, allowed):
                result.append(f"{capture}: {'new capture' if current_exists else 'removed capture'}")
            continue
        result.extend(f"{capture}: {line}" for line in changes[capture] if not _line_is_allowed(capture, line, allowed))
    return result


def _resolve(root: Path, value: object, original_root: Path | None = None) -> Path:
    if not isinstance(value, (str, Path)):
        raise TypeError("baseline_dir must be a path")
    path = Path(value)
    if path.is_absolute() and original_root is not None:
        with suppress(OSError, RuntimeError, ValueError):
            path = root / path.resolve().relative_to(original_root.resolve())
    return path if path.is_absolute() else root / path


def _package_value(value: object, original_root: Path) -> str | None:
    if value is None:
        return None
    path = Path(value) if isinstance(value, (str, Path)) else None
    if path is not None and path.is_absolute():
        try:
            return path.resolve().relative_to(original_root.resolve()).as_posix()
        except (OSError, RuntimeError, ValueError):
            return str(path)
    return str(value)


def _failure_output(lines: list[str]) -> str:
    detail = "\n".join(lines)
    if len(detail) <= 4000:
        return detail
    shown = detail[:4000]
    cut_lines = len(lines) - shown.count("\n")
    return f"{shown}\n... {cut_lines} more lines cut"


def prompt_snapshot_handler(
    root: Path | None = None,
    run: Callable[..., subprocess.CompletedProcess] = subprocess.run,
) -> StationHandler:
    """Return a handler that checks a scene's prompt payload against its baseline."""

    base_root = Path(root) if root is not None else _repository_root()

    def handle(ticket, now: datetime) -> StationResult:
        del now
        tree = ticket_tree(ticket.payload, ticket.id, base_root)
        repository_root = tree if tree is not None else base_root
        payload = ticket.payload
        if "baseline_dir" not in payload:
            return StationResult(False, "prompt_snapshot", "missing payload key: baseline_dir")
        try:
            baseline_dir = _resolve(repository_root, payload["baseline_dir"], base_root if tree is not None else None)
        except (TypeError, ValueError) as error:
            return StationResult(False, "prompt_snapshot", str(error))
        if not baseline_dir.is_dir():
            return StationResult(False, "prompt_snapshot", f"baseline directory does not exist: {baseline_dir}")

        scene_prefix = f"{ticket.scene}."
        try:
            baseline_files = {
                path.name: path
                for path in baseline_dir.iterdir()
                if path.is_file() and path.name.startswith(scene_prefix)
            }
        except OSError as error:
            return StationResult(False, "prompt_snapshot", str(error))
        baseline_names = set(baseline_files)
        if not baseline_names:
            return StationResult(False, "prompt_snapshot", f"no baseline captures for scene {ticket.scene}")

        allowed = payload.get("allowed_changes", [])
        if not isinstance(allowed, list):
            allowed = []
        package = payload.get("package")
        package_value = (
            _package_value(package, base_root) if tree is not None else (str(package) if package is not None else None)
        )
        try:
            with tempfile.TemporaryDirectory() as temporary_name:
                current_dir = Path(temporary_name)
                capture_scene(ticket.scene, current_dir, root=repository_root, package=package_value, run=run)
                current_files = {
                    path.name: path
                    for path in current_dir.iterdir()
                    if path.is_file() and path.name.startswith(scene_prefix)
                }
                changes = _diff_capture_paths(baseline_files, current_files)
                bad = unintended(changes, allowed, baseline_dir, current_dir)
                compared = baseline_names | set(current_files)
                intended_lines = sum(
                    1
                    for name, lines in changes.items()
                    if _capture_exists(baseline_dir, name) and _capture_exists(current_dir, name)
                    for line in lines
                    if _line_is_allowed(name, line, allowed)
                )
        except SnapshotError as error:
            return StationResult(False, "prompt_snapshot", str(error))
        except (OSError, TypeError, ValueError) as error:
            return StationResult(False, "prompt_snapshot", str(error))

        if bad:
            return StationResult(False, "prompt_snapshot", _failure_output(bad))
        return StationResult(
            True,
            "prompt_snapshot",
            f"{len(compared)} captures compared, {intended_lines} intended changed lines",
        )

    return handle


def main(argv: list[str] | None = None) -> int:
    """Record a prompt snapshot baseline from the command line."""

    command = argparse.ArgumentParser(prog="python -m factory.stations.prompt_snapshot")
    subparsers = command.add_subparsers(dest="subcommand", required=True)
    record = subparsers.add_parser("record", help="capture a scene's prompts")
    record.add_argument("--scene", required=True)
    record.add_argument("--out", type=Path, required=True)
    record.add_argument("--package")
    args = command.parse_args(argv)
    try:
        names = capture_scene(args.scene, args.out, root=_repository_root(), package=args.package)
    except SnapshotError as error:
        print(str(error), file=sys.stderr)
        return 2
    for name in names:
        print(name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

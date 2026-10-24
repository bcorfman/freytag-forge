"""Run the local quick pytest tier while reporting omitted heavy files."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DURATIONS_PATH = ROOT / "tests" / "shard_durations.json"


def load_durations(path: Path = DURATIONS_PATH) -> dict[str, float]:
    """Load repository-relative test-file durations from a shard report."""
    payload = json.loads(path.read_text())
    return {str(name): float(seconds) for name, seconds in payload["files"].items()}


def _relative(path: Path) -> str:
    return path.resolve().relative_to(ROOT).as_posix()


def _also_matches(path: Path, also: Iterable[str]) -> bool:
    relative = _relative(path)
    for candidate in also:
        candidate_path = Path(candidate)
        if not candidate_path.is_absolute():
            candidate_path = ROOT / candidate_path
        try:
            candidate_relative = candidate_path.resolve().relative_to(ROOT).as_posix()
        except ValueError:
            continue
        if relative == candidate_relative or path.is_relative_to(candidate_path.resolve()):
            return True
    return False


def select_test_files(
    *, threshold: float = 15.0, durations_path: Path = DURATIONS_PATH, also: Iterable[str] = ()
) -> tuple[list[Path], list[tuple[Path, float]]]:
    """Return selected test files and skipped heavy files in stable path order."""
    durations = load_durations(durations_path)
    selected: list[Path] = []
    skipped: list[tuple[Path, float]] = []
    for path in sorted((ROOT / "tests").rglob("test_*.py")):
        seconds = durations.get(_relative(path))
        heavy = seconds is not None and seconds >= threshold
        if heavy and not _also_matches(path, also):
            skipped.append((path, seconds))
        else:
            selected.append(path)
    return selected, skipped


def _display_command(command: list[str]) -> str:
    return " ".join(repr(part) if " " in part else part for part in command)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--threshold", type=float, default=15.0)
    parser.add_argument("--also", nargs="+", default=[], metavar="PATH")
    parser.add_argument("--list", action="store_true", dest="list_only")
    return parser


def main(argv: list[str] | None = None, *, durations_path: Path = DURATIONS_PATH) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if "--" in arguments:
        separator = arguments.index("--")
        own_arguments, pytest_arguments = arguments[:separator], arguments[separator + 1 :]
    else:
        own_arguments, pytest_arguments = arguments, []
    options = _parser().parse_args(own_arguments)
    durations = load_durations(durations_path)
    selected, skipped = select_test_files(threshold=options.threshold, durations_path=durations_path, also=options.also)
    predicted_cpu = sum(durations.get(_relative(path), 0.0) for path in selected)

    print(f"Selected {len(selected)} test files; skipped {len(skipped)} heavy files.")
    if options.list_only:
        for path in selected:
            print(f"SELECTED {_relative(path)} ({durations.get(_relative(path), 0.0):.3f}s)")
        for path, seconds in skipped:
            print(f"SKIPPED {_relative(path)} ({seconds:.3f}s)")
        print(f"Predicted quick-tier CPU seconds: {predicted_cpu:.3f}")
        return 0

    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--no-cov",
        "-p",
        "no:cacheprovider",
        "-n",
        "auto",
        *(str(path) for path in selected),
        *pytest_arguments,
    ]
    environment = os.environ.copy()
    environment.setdefault("TMPDIR", "/tmp")
    result = subprocess.run(command, cwd=ROOT, env=environment, check=False)
    if skipped:
        print("Heavy files skipped:")
        for path, seconds in skipped:
            print(f"  {_relative(path)} ({seconds:.3f}s)")
        heavy_command = [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--no-cov",
            "-p",
            "no:cacheprovider",
            "-n",
            "auto",
            *(str(path) for path, _ in skipped),
        ]
        print(f"Run skipped files with: {_display_command(heavy_command)}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

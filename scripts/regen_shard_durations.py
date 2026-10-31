"""Regenerate the test-file duration manifest from a tier report."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DURATIONS_PATH = ROOT / "tests" / "shard_durations.json"


def test_files(root: Path = ROOT) -> set[str]:
    """Return repository-relative test files that can be timed."""
    tests_root = root / "tests"
    return {path.relative_to(root).as_posix() for path in tests_root.rglob("test_*.py")}


def load_payload(path: Path) -> dict[str, float]:
    """Load the file durations from a version-one manifest."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return {str(name): float(seconds) for name, seconds in payload["files"].items()}


def missing_files(durations_path: Path = DURATIONS_PATH, root: Path = ROOT) -> list[str]:
    """Return test files on disk that are absent from the manifest."""
    return sorted(test_files(root) - set(load_payload(durations_path)))


def build_payload(file_seconds: Mapping[str, float]) -> dict[str, object]:
    """Build a sorted, rounded version-one manifest payload."""
    return {
        "version": 1,
        "files": {name: round(float(file_seconds[name]), 2) for name in sorted(file_seconds)},
    }


def merge_missing(
    existing: Mapping[str, float], report_seconds: Mapping[str, float], *, root: Path = ROOT
) -> dict[str, float]:
    """Keep current files, add report timings for missing files, and drop stale files."""
    present = test_files(root)
    missing = present - set(existing)
    merged = {name: seconds for name, seconds in existing.items() if name in present}
    merged.update({name: report_seconds[name] for name in missing if name in report_seconds})
    return merged


def write_payload(file_seconds: Mapping[str, float], durations_path: Path = DURATIONS_PATH) -> None:
    """Write a duration manifest with stable formatting."""
    durations_path.write_text(json.dumps(build_payload(file_seconds), indent=2) + "\n", encoding="utf-8")


def _report_seconds(report_path: Path) -> dict[str, float]:
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return {str(name): float(seconds) for name, seconds in payload["file_seconds"].items()}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--missing-only", action="store_true")
    parser.add_argument("--from-report", type=Path, metavar="PATH")
    return parser


def _run_pytest(report_path: Path, files: list[str] | None = None) -> int:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--no-cov",
        "-p",
        "no:cacheprovider",
        "-n",
        "4",
        "--tier-report",
        str(report_path),
        *(files or []),
    ]
    environment = os.environ.copy()
    environment.setdefault("TMPDIR", "/tmp")
    return subprocess.run(command, cwd=ROOT, env=environment, check=False).returncode


def main(argv: list[str] | None = None, *, durations_path: Path = DURATIONS_PATH) -> int:
    options = _parser().parse_args(sys.argv[1:] if argv is None else argv)
    existing = load_payload(durations_path)
    missing = missing_files(durations_path)
    if options.missing_only and not missing:
        print("No missing test files; shard durations are unchanged.")
        return 0

    report_path: Path | None = options.from_report
    temporary_path: Path | None = None
    if report_path is None:
        descriptor, name = tempfile.mkstemp(prefix="tier-report-", suffix=".json", dir=ROOT)
        os.close(descriptor)
        temporary_path = Path(name)
        report_path = temporary_path

    try:
        if options.from_report is None:
            exit_status = _run_pytest(report_path, missing if options.missing_only else None)
            if exit_status not in (0, 5):
                print(f"Refusing to write shard durations: pytest exited with status {exit_status}.", file=sys.stderr)
                return exit_status or 1
        report_seconds = _report_seconds(report_path)
        file_seconds = merge_missing(existing, report_seconds) if options.missing_only else report_seconds
        write_payload(file_seconds, durations_path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
    print(f"Wrote {durations_path}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

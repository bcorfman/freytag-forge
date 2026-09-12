"""Guard for a full_access task running directly in the real repository.

A full_access worker has no sandbox, so the usual "you own only these files"
instruction is not enforced by anything. This check enforces it: the only paths
allowed to change are benchmark OUTPUT paths. Any edit to tracked source, tests,
story data or docs fails the task loudly and names the files.

Usage: check_no_source_drift.py <repo-root> [<allowed-prefix> ...]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

DEFAULT_ALLOWED = ("bench/results/", "bench-report.md")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: check_no_source_drift.py <repo-root> [<allowed-prefix> ...]", file=sys.stderr)
        return 2
    repo = Path(argv[1])
    allowed = tuple(argv[2:]) or DEFAULT_ALLOWED

    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        print(f"FAIL: could not read git status in {repo}: {result.stderr.strip()}", file=sys.stderr)
        return 1

    drifted: list[str] = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        path = line[3:].strip().strip('"')
        # Renames report "old -> new"; judge the destination.
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if not any(path.startswith(prefix) for prefix in allowed):
            drifted.append(f"{line[:2].strip() or '??'} {path}")

    if drifted:
        print("FAIL: a full_access worker modified paths outside the benchmark output", file=sys.stderr)
        print(f"  allowed prefixes: {', '.join(allowed)}", file=sys.stderr)
        for entry in drifted:
            print(f"  - {entry}", file=sys.stderr)
        print(
            "  This task may only produce benchmark artifacts. Revert these changes; a benchmark run must never "
            "edit source, tests, story data, or docs.",
            file=sys.stderr,
        )
        return 1

    print(f"PASS: no source drift; changes confined to {', '.join(allowed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

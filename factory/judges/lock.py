"""Freeze the source files that define factory judge questions."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

DEFAULT_PATTERNS = (
    "bench/*-judge.mjs",
    "bench/calibration/labels-*.json",
    "bench/calibration/check_calib.py",
)
DEFAULT_LOCK = "factory/state/judge-lock.json"
DEFAULT_ROOT = Path(__file__).resolve().parents[2]


def _lock_path(root: Path, lock_path: Path | str | None) -> Path:
    path = Path(lock_path or DEFAULT_LOCK)
    return path if path.is_absolute() else root / path


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError:
        return False
    return True


def compute(root: Path, patterns: tuple[str, ...] = DEFAULT_PATTERNS) -> dict[str, str]:
    """Hash all matching regular files beneath ``root`` by POSIX path."""

    root = Path(root)
    hashes: dict[str, str] = {}
    for pattern in patterns:
        if Path(pattern).is_absolute():
            continue
        for path in root.glob(pattern):
            if not path.is_file() or not _inside_root(path, root):
                continue
            relative = path.relative_to(root).as_posix()
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return dict(sorted(hashes.items()))


def write(
    root: Path,
    lock_path: Path | str | None = None,
    patterns: tuple[str, ...] = DEFAULT_PATTERNS,
) -> dict[str, str]:
    """Write and return the current judge-question hashes."""

    root = Path(root)
    result = compute(root, patterns)
    path = _lock_path(root, lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def check(
    root: Path,
    lock_path: Path | str | None = None,
    patterns: tuple[str, ...] = DEFAULT_PATTERNS,
) -> list[str]:
    """Return stable, human-readable differences between lock and disk."""

    root = Path(root)
    path = _lock_path(root, lock_path)
    locked = json.loads(path.read_text(encoding="utf-8"))
    current = compute(root, patterns)
    changed = sorted(f"changed {name}" for name in locked.keys() & current.keys() if locked[name] != current[name])
    missing = sorted(f"missing {name}" for name in locked.keys() - current.keys())
    new = sorted(f"new {name}" for name in current.keys() - locked.keys())
    return changed + missing + new


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("write", "check"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
        subparser.add_argument("--lock", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the lock writer or checker."""

    options = _parser().parse_args(argv)
    if options.command == "write":
        result = write(options.root, options.lock)
        print(f"locked {len(result)} files")
        return 0

    try:
        differences = check(options.root, options.lock)
    except FileNotFoundError:
        print(f"lock file not found: {_lock_path(options.root, options.lock)}", file=sys.stderr)
        return 2
    if differences:
        print("\n".join(differences))
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

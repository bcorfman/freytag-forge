"""Guard the factory's frozen harness against accidental changes."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections.abc import Sequence
from pathlib import Path


def _normalise_path(path: str | Path) -> str:
    value = str(path).replace("\\", "/")
    if value.startswith("/") or re.match(r"^[A-Za-z]:/", value):
        raise ValueError(f"absolute paths are not allowed: {path}")

    parts = value.split("/")
    while parts and parts[0] == ".":
        parts.pop(0)
    if ".." in parts:
        raise ValueError(f"parent path segments are not allowed: {path}")
    return "/".join(part for part in parts if part not in ("", "."))


def load_patterns(path: Path) -> list[str]:
    """Load frozen repo-relative glob patterns from a JSON configuration file."""

    with path.open(encoding="utf-8") as stream:
        config = json.load(stream)
    patterns = config["frozen"]
    if not isinstance(patterns, list) or not all(isinstance(pattern, str) for pattern in patterns):
        raise ValueError("frozen configuration must contain a list of string patterns")
    return [_normalise_path(pattern) for pattern in patterns]


def glob_to_regex(glob: str) -> re.Pattern[str]:
    """Convert the supported repo-relative glob syntax into an anchored regex."""

    normalised = _normalise_path(glob)
    pieces: list[str] = ["^"]
    index = 0
    while index < len(normalised):
        if normalised.startswith("**/", index):
            pieces.append("(?:.*/)?")
            index += 3
        elif normalised.startswith("**", index):
            pieces.append(".*")
            index += 2
        elif normalised[index] == "*":
            pieces.append("[^/]*")
            index += 1
        else:
            pieces.append(re.escape(normalised[index]))
            index += 1
    pieces.append("$")
    return re.compile("".join(pieces))


def is_frozen(path: str | Path, patterns: list[str]) -> bool:
    """Return whether a normalized repo-relative path matches any frozen glob."""

    normalised = _normalise_path(path)
    return any(glob_to_regex(pattern).fullmatch(normalised) is not None for pattern in patterns)


def touches_frozen(paths: Sequence[str | Path], patterns: list[str]) -> list[str]:
    """Return sorted, unique normalized paths that match the frozen patterns."""

    normalised = {_normalise_path(path) for path in paths}
    return sorted(path for path in normalised if is_frozen(path, patterns))


def changed_paths(repo: Path, base: str) -> list[str]:
    """Collect tracked changes from ``base`` and standard untracked files."""

    diff = subprocess.run(
        ["git", "-C", str(repo), "diff", "--name-only", base],
        check=True,
        capture_output=True,
        text=True,
    )
    untracked = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "--others", "--exclude-standard"],
        check=True,
        capture_output=True,
        text=True,
    )
    paths = diff.stdout.splitlines() + untracked.stdout.splitlines()
    return sorted({_normalise_path(path) for path in paths})


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check whether a change touches the frozen harness.")
    parser.add_argument("--repo", type=Path, default=Path("."))
    parser.add_argument("--base", required=True)
    parser.add_argument("--patterns", type=Path, default=Path(__file__).parent / "config" / "frozen.json")
    args = parser.parse_args(argv)

    patterns = load_patterns(args.patterns)
    touched = touches_frozen(changed_paths(args.repo, args.base), patterns)
    if touched:
        print("\n".join(touched))
        return 1
    print("ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

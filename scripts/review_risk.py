"""Produce an advisory pull-request review-risk classification."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml

TIERS = ("low", "ordinary", "high")


def _run_git(*args: str) -> str:
    result = subprocess.run(["git", *args], check=False, capture_output=True, text=True)
    if result.returncode:
        message = result.stderr.strip() or f"git {' '.join(args)} failed"
        raise RuntimeError(message)
    return result.stdout


def load_policy(path: Path) -> dict:
    try:
        policy = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f"could not load policy {path}: {exc}") from exc
    if not isinstance(policy, dict) or policy.get("version") != 1 or policy.get("enforcement") != "advisory":
        raise ValueError("policy must declare version 1 and advisory enforcement")
    tiers = policy.get("tiers")
    if not isinstance(tiers, dict) or set(tiers) != set(TIERS):
        raise ValueError("policy tiers must have exactly low, ordinary, and high")
    for tier in TIERS:
        if not isinstance(tiers[tier], dict) or not isinstance(tiers[tier].get("paths"), list):
            raise ValueError(f"policy tier {tier} must contain a paths list")
    return policy


def _glob_regex(pattern: str) -> re.Pattern[str]:
    """Compile repository globs: ** crosses directories, while * does not."""
    pieces: list[str] = []
    index = 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            pieces.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            pieces.append(".*")
            index += 2
        elif pattern[index] == "*":
            pieces.append("[^/]*")
            index += 1
        elif pattern[index] == "?":
            pieces.append("[^/]")
            index += 1
        else:
            pieces.append(re.escape(pattern[index]))
            index += 1
    return re.compile("^" + "".join(pieces) + "$")


def _matches(path: str, pattern: str) -> bool:
    return _glob_regex(pattern).fullmatch(path.replace("\\", "/")) is not None


def classify_paths(paths: list[str], policy: dict) -> str:
    if not paths:
        return "low"
    highest = "low"
    tiers = policy["tiers"]
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        path_tier = policy.get("default_tier", "ordinary")
        for tier in reversed(TIERS):
            if any(_matches(normalized, pattern) for pattern in tiers[tier]["paths"]):
                path_tier = tier
                break
        if TIERS.index(path_tier) > TIERS.index(highest):
            highest = path_tier
    return highest


def is_documentation_only(paths: list[str]) -> bool:
    if not paths:
        return False
    for path in paths:
        normalized = path.replace("\\", "/")
        if normalized.startswith("./"):
            normalized = normalized[2:]
        if not (
            (normalized.startswith("docs/") or normalized.startswith(".plans/"))
            and normalized.endswith(".md")
            or normalized in {"README.md", "LICENSE"}
        ):
            return False
    return True


def detect_weakened_assertions(diff: str) -> list[str]:
    """Return test files with heuristic evidence of possibly weakened assertions."""
    reports: list[str] = []
    current: str | None = None
    old_path: str | None = None
    new_path: str | None = None
    deleted = False
    removed = added = 0
    added_skip = False

    def finish() -> None:
        nonlocal removed, added, added_skip, deleted, current, old_path, new_path
        candidates = [path for path in (old_path, new_path) if path and _is_test_path(path)]
        if candidates and (deleted or removed > added or added_skip):
            for path in candidates:
                if path not in reports:
                    reports.append(path)
        removed = added = 0
        added_skip = deleted = False
        current = old_path = new_path = None

    for line in diff.splitlines():
        if line.startswith("diff --git "):
            finish()
            header_paths = re.match(r"^a/(.*) b/(.*)$", line.removeprefix("diff --git "))
            if header_paths:
                old_path = _diff_path(f"a/{header_paths.group(1)}")
                new_path = _diff_path(f"b/{header_paths.group(2)}")
        elif line.startswith("deleted file mode"):
            deleted = True
        elif line.startswith("--- "):
            old_path = _diff_path(line[4:])
        elif line.startswith("+++ "):
            new_path = _diff_path(line[4:])
        elif line.startswith("-") and not line.startswith("---"):
            if _assertion_line(line[1:]):
                removed += 1
        elif line.startswith("+") and not line.startswith("+++"):
            if _assertion_line(line[1:]):
                added += 1
            if re.search(
                r"pytest\.mark\.(?:skip|skipif|xfail)\b|pytest\.(?:skip|xfail|importorskip)\s*\(",
                line[1:],
            ):
                added_skip = True
    finish()
    return reports


def _diff_path(value: str) -> str | None:
    value = value.strip().split("\t", 1)[0]
    return None if value == "/dev/null" else value.removeprefix("a/").removeprefix("b/")


def _is_test_path(path: str) -> bool:
    return path.startswith("tests/") or re.match(r"^packages/[^/]+/tests(?:/|$)", path) is not None


def _assertion_line(line: str) -> bool:
    return bool(re.search(r"\bassert\b|pytest\.raises", line))


def _parse_changed_paths(name_status: str) -> list[str]:
    paths: list[str] = []
    records = name_status.split("\0")
    index = 0
    while index < len(records) - 1:
        status = records[index]
        index += 1
        changed = [records[index]]
        index += 1
        if status[0] in {"R", "C"}:
            changed.append(records[index])
            index += 1
        for path in changed:
            if path not in paths:
                paths.append(path)
    return paths


def _main(args: argparse.Namespace) -> int:
    policy = load_policy(Path(args.policy))
    diff = _run_git(
        "-c", "core.quotePath=false", "diff", "--find-renames", "--no-ext-diff", f"{args.base}...{args.head}"
    )
    name_status = _run_git(
        "-c", "core.quotePath=false", "diff", "--name-status", "-z", "--find-renames", f"{args.base}...{args.head}"
    )
    paths = _parse_changed_paths(name_status)
    tier = classify_paths(paths, policy)
    flags = detect_weakened_assertions(diff)
    if flags:
        tier = "high"
    head_sha = _run_git("rev-parse", args.head).strip()
    treatment = policy["tiers"][tier]["treatment"]
    lines = [f"## Review risk: {tier}", "", treatment, "", f"Reviewed commit: {head_sha}", ""]
    lines.append("Files setting the tier:")
    lines.extend(f"- `{path}`" for path in paths if classify_paths([path], policy) == tier)
    if flags:
        lines.extend(["", "Possibly weakened safety assertions (heuristic; review manually):"])
        lines.extend(f"- `{path}`" for path in flags)
    lines.extend(["", "This result is advisory and applies only to that commit."])
    print("\n".join(lines))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--head", required=True)
    parser.add_argument("--policy", default=".github/review-policy.yml")
    try:
        return _main(parser.parse_args())
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"review risk error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

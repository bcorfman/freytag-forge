"""Ringer worker task specifications and safe manifest generation."""

from __future__ import annotations

import json
import re
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WORKER_PREAMBLE = """The cwd IS a git worktree of {repo} detached at HEAD; edit files there.
NEVER git commit; never touch {repo} itself; never run `uv`; never call a billed model or the network.
First run `[ -e .venv ] || ln -s {repo}/.venv .venv`.
Run tests with `PYTHONPATH=$PWD TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 <tests>`;
Never pass `--cov`.
Run Ruff via `.venv/bin/python -m ruff`.
Never delete the .venv link.
Edit only owned files.
"""


@dataclass
class TaskSpec:
    key: str
    task_type: str = "code-feature"
    spec_body: str = ""
    verified: str = ""
    ownership: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    check_extra: str = ""
    engine: str = "codex"
    effort: str = "high"
    max_attempts: int = 2
    timeout_s: int = 1800
    check_timeout_s: int = 600


def lint_check(check: str) -> list[str]:
    """Find unsafe or ineffective patterns in a generated Ringer check."""

    problems: list[str] = []
    lines = check.splitlines()
    set_pattern = re.compile(r"^\s*set\s+(-[^\s#;]+)(?:\s|;|$)")
    set_lines = [line for line in lines if set_pattern.match(line)]
    has_errexit = any("e" in match.group(1)[1:] for line in set_lines if (match := set_pattern.match(line)))
    has_pipefail = bool(re.search(r"\bpipefail\b", check))

    if not has_errexit:
        problems.append("The check does not enable errexit, so an early failure can be followed by a false PASS.")
    if "PIPESTATUS" in check:
        problems.append("PIPESTATUS is a Bashism, so the check is not portable to the required shell.")
    if re.search(r"(?<!\|)\|\s*(?:tail|head)(?:\s|$)", check) and not has_pipefail:
        problems.append("Piping into tail or head without pipefail can hide the preceding command's failure status.")

    body_start = next((index for index, line in enumerate(lines) if set_pattern.match(line)), None)
    body_lines = lines[body_start + 1 :] if body_start is not None else []
    meaningful_body = [line.strip() for line in body_lines if line.strip() and not line.lstrip().startswith("#")]
    harmless_line = re.compile(r"(?:true|echo(?:\s.*)?|exit\s+0)\s*$")
    if body_start is not None and (
        not meaningful_body or all(harmless_line.fullmatch(line) for line in meaningful_body)
    ):
        problems.append("The check body has no failing command, so it cannot detect a worker failure.")

    if re.search(r"\brm\s+(?:-[^\s]*f[^\s]*\s+)?\.venv(?:\s|$)", check):
        problems.append("Removing .venv can destroy the worker's required virtual-environment link.")
    if "--cov" in check:
        problems.append(
            "Using --cov makes the check depend on coverage behavior instead of the requested test contract."
        )
    return problems


def _quote(value: str | Path) -> str:
    return shlex.quote(str(value))


def build_check(task: TaskSpec, repo: str, workdir: str) -> str:
    """Build a POSIX-style worker check that verifies and stages one task."""

    owned = list(task.ownership)
    tests = list(task.tests)
    owned_python = [path for path in owned if path.endswith(".py")]
    pytest_output = '"$pytest_output"'
    patch_path = Path(workdir) / f"{task.key}.patch"
    repo_venv = Path(repo) / ".venv"

    lines = [
        "set -eo pipefail",
        "",
        f"[ -e .venv ] || ln -s {_quote(repo_venv)} .venv",
        "pytest_output=$(mktemp)",
        "set +e",
        "PYTHONPATH=$PWD TMPDIR=/tmp .venv/bin/python -m pytest -q -p no:cacheprovider -n 0 "
        + " ".join(_quote(test) for test in tests)
        + f" > {pytest_output} 2>&1",
        "pytest_status=$?",
        "set -e",
        f"tail -n 80 {pytest_output}",
        f"rm -f {pytest_output}",
        'if [ "$pytest_status" -ne 0 ]; then',
        '  exit "$pytest_status"',
        "fi",
    ]

    if owned_python:
        python_paths = " ".join(_quote(path) for path in owned_python)
        lines.extend(
            [
                f".venv/bin/python -m ruff check {python_paths}",
                f".venv/bin/python -m ruff format --check {python_paths}",
            ]
        )

    if task.check_extra.strip():
        lines.extend(["", task.check_extra.rstrip()])

    owned_paths = " ".join(_quote(path) for path in owned)
    case_patterns = "|".join(_quote(path) for path in owned)
    staged_paths = '"$staged_paths"'
    lines.extend(
        [
            "",
            f"git add -A -- {owned_paths}",
            "staged_paths=$(mktemp)",
            f"git diff --cached --name-only > {staged_paths}",
            "while IFS= read -r staged_path; do",
            '  case "$staged_path" in',
            f"    {case_patterns}) ;;",
            '    *) echo "staged file is outside task ownership: $staged_path" >&2; exit 1 ;;',
            "  esac",
            f"done < {staged_paths}",
            f"rm -f {staged_paths}",
            f"git diff --cached > {_quote(patch_path)}",
            f"[ -s {_quote(patch_path)} ] || {{ echo 'staged patch is empty' >&2; exit 1; }}",
        ]
    )
    return "\n".join(lines) + "\n"


def build_manifest(
    run_name: str,
    repo: str,
    workdir: str,
    tasks: list[TaskSpec],
    max_parallel: int = 4,
) -> dict[str, Any]:
    """Build and validate a manifest with disjoint task ownership."""

    seen_keys: set[str] = set()
    seen_ownership: dict[str, str] = {}
    manifest_tasks: list[dict[str, Any]] = []

    for task in tasks:
        if task.key in seen_keys:
            raise ValueError(f"duplicate task key: {task.key}")
        seen_keys.add(task.key)
        ownership = list(task.ownership)
        if not ownership:
            raise ValueError(f"task {task.key} must own at least one file")
        for path in ownership:
            previous_key = seen_ownership.get(path)
            if previous_key is not None:
                raise ValueError(f"ownership overlap for {path}: {previous_key} and {task.key}")
            seen_ownership[path] = task.key

        owned_sentence = ", ".join(ownership)
        verified = task.verified or (
            f"Checks that {task.key} changed only the owned files and the repository tests and checks it names pass."
        )
        spec = (
            WORKER_PREAMBLE.format(repo=repo) + f"\nYou own exactly these files: {owned_sentence}.\n\n" + task.spec_body
        )
        check = build_check(task, repo, workdir)
        assert not lint_check(check), lint_check(check)
        manifest_tasks.append(
            {
                "key": task.key,
                "task_type": task.task_type,
                "engine": task.engine,
                "engine_args": ["-c", f"model_reasoning_effort={task.effort}"],
                "max_attempts": task.max_attempts,
                "timeout_s": task.timeout_s,
                "check_timeout_s": task.check_timeout_s,
                "ownership": ownership,
                "verified": verified,
                "spec": spec,
                "check": check,
            }
        )

    return {
        "run_name": run_name,
        "workdir": workdir,
        "max_parallel": max_parallel,
        "worktrees": True,
        "repo": repo,
        "tasks": manifest_tasks,
    }


def write_manifest(manifest: dict[str, Any], path: str | Path) -> None:
    """Write a manifest as readable, indented JSON."""

    Path(path).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

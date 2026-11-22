"""Locate the patched worktree produced by the wiring station."""

from __future__ import annotations

import subprocess
from pathlib import Path

from factory.followups import _safe_id


def _inside(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _git_value(path: Path, *arguments: str) -> Path | str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(path), *arguments],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def ticket_tree(payload: dict, ticket_id: str, root: Path) -> Path | None:
    """Return a ticket's applied tree when it is a worktree of ``root``."""

    workspace_value = payload.get("workspace")
    if not isinstance(workspace_value, str):
        return None
    try:
        workspace = Path(workspace_value).expanduser().resolve()
        repository_root = Path(root).expanduser().resolve()
    except (OSError, RuntimeError, TypeError, ValueError):
        return None
    safe_id = _safe_id(ticket_id)
    candidate = (workspace / safe_id / "tree").resolve()
    if not _inside(candidate, workspace) or not candidate.is_dir():
        return None
    if not (candidate / ".git").is_file():
        return None
    if _git_value(candidate, "rev-parse", "--is-inside-work-tree") != "true":
        return None

    candidate_common = _git_value(candidate, "rev-parse", "--git-common-dir")
    root_common = _git_value(repository_root, "rev-parse", "--git-common-dir")
    if not isinstance(candidate_common, str) or not isinstance(root_common, str):
        return None
    candidate_common_path = Path(candidate_common)
    root_common_path = Path(root_common)
    if not candidate_common_path.is_absolute():
        candidate_common_path = candidate / candidate_common_path
    if not root_common_path.is_absolute():
        root_common_path = repository_root / root_common_path
    try:
        if candidate_common_path.resolve() != root_common_path.resolve():
            return None
    except OSError:
        return None
    return candidate

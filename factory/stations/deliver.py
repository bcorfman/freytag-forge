"""Deliver a factory-created fix through GitHub and staging."""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from factory.followups import _safe_id
from factory.frozen import load_patterns, touches_frozen
from factory.guard import LimitSleep
from factory.line import StationHandler, StationResult
from factory.stations.live_playtest import _fetch_version
from factory.stations.tree import ticket_tree

_RUNNER = Callable[[list[str], Path], tuple[int, str]]
_MERGE_BLOCKED_PREFIXES = ("factory", ".github", "scripts")
_PR_URL_NUMBER_RE = re.compile(r"/pull/(\d+)")


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _default_runner(argv: list[str], cwd: Path) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            argv,
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return 1, str(error)
    output = "".join(str(value) for value in (completed.stdout, completed.stderr) if value)
    return completed.returncode, output


def _redact(value: str) -> str:
    result = value
    for secret in os.environ.values():
        if secret and len(secret) >= 8:
            result = result.replace(secret, "[redacted]")
    return result


def _one_line(value: str) -> str:
    return " ".join(_redact(value).split())


def _atomic_json_write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: str | None = None
    try:
        descriptor, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", text=True)
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary)


def _record(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _run(runner: _RUNNER, argv: list[str], cwd: Path) -> tuple[bool, str]:
    try:
        code, output = runner(argv, cwd)
    except Exception as error:
        return False, _one_line(str(error) or error.__class__.__name__)
    if not isinstance(code, int) or not isinstance(output, str):
        return False, "runner returned an invalid result"
    return code == 0, output


def _changed_paths(runner: _RUNNER, tree: Path) -> tuple[list[str] | None, str | None]:
    passed, output = _run(runner, ["git", "merge-base", "HEAD", "origin/main"], tree)
    if not passed or not output.strip():
        return None, "could not inspect tree diff"
    merge_base = output.strip().splitlines()[-1]
    passed, output = _run(runner, ["git", "diff", "--name-only", merge_base, "--"], tree)
    if not passed:
        return None, "could not inspect tree diff"
    tracked = output.splitlines()
    passed, output = _run(runner, ["git", "ls-files", "--others", "--exclude-standard"], tree)
    if not passed:
        return None, "could not inspect untracked files"
    paths = sorted({path.replace("\\", "/") for path in tracked + output.splitlines() if path.strip()})
    return paths, None


def _diff_hash(runner: _RUNNER, tree: Path, paths: list[str]) -> tuple[str | None, str | None]:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.encode("utf-8", errors="surrogateescape"))
        digest.update(b"\0")
        file_path = tree / path
        try:
            content = file_path.read_bytes() if file_path.is_file() else b"<deleted>"
        except OSError:
            return None, "could not read changed file"
        digest.update(hashlib.sha256(content).hexdigest().encode("ascii"))
        digest.update(b"\0")
    return digest.hexdigest(), None


def _blocked_paths(paths: list[str], patterns_path: Path) -> list[str]:
    try:
        patterns = load_patterns(patterns_path)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        patterns = []
    blocked = [
        path
        for path in paths
        if path in _MERGE_BLOCKED_PREFIXES or any(path.startswith(f"{prefix}/") for prefix in _MERGE_BLOCKED_PREFIXES)
    ]
    return sorted(set(blocked + touches_frozen(paths, patterns)))


def _ticket_class(ticket: Any) -> str:
    value = getattr(ticket, "ticket_class", None)
    return getattr(value, "value", None) or str(value or getattr(ticket, "payload", {}).get("class", "unknown"))


def _gate_tail(output: str) -> str:
    return _one_line(output[-4000:])


def _pr_number(output: str) -> int | None:
    match = _PR_URL_NUMBER_RE.search(output)
    if match:
        return int(match.group(1))
    stripped = output.strip()
    return int(stripped) if stripped.isdigit() else None


def _staging_check(runner: _RUNNER, root: Path, now: datetime) -> str | None:
    lock = root / "factory/state/staged_run.lock"
    if lock.exists():
        raise LimitSleep("staging", now + timedelta(seconds=600))
    passed, output = _run(
        runner,
        [
            "gh",
            "run",
            "list",
            "--branch",
            "main",
            "--workflow",
            "tests",
            "--status",
            "in_progress",
            "--json",
            "databaseId",
        ],
        root,
    )
    if not passed:
        return "could not inspect staging runs"
    try:
        runs = json.loads(output)
    except json.JSONDecodeError:
        return "could not inspect staging runs"
    if not isinstance(runs, list):
        return "could not inspect staging runs"
    if runs:
        raise LimitSleep("staging", now + timedelta(seconds=600))
    return None


def _find_pr(runner: _RUNNER, root: Path, branch: str) -> tuple[int | None, str | None]:
    passed, output = _run(
        runner,
        ["gh", "pr", "list", "--head", branch, "--state", "all", "--json", "number,state"],
        root,
    )
    if not passed:
        return None, "could not inspect existing pull requests"
    try:
        values = json.loads(output)
    except json.JSONDecodeError:
        return None, "could not inspect existing pull requests"
    if not isinstance(values, list):
        return None, "could not inspect existing pull requests"
    for value in values:
        if isinstance(value, dict) and isinstance(value.get("number"), int):
            return value["number"], None
    return None, None


def _ci_status(runner: _RUNNER, root: Path, pr_number: int, now: datetime) -> None:
    passed, output = _run(runner, ["gh", "pr", "view", str(pr_number), "--json", "statusCheckRollup,state"], root)
    if not passed:
        raise RuntimeError("could not inspect pull request checks")
    try:
        value = json.loads(output)
    except json.JSONDecodeError as error:
        raise RuntimeError("could not inspect pull request checks") from error
    checks = value.get("statusCheckRollup") if isinstance(value, dict) else None
    if not isinstance(checks, list) or not checks:
        raise LimitSleep("ci", now + timedelta(seconds=120))
    pending = []
    failed = []
    for check in checks:
        if not isinstance(check, dict):
            pending.append("check")
            continue
        conclusion = str(check.get("conclusion") or "").upper()
        status = str(check.get("status") or "").upper()
        state = str(check.get("state") or "").upper()
        name = check.get("name") or check.get("context") or "check"
        if conclusion in {"SUCCESS", "NEUTRAL", "SKIPPED"} or state in {"SUCCESS", "NEUTRAL"}:
            continue
        if conclusion in {"FAILURE", "CANCELLED", "TIMED_OUT", "ERROR", "ACTION_REQUIRED"} or state in {
            "FAILURE",
            "ERROR",
            "CANCELLED",
        }:
            failed.append(str(name))
            continue
        if not conclusion or status not in {"COMPLETED", "SUCCESS", "FAILURE", "CANCELLED", "TIMED_OUT"}:
            pending.append(str(name))
        else:
            failed.append(str(name))
    if failed:
        raise RuntimeError("failed CI checks: " + ",".join(sorted(set(failed))))
    if pending:
        raise LimitSleep("ci", now + timedelta(seconds=120))


def deliver_handler(
    root: Path | None = None,
    *,
    runner: _RUNNER | None = None,
    gates: StationHandler | None = None,
    fetch_version: Callable[[str], dict[str, Any]] | None = None,
    now_fn: Callable[[], datetime] | None = None,
) -> StationHandler:
    """Return the station-9 delivery handler."""

    repository_root = Path(root) if root is not None else _repository_root()
    invoke = runner or _default_runner
    gate_handler = gates or __import__(
        "factory.stations.free_gates", fromlist=["free_gates_handler"]
    ).free_gates_handler(repository_root)
    version_fetch = fetch_version or _fetch_version
    clock = now_fn or (lambda: datetime.now(UTC))

    def handle(ticket, now: datetime) -> StationResult:
        payload = ticket.payload
        if payload.get("merge_to_main") is not True:
            return StationResult(False, "deliver", "ticket is not authorized to merge to main")
        workspace_value = payload.get("workspace")
        if not isinstance(workspace_value, str):
            return StationResult(False, "deliver", "missing payload key: workspace")
        workspace = Path(workspace_value).expanduser()
        safe_id = _safe_id(ticket.id)
        delivery_path = workspace / safe_id / "delivery.json"
        saved = _record(delivery_path) if delivery_path.exists() else None
        if saved is not None and saved.get("merged_sha") is not None:
            record = saved
            merged_sha = record["merged_sha"]
            pr_number = record.get("pr_number")
        else:
            tree = ticket_tree(payload, ticket.id, repository_root)
            if tree is None:
                return StationResult(False, "deliver", "ticket tree not found")
            paths, error = _changed_paths(invoke, tree)
            if error:
                return StationResult(False, "deliver", error)
            assert paths is not None
            has_pr = isinstance(saved.get("pr_number"), int) if saved is not None else False
            if not has_pr:
                if not paths:
                    return StationResult(False, "deliver", "empty diff against origin/main")
                config_path = repository_root / "factory/config/frozen.json"
                if not config_path.is_file():
                    config_path = Path(__file__).resolve().parents[1] / "config/frozen.json"
                blocked = _blocked_paths(paths, config_path)
                if blocked:
                    return StationResult(False, "deliver", "protected paths: " + ",".join(blocked))
            diff_hash, error = _diff_hash(invoke, tree, paths)
            if error or diff_hash is None:
                return StationResult(False, "deliver", error or "could not hash tree diff")
            if saved is not None and saved.get("diff_hash") != diff_hash:
                return StationResult(False, "deliver", "diff changed after delivery started")

            gate_result = gate_handler(ticket, now)
            if not gate_result.passed:
                return StationResult(False, "deliver", "free gates failed: " + _gate_tail(gate_result.output))
            staging_error = _staging_check(invoke, repository_root, now)
            if staging_error:
                return StationResult(False, "deliver", staging_error)

            branch = saved.get("branch") if saved else f"factory/{safe_id}"
            if not isinstance(branch, str) or branch != f"factory/{safe_id}":
                return StationResult(False, "deliver", "invalid delivery branch")
            record = {
                "diff_hash": diff_hash,
                "branch": branch,
                "pr_number": saved.get("pr_number") if saved else None,
                "merged_sha": saved.get("merged_sha") if saved else None,
                "merged_at": saved.get("merged_at") if saved else None,
            }

            if record["merged_sha"] is None:
                pr_number = record["pr_number"]
                if not isinstance(pr_number, int):
                    pr_number, error = _find_pr(invoke, repository_root, branch)
                    if error:
                        return StationResult(False, "deliver", error)
                if pr_number is None:
                    passed, output = _run(invoke, ["git", "switch", "-c", branch], tree)
                    if not passed and "already exists" not in output.lower():
                        return StationResult(False, "deliver", "could not create delivery branch")
                    passed, output = _run(invoke, ["git", "add", "--", *paths], tree)
                    if not passed:
                        return StationResult(False, "deliver", "could not stage delivery diff")
                    message = f"Factory: {ticket.scene} {_ticket_class(ticket)} fix ({ticket.id})"
                    passed, output = _run(invoke, ["git", "commit", "--only", "-m", message, "--", *paths], tree)
                    if not passed:
                        return StationResult(False, "deliver", "git commit failed: " + _one_line(output))
                    passed, output = _run(invoke, ["git", "fetch", "origin", "main"], tree)
                    if not passed:
                        return StationResult(False, "deliver", "git fetch failed: " + _one_line(output))
                    passed, output = _run(
                        invoke,
                        ["git", "rev-list", "--left-right", "--count", "HEAD...origin/main"],
                        tree,
                    )
                    if not passed:
                        return StationResult(False, "deliver", "could not inspect branch base")
                    try:
                        behind = int(output.split()[1])
                    except (IndexError, ValueError):
                        return StationResult(False, "deliver", "could not inspect branch base")
                    if behind:
                        passed, output = _run(invoke, ["git", "rebase", "origin/main"], tree)
                        if not passed:
                            _run(invoke, ["git", "rebase", "--abort"], tree)
                            return StationResult(False, "deliver", "git rebase failed: " + _one_line(output))
                    passed, output = _run(
                        invoke, ["git", "push", "--force-with-lease", "origin", f"{branch}:{branch}"], tree
                    )
                    if not passed:
                        return StationResult(False, "deliver", "git push failed: " + _one_line(output))
                    plan = payload.get("plan")
                    body_lines = [f"Ticket: {ticket.id}"]
                    if isinstance(plan, dict):
                        for key in ("reason", "kind"):
                            if key in plan:
                                body_lines.append(f"{key}: {_one_line(str(plan[key]))}")
                    body_lines.extend(("Free gates output:", _gate_tail(gate_result.output)))
                    passed, output = _run(
                        invoke,
                        [
                            "gh",
                            "pr",
                            "create",
                            "--base",
                            "main",
                            "--head",
                            branch,
                            "--title",
                            message,
                            "--body",
                            _redact("\n".join(body_lines)),
                        ],
                        repository_root,
                    )
                    if not passed:
                        return StationResult(False, "deliver", "could not create pull request")
                    pr_number = _pr_number(output)
                    if pr_number is None:
                        pr_number, _ = _find_pr(invoke, repository_root, branch)
                        if pr_number is None:
                            return StationResult(False, "deliver", "could not read pull request number")
                record["pr_number"] = pr_number
                _atomic_json_write(delivery_path, record)

                try:
                    _ci_status(invoke, repository_root, pr_number, now)
                except RuntimeError as error:
                    return StationResult(False, "deliver", _one_line(str(error)))
                staging_error = _staging_check(invoke, repository_root, now)
                if staging_error:
                    return StationResult(False, "deliver", staging_error)
                passed, output = _run(
                    invoke,
                    ["gh", "pr", "merge", str(pr_number), "--merge", "--delete-branch"],
                    repository_root,
                )
                if not passed:
                    return StationResult(False, "deliver", "could not merge pull request")
                passed, output = _run(
                    invoke, ["gh", "pr", "view", str(pr_number), "--json", "mergeCommit,state"], repository_root
                )
                if not passed:
                    return StationResult(False, "deliver", "could not read merge result")
                try:
                    merge = json.loads(output)
                except json.JSONDecodeError:
                    return StationResult(False, "deliver", "could not read merge result")
                merged_sha = merge.get("mergeCommit", {}).get("oid") if isinstance(merge, dict) else None
                if not isinstance(merged_sha, str) or not merged_sha or merge.get("state") != "MERGED":
                    return StationResult(False, "deliver", "pull request did not merge")
                record["merged_sha"] = merged_sha
                record["merged_at"] = clock().isoformat()
                _atomic_json_write(delivery_path, record)
                _run(invoke, ["git", "fetch", "--prune", "origin"], tree)
                branch_list_passed, branch_output = _run(invoke, ["git", "branch", "--list", branch], tree)
                if branch_list_passed and branch_output.strip():
                    _run(invoke, ["git", "branch", "-D", branch], tree)
            else:
                merged_sha = record["merged_sha"]
                pr_number = record.get("pr_number")

        merged_at_value = record.get("merged_at")
        if not isinstance(merged_at_value, str) or not isinstance(merged_sha, str):
            return StationResult(False, "deliver", "delivery record has no merge timestamp")
        try:
            merged_at = datetime.fromisoformat(merged_at_value.replace("Z", "+00:00"))
        except ValueError:
            return StationResult(False, "deliver", "delivery record has an invalid merge timestamp")
        current = clock()
        try:
            version = version_fetch(os.environ.get("E2E_API_BASE_URL", "").rstrip("/") + "/api/v1/version")
        except Exception:
            version = None
        if not (
            isinstance(version, dict)
            and version.get("channel") == "staging"
            and version.get("runtime") == "scene-v1"
            and version.get("sha") == merged_sha
        ):
            if current - merged_at < timedelta(minutes=45):
                raise LimitSleep("staging", current + timedelta(seconds=120))
            return StationResult(False, "deliver", f"staging did not reach {merged_sha} in 45 minutes")
        return StationResult(
            True,
            "deliver",
            f"delivered {ticket.id} at {merged_sha}",
            payload_updates={"merged_sha": merged_sha, "expected_sha": merged_sha, "pr_number": pr_number},
        )

    return handle

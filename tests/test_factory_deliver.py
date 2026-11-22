import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from factory.guard import LimitSleep
from factory.line import StationResult
from factory.stations.deliver import deliver_handler
from factory.tickets import Station, Ticket

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _fixture(tmp_path: Path) -> tuple[Path, Ticket, Path]:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "factory@example.test")
    _git(root, "config", "user.name", "Factory")
    (root / "README.md").write_text("base\n", encoding="utf-8")
    _git(root, "add", "--", "README.md")
    _git(root, "commit", "-qm", "base")
    bare = tmp_path / "origin.git"
    subprocess.run(["git", "clone", "-q", "--bare", str(root), str(bare)], check=True)
    _git(root, "remote", "add", "origin", str(bare))
    _git(root, "push", "-q", "origin", "main")
    workspace = tmp_path / "workspace"
    tree = workspace / "ticket" / "tree"
    tree.parent.mkdir(parents=True)
    _git(root, "worktree", "add", "--detach", str(tree), "HEAD")
    (tree / "README.md").write_text("factory fix\n", encoding="utf-8")
    ticket = Ticket(
        id="ticket",
        scene="1A",
        station=Station.DELIVER,
        token_budget=100,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload={"merge_to_main": True, "workspace": str(workspace), "plan": {"reason": "test", "kind": "fix"}},
    )
    return root, ticket, bare


class GhRunner:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.calls: list[list[str]] = []
        self.ci_calls = 0
        self.version_calls = 0

    def __call__(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        self.calls.append(argv)
        if argv[0] != "gh":
            result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
            return result.returncode, (result.stdout or "") + (result.stderr or "")
        if argv[1:4] == ["run", "list", "--branch"]:
            return 0, "[]"
        if argv[1:3] == ["pr", "list"]:
            return 0, "[]"
        if argv[1:3] == ["pr", "create"]:
            return 0, "https://github.example.test/pull/7\n"
        if argv[1:3] == ["pr", "merge"]:
            return 0, "merged\n"
        if argv[1:3] == ["pr", "view"] and "statusCheckRollup,state" in argv:
            self.ci_calls += 1
            conclusion = None if self.ci_calls == 1 else "SUCCESS"
            status = "IN_PROGRESS" if conclusion is None else "COMPLETED"
            return 0, json.dumps(
                {"state": "OPEN", "statusCheckRollup": [{"name": "tests", "status": status, "conclusion": conclusion}]}
            )
        if argv[1:3] == ["pr", "view"]:
            return 0, json.dumps({"state": "MERGED", "mergeCommit": {"oid": "a" * 40}})
        raise AssertionError(argv)


def _passing(_ticket, _now):
    return StationResult(True, "free_gates", "all free gates passed")


def test_refuses_without_merge_authorization(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    ticket.payload.pop("merge_to_main")
    runner = GhRunner(root)

    result = deliver_handler(root, runner=runner, gates=_passing)(ticket, NOW)

    assert not result.passed
    assert "authorized" in result.output
    assert runner.calls == []


def test_failing_gate_does_not_push_or_create_pr(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(root)

    def failing_gate(_ticket, _now):
        return StationResult(False, "ruff", "bad verdict")

    result = deliver_handler(root, runner=runner, gates=failing_gate)(ticket, NOW)

    assert not result.passed and result.output == "free gates failed: bad verdict"
    assert not any(call[:2] == ["git", "push"] or call[0:3] == ["gh", "pr", "create"] for call in runner.calls)


def test_delivery_output_does_not_expose_environment_secret(tmp_path: Path, monkeypatch) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    secret = "factory-test-secret-token"
    monkeypatch.setenv("FACTORY_TEST_SECRET", secret)
    runner = GhRunner(root)

    def failing_gate(_ticket, _now):
        return StationResult(False, "ruff", f"verdict included {secret}")

    result = deliver_handler(root, runner=runner, gates=failing_gate)(ticket, NOW)

    assert secret not in result.output


def test_happy_path_is_idempotent_and_waits_for_staging(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(root)
    versions = [
        {"channel": "staging", "runtime": "scene-v1", "sha": "old"},
        {"channel": "staging", "runtime": "scene-v1", "sha": "a" * 40},
    ]

    def fetch(_url):
        return versions.pop(0)

    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="ci"):
        handler(ticket, NOW)
    assert (Path(ticket.payload["workspace"]) / "ticket" / "delivery.json").exists()
    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="staging"):
        handler(ticket, NOW)
    result = handler(ticket, NOW)

    assert result.passed
    assert result.payload_updates == {"merged_sha": "a" * 40, "expected_sha": "a" * 40, "pr_number": 7}
    assert sum(call[0:3] == ["gh", "pr", "create"] for call in runner.calls) == 1
    merge = next(call for call in runner.calls if call[:3] == ["gh", "pr", "merge"])
    assert "--merge" in merge and "--delete-branch" in merge
    assert "--squash" not in merge and "--rebase" not in merge


def test_failed_ci_returns_check_names_only(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    base_runner = GhRunner(root)

    def runner(argv: list[str], cwd: Path) -> tuple[int, str]:
        if argv[:3] == ["gh", "pr", "view"] and "statusCheckRollup,state" in argv:
            return 0, json.dumps(
                {
                    "state": "OPEN",
                    "statusCheckRollup": [
                        {"name": "tests", "status": "COMPLETED", "conclusion": "FAILURE"},
                        {"name": "lint", "status": "COMPLETED", "conclusion": "CANCELLED"},
                    ],
                }
            )
        return base_runner(argv, cwd)

    result = deliver_handler(root, runner=runner, gates=_passing)(ticket, NOW)

    assert result == StationResult(False, "deliver", "failed CI checks: lint,tests")


def test_staging_timeout_is_a_failure_after_forty_five_minutes(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(root)
    versions = [{"channel": "staging", "runtime": "scene-v1", "sha": "old"}] * 2

    def fetch(_url):
        return versions.pop() if versions else {"channel": "staging", "runtime": "scene-v1", "sha": "old"}

    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="ci"):
        handler(ticket, NOW)
    with pytest.raises(LimitSleep, match="staging"):
        handler(ticket, NOW)
    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    record["merged_at"] = (NOW - timedelta(minutes=46)).isoformat()
    record_path.write_text(json.dumps(record), encoding="utf-8")

    result = handler(ticket, NOW)

    assert result == StationResult(False, "deliver", f"staging did not reach {'a' * 40} in 45 minutes")


def test_fresh_staged_lock_sleeps_before_github_work(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    lock = root / "factory/state/staged_run.lock"
    lock.parent.mkdir(parents=True)
    lock.write_text("other\n", encoding="utf-8")
    runner = GhRunner(root)

    with pytest.raises(LimitSleep, match="staging"):
        deliver_handler(root, runner=runner, gates=_passing)(ticket, NOW)
    assert not any(call[0] == "gh" for call in runner.calls)


def test_stale_record_rejects_changed_diff(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(root)
    handler = deliver_handler(root, runner=runner, gates=_passing)
    with pytest.raises(LimitSleep):
        handler(ticket, NOW)
    tree = Path(ticket.payload["workspace"]) / "ticket" / "tree"
    (tree / "README.md").write_text("changed again\n", encoding="utf-8")

    result = handler(ticket, NOW)

    assert not result.passed
    assert result.output == "diff changed after delivery started"

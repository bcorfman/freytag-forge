import json
import subprocess
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from factory.guard import LimitSleep
from factory.line import StationResult
from factory.stations.deliver import _changed_paths, _default_runner, _diff_hash, deliver_handler
from factory.tickets import Station, Ticket

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def _local_runner(argv: list[str], cwd: Path) -> tuple[int, str]:
    result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
    return result.returncode, (result.stdout or "") + (result.stderr or "")


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
    def __init__(
        self,
        root: Path,
        *,
        create_output: str = "https://github.example.test/pull/7\n",
        fallback_pr_list: str = "[]",
        merge_code: int = 0,
        initial_pr_state: str = "OPEN",
        merged_pr_state: str = "MERGED",
    ) -> None:
        self.root = root
        self.calls: list[list[str]] = []
        self.ci_calls = 0
        self.version_calls = 0
        self.create_output = create_output
        self.fallback_pr_list = fallback_pr_list
        self.create_called = False
        self.merge_code = merge_code
        self.pr_state = initial_pr_state
        self.merged_pr_state = merged_pr_state

    def __call__(self, argv: list[str], cwd: Path) -> tuple[int, str]:
        self.calls.append(argv)
        if argv[0] != "gh":
            result = subprocess.run(argv, cwd=cwd, capture_output=True, text=True)
            return result.returncode, (result.stdout or "") + (result.stderr or "")
        if argv[1:4] == ["run", "list", "--branch"]:
            return 0, "[]"
        if argv[1:3] == ["pr", "list"]:
            return 0, self.fallback_pr_list if self.create_called else "[]"
        if argv[1:3] == ["pr", "create"]:
            self.create_called = True
            return 0, self.create_output
        if argv[1:3] == ["pr", "merge"]:
            self.pr_state = self.merged_pr_state
            return self.merge_code, "merged\n"
        if argv[1:3] == ["pr", "view"] and "statusCheckRollup,state" in argv:
            self.ci_calls += 1
            conclusion = None if self.ci_calls == 1 else "SUCCESS"
            status = "IN_PROGRESS" if conclusion is None else "COMPLETED"
            return 0, json.dumps(
                {"state": "OPEN", "statusCheckRollup": [{"name": "tests", "status": status, "conclusion": conclusion}]}
            )
        if argv[1:3] == ["pr", "view"] and "mergeCommit,state" in argv:
            merge_commit = {"oid": "a" * 40} if self.pr_state == "MERGED" else None
            return 0, json.dumps({"state": self.pr_state, "mergeCommit": merge_commit})
        if argv[1:3] == ["pr", "view"]:
            return 0, json.dumps({"state": "MERGED", "mergeCommit": {"oid": "a" * 40}})
        raise AssertionError(argv)


def _passing(_ticket, _now):
    return StationResult(True, "free_gates", "all free gates passed")


def test_default_runner_returns_stdout_only_on_success(tmp_path: Path) -> None:
    executable = tmp_path / "fake-command"
    executable.write_text(
        "#!/bin/sh\nprintf '%s\\n' '{\"ok\": true}'\nprintf '%s\\n' 'hint: use --help' >&2\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)

    code, output = _default_runner([str(executable)], tmp_path)

    assert code == 0
    assert json.loads(output) == {"ok": True}
    assert output == '{"ok": true}\n'


def test_default_runner_includes_stderr_on_failure(tmp_path: Path) -> None:
    executable = tmp_path / "fake-command"
    executable.write_text(
        "#!/bin/sh\nprintf '%s\\n' '{\"ok\": false}'\nprintf '%s\\n' 'hint: command failed' >&2\nexit 1\n",
        encoding="utf-8",
    )
    executable.chmod(0o755)

    code, output = _default_runner([str(executable)], tmp_path)

    assert code == 1
    assert output == '{"ok": false}\nhint: command failed\n'


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


def test_merge_command_failing_after_the_merge_still_succeeds(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(root, merge_code=1)
    versions = [
        {"channel": "staging", "runtime": "scene-v1", "sha": "old"},
        {"channel": "staging", "runtime": "scene-v1", "sha": "a" * 40},
    ]

    def fetch(_url):
        return versions.pop(0)

    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="ci"):
        handler(ticket, NOW)
    with pytest.raises(LimitSleep, match="staging"):
        handler(ticket, NOW)

    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["merged_sha"] == "a" * 40
    assert record["merged_at"] == NOW.isoformat()
    assert any(call[:3] == ["gh", "pr", "merge"] for call in runner.calls)

    result = handler(ticket, NOW)

    assert result.passed
    assert result.payload_updates == {"merged_sha": "a" * 40, "expected_sha": "a" * 40, "pr_number": 7}


def test_merge_command_failing_and_not_merged_fails(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(root, merge_code=1, merged_pr_state="OPEN")

    handler = deliver_handler(root, runner=runner, gates=_passing, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="ci"):
        handler(ticket, NOW)

    result = handler(ticket, NOW)

    assert result == StationResult(False, "deliver", "could not merge pull request")
    assert any(call[:3] == ["gh", "pr", "merge"] for call in runner.calls)
    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["merged_sha"] is None


def test_resume_with_already_merged_pr_skips_ci_and_merge(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record_path.write_text(
        json.dumps(
            {
                "diff_hash": "obsolete",
                "branch": "factory/ticket",
                "pr_number": 7,
                "merged_sha": None,
                "merged_at": None,
            }
        ),
        encoding="utf-8",
    )
    runner = GhRunner(root, initial_pr_state="MERGED")
    versions = [
        {"channel": "staging", "runtime": "scene-v1", "sha": "old"},
        {"channel": "staging", "runtime": "scene-v1", "sha": "a" * 40},
    ]

    def fetch(_url):
        return versions.pop(0)

    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="staging"):
        handler(ticket, NOW)

    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["merged_sha"] == "a" * 40
    assert record["merged_at"] == NOW.isoformat()
    assert not any("statusCheckRollup,state" in call for call in runner.calls)
    assert not any(call[:3] == ["gh", "pr", "merge"] for call in runner.calls)

    result = handler(ticket, NOW)

    assert result.passed
    assert result.payload_updates == {"merged_sha": "a" * 40, "expected_sha": "a" * 40, "pr_number": 7}


def test_closed_pr_fails(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record_path.write_text(
        json.dumps({"branch": "factory/ticket", "pr_number": 7, "merged_sha": None, "merged_at": None}),
        encoding="utf-8",
    )
    runner = GhRunner(root, initial_pr_state="CLOSED")

    result = deliver_handler(root, runner=runner, gates=_passing)(ticket, NOW)

    assert result == StationResult(False, "deliver", "pull request closed without merging")
    assert not any("statusCheckRollup,state" in call for call in runner.calls)
    assert not any(call[:3] == ["gh", "pr", "merge"] for call in runner.calls)


def test_pr_number_read_from_url_followed_by_notice_lines(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(
        root,
        create_output="https://github.example.test/pull/810\n\nnotice one\nnotice two\n",
    )
    versions = [
        {"channel": "staging", "runtime": "scene-v1", "sha": "old"},
        {"channel": "staging", "runtime": "scene-v1", "sha": "a" * 40},
    ]

    def fetch(_url):
        return versions.pop(0)

    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="ci"):
        handler(ticket, NOW)

    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["pr_number"] == 810


def test_pr_number_falls_back_to_branch_lookup(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(
        root, create_output="created pull request\n", fallback_pr_list='[{"number": 811, "state": "OPEN"}]'
    )
    versions = [
        {"channel": "staging", "runtime": "scene-v1", "sha": "old"},
        {"channel": "staging", "runtime": "scene-v1", "sha": "a" * 40},
    ]

    def fetch(_url):
        return versions.pop(0)

    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="ci"):
        handler(ticket, NOW)

    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record = json.loads(record_path.read_text(encoding="utf-8"))
    assert record["pr_number"] == 811


def test_pr_number_unreadable_everywhere_fails(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    runner = GhRunner(root, create_output="created pull request\n")

    result = deliver_handler(root, runner=runner, gates=_passing)(ticket, NOW)

    assert result == StationResult(False, "deliver", "could not read pull request number")
    assert not any(call[:3] == ["gh", "pr", "merge"] for call in runner.calls)


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


def test_changed_content_after_start_still_fails(tmp_path: Path) -> None:
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


def test_resume_after_merge_waits_for_deploy_without_rediffing(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    tree = Path(ticket.payload["workspace"]) / "ticket" / "tree"
    _git(tree, "add", "--", "README.md")
    _git(tree, "commit", "-qm", "merged fix")
    merged_sha = _git(tree, "rev-parse", "HEAD")
    _git(tree, "push", "-q", "origin", "HEAD:main")
    _git(tree, "fetch", "-q", "origin", "main")
    record_path = Path(ticket.payload["workspace"]) / "ticket" / "delivery.json"
    record_path.write_text(
        json.dumps(
            {
                "diff_hash": "obsolete",
                "branch": "factory/ticket",
                "pr_number": 7,
                "merged_sha": merged_sha,
                "merged_at": NOW.isoformat(),
            }
        ),
        encoding="utf-8",
    )
    runner = GhRunner(root)
    versions = [
        {"channel": "staging", "runtime": "scene-v1", "sha": "old"},
        {"channel": "staging", "runtime": "scene-v1", "sha": merged_sha},
    ]

    def fetch(_url):
        return versions.pop(0)

    handler = deliver_handler(root, runner=runner, gates=_passing, fetch_version=fetch, now_fn=lambda: NOW)
    with pytest.raises(LimitSleep, match="staging"):
        handler(ticket, NOW)
    result = handler(ticket, NOW)

    assert result.passed
    assert result.payload_updates == {"merged_sha": merged_sha, "expected_sha": merged_sha, "pr_number": 7}
    assert runner.calls == []


def test_behind_main_rebases_after_commit(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    (root / "unrelated.txt").write_text("main moved\n", encoding="utf-8")
    _git(root, "add", "--", "unrelated.txt")
    _git(root, "commit", "-qm", "unrelated main change")
    _git(root, "push", "-q", "origin", "main")
    runner = GhRunner(root)

    with pytest.raises(LimitSleep, match="ci"):
        deliver_handler(root, runner=runner, gates=_passing, fetch_version=lambda _url: {}, now_fn=lambda: NOW)(
            ticket, NOW
        )

    tree = Path(ticket.payload["workspace"]) / "ticket" / "tree"
    assert _git(tree, "show", "HEAD:README.md") == "factory fix"
    assert _git(tree, "show", "HEAD:unrelated.txt") == "main moved"
    assert sum(call[:3] == ["git", "rebase", "origin/main"] for call in runner.calls) == 1
    assert sum(call[:3] == ["gh", "pr", "create"] for call in runner.calls) == 1


def test_rebase_conflict_fails_with_git_output(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    (root / "README.md").write_text("conflicting main change\n", encoding="utf-8")
    _git(root, "add", "--", "README.md")
    _git(root, "commit", "-qm", "conflicting main change")
    _git(root, "push", "-q", "origin", "main")
    runner = GhRunner(root)

    result = deliver_handler(root, runner=runner, gates=_passing)(ticket, NOW)

    assert not result.passed
    assert "git rebase failed:" in result.output
    tree = Path(ticket.payload["workspace"]) / "ticket" / "tree"
    assert _git(tree, "status", "--porcelain") == ""
    assert ["git", "rebase", "--abort"] in runner.calls
    assert not any(call[:3] == ["git", "push", "--force-with-lease"] for call in runner.calls)
    assert not any(call[:3] == ["gh", "pr", "create"] for call in runner.calls)


def test_diff_hash_is_stable_across_commit_and_main_advance(tmp_path: Path) -> None:
    root, ticket, _bare = _fixture(tmp_path)
    tree = Path(ticket.payload["workspace"]) / "ticket" / "tree"
    paths_before, error = _changed_paths(_local_runner, tree)
    assert error is None and paths_before is not None
    hash_before, error = _diff_hash(_local_runner, tree, paths_before)
    assert error is None and hash_before is not None
    runner = GhRunner(root)

    with pytest.raises(LimitSleep, match="ci"):
        deliver_handler(root, runner=runner, gates=_passing, fetch_version=lambda _url: {}, now_fn=lambda: NOW)(
            ticket, NOW
        )

    paths_after_commit, error = _changed_paths(_local_runner, tree)
    assert error is None and paths_after_commit is not None
    hash_after_commit, error = _diff_hash(_local_runner, tree, paths_after_commit)
    assert error is None and hash_after_commit is not None
    assert paths_after_commit == paths_before
    assert hash_after_commit == hash_before

    (root / "unrelated.txt").write_text("main advanced\n", encoding="utf-8")
    _git(root, "add", "--", "unrelated.txt")
    _git(root, "commit", "-qm", "unrelated main change")
    _git(root, "push", "-q", "origin", "main")
    _git(tree, "fetch", "-q", "origin", "main")
    paths_after_main, error = _changed_paths(_local_runner, tree)
    assert error is None and paths_after_main is not None
    hash_after_main, error = _diff_hash(_local_runner, tree, paths_after_main)
    assert error is None and hash_after_main is not None
    assert paths_after_main == paths_before
    assert hash_after_main == hash_before

    with pytest.raises(LimitSleep, match="staging"):
        deliver_handler(root, runner=runner, gates=_passing, fetch_version=lambda _url: {}, now_fn=lambda: NOW)(
            ticket, NOW
        )

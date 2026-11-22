import json
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest

from factory.guard import LimitSleep, ModelNotAllowed, SpendLedger
from factory.stations.fun_review import (
    FUN_REVIEW_BRIEF,
    ReviewReply,
    default_reviewer,
    fun_review_handler,
)
from factory.tickets import Station, Ticket

ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return completed.stdout


def _runner(argv: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _fixture(tmp_path: Path, *, changed: bool = True, content: str = "fixed text\n") -> tuple[Path, Path, Ticket]:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Factory Test")
    (root / "scene.txt").write_text("original text\n", encoding="utf-8")
    (root / "criteria.txt").write_text("Keep the repair concrete and give the player a next move.", encoding="utf-8")
    _git(root, "add", "scene.txt", "criteria.txt")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")

    workspace = tmp_path / "workspace"
    tree = workspace / "review-ticket" / "tree"
    tree.parent.mkdir(parents=True)
    _git(root, "worktree", "add", "-q", "--detach", str(tree), "HEAD")
    if changed:
        (tree / "scene.txt").write_text(content, encoding="utf-8")
    ticket = Ticket(
        id="review-ticket",
        scene="scene-1",
        station=Station.FUN_REVIEW,
        token_budget=1000,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload={
            "merge_to_main": True,
            "workspace": str(workspace),
            "review_criteria_path": "criteria.txt",
            "failing_turns": [{"key": "turn-1", "player_input": "look around", "narration": "The scene stops here."}],
        },
    )
    return root, tree, ticket


def _reply(
    verdict: str = "pass",
    *,
    checks: dict | None = None,
    reasons: str = "It gives the player a clear next move.",
    tokens: int = 7,
) -> ReviewReply:
    return ReviewReply(
        json.dumps(
            {
                "verdict": verdict,
                "checks": checks or {"fits_scene": True, "gives_a_reason_to_act": True, "keeps_pace": True},
                "reasons": reasons,
            }
        ),
        tokens,
    )


def _reviewer(responses: list[ReviewReply], prompts: list[str]):
    def review(_ticket, prompt: str, _now: datetime) -> ReviewReply:
        prompts.append(prompt)
        return responses.pop(0)

    return review


def test_pass_writes_record_and_includes_the_complete_packet(tmp_path: Path) -> None:
    root, _tree, ticket = _fixture(tmp_path)
    prompts: list[str] = []
    handler = fun_review_handler(root, reviewer=_reviewer([_reply()], prompts), runner=_runner)

    result = handler(ticket, NOW)

    assert result.passed
    assert result.tokens == 7
    assert result.payload_updates is not None
    assert result.payload_updates["fun_review"]["verdict"] == "pass"
    assert result.payload_updates["fun_review"]["reasons"] == "It gives the player a clear next move."
    assert isinstance(result.payload_updates["fun_review"]["diff_hash"], str)
    assert len(prompts) == 1
    assert prompts[0].startswith(FUN_REVIEW_BRIEF)
    assert "Scene: scene-1" in prompts[0]
    assert "Keep the repair concrete" in prompts[0]
    assert '"key": "turn-1"' in prompts[0]
    assert "fixed text" in prompts[0]
    record = json.loads((tmp_path / "workspace/review-ticket/review.json").read_text(encoding="utf-8"))
    assert record["diff_hash"] == result.payload_updates["fun_review"]["diff_hash"]
    assert record["verdict"] == "pass"


def test_block_and_false_check_are_failures_with_tokens(tmp_path: Path) -> None:
    root, _tree, ticket = _fixture(tmp_path)
    blocked = fun_review_handler(
        root,
        reviewer=lambda *_: _reply("block", reasons="The repair is filler.", tokens=9),
        runner=_runner,
    )(ticket, NOW)
    assert not blocked.passed
    assert blocked.output == "fun review blocked the fix: The repair is filler."
    assert blocked.tokens == 9

    root, _tree, ticket = _fixture(tmp_path / "false")
    result = fun_review_handler(
        root,
        reviewer=lambda *_: _reply(checks={"fits_scene": True, "gives_a_reason_to_act": False, "keeps_pace": True}),
        runner=_runner,
    )(ticket, NOW)
    assert not result.passed
    assert result.output.startswith("fun review blocked the fix:")


def test_invalid_replies_retry_once_and_tokens_are_summed(tmp_path: Path) -> None:
    root, _tree, ticket = _fixture(tmp_path)
    prompts: list[str] = []
    result = fun_review_handler(
        root,
        reviewer=_reviewer([ReviewReply("garbage", 2), ReviewReply("still bad", 3)], prompts),
        runner=_runner,
    )(ticket, NOW)
    assert not result.passed
    assert result.output == "no usable verdict from the reviewer"
    assert result.tokens == 5
    assert len(prompts) == 2
    assert prompts[1].endswith("Your last reply was not valid. Reply with the JSON object only.")
    assert not (tmp_path / "workspace/review-ticket/review.json").exists()

    root, _tree, ticket = _fixture(tmp_path / "valid")
    prompts = []
    result = fun_review_handler(
        root,
        reviewer=_reviewer([ReviewReply("garbage", 2), _reply(tokens=4)], prompts),
        runner=_runner,
    )(ticket, NOW)
    assert result.passed and result.tokens == 6


def test_idempotency_reuses_pass_and_block_and_reviews_changed_content(tmp_path: Path) -> None:
    root, tree, ticket = _fixture(tmp_path)
    prompts: list[str] = []
    responses = [_reply(), _reply(reasons="The changed repair still gives a move.")]
    handler = fun_review_handler(root, reviewer=_reviewer(responses, prompts), runner=_runner)
    first = handler(ticket, NOW)
    second = fun_review_handler(root, reviewer=_reviewer(responses, prompts), runner=_runner)(ticket, NOW)
    assert first.passed and second.passed and len(prompts) == 1

    (tree / "scene.txt").write_text("changed repair text\n", encoding="utf-8")
    third = handler(ticket, NOW)
    assert third.passed and len(prompts) == 2

    root, tree, ticket = _fixture(tmp_path / "blocked")
    calls: list[str] = []
    handler = fun_review_handler(
        root,
        reviewer=_reviewer([_reply("block", reasons="No reason to act.")], calls),
        runner=_runner,
    )
    first = handler(ticket, NOW)
    second = handler(ticket, NOW)
    assert not first.passed and not second.passed and len(calls) == 1
    assert second.output == first.output and second.tokens == 0
    assert tree.is_dir()


def test_huge_diff_is_cut_and_validation_errors_do_not_review(tmp_path: Path) -> None:
    root, _tree, ticket = _fixture(tmp_path, content="x" * 22000)
    prompts: list[str] = []
    result = fun_review_handler(root, reviewer=_reviewer([_reply()], prompts), runner=_runner)(ticket, NOW)
    assert result.passed
    assert "[diff cut at 16000 characters]" in prompts[0]
    assert prompts[0].endswith("[diff cut at 16000 characters]")

    calls: list[str] = []
    for payload, message in (
        ({}, "ticket is not authorized to merge to main"),
        ({"merge_to_main": True}, "missing payload key: workspace"),
        ({"merge_to_main": True, "workspace": str(tmp_path / "missing")}, "ticket tree not found"),
    ):
        invalid = Ticket("invalid", "scene", Station.FUN_REVIEW, 100, NOW.isoformat(), NOW.isoformat(), payload=payload)
        result = fun_review_handler(root, reviewer=_reviewer([_reply()], calls), runner=_runner)(invalid, NOW)
        assert not result.passed and result.output == message
    empty_root, _tree, empty_ticket = _fixture(tmp_path / "empty", changed=False)
    result = fun_review_handler(empty_root, reviewer=_reviewer([_reply()], calls), runner=_runner)(empty_ticket, NOW)
    assert not result.passed and result.output == "empty diff against origin/main"
    assert calls == []


def test_limit_sleep_propagates_without_a_record(tmp_path: Path) -> None:
    root, _tree, ticket = _fixture(tmp_path)
    error = LimitSleep("claude_code", NOW)

    def reviewer(*_args):
        raise error

    with pytest.raises(LimitSleep) as caught:
        fun_review_handler(root, reviewer=reviewer, runner=_runner)(ticket, NOW)
    assert caught.value is error
    assert not (tmp_path / "workspace/review-ticket/review.json").exists()


def test_default_reviewer_uses_fun_review_pin_and_rejects_sonnet(tmp_path: Path) -> None:
    config_dir = tmp_path / "factory/config"
    config_dir.mkdir(parents=True)
    for name in ("allowlist.json", "factory.json"):
        shutil.copy2(ROOT / "factory/config" / name, config_dir / name)
    stream = (
        json.dumps(
            {"type": "assistant", "message": {"content": [{"type": "text", "text": "review"}]}},
        )
        + "\n"
        + json.dumps(
            {
                "type": "result",
                "result": json.dumps(
                    {
                        "verdict": "pass",
                        "checks": {
                            "fits_scene": True,
                            "gives_a_reason_to_act": True,
                            "keeps_pace": True,
                        },
                        "reasons": "Good.",
                    }
                ),
                "usage": {"input_tokens": 2, "output_tokens": 3},
                "total_cost_usd": 0.01,
            }
        )
    )
    calls: list[list[str]] = []

    def run(argv, **_kwargs):
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, stream, "")

    ticket = Ticket("review", "scene", Station.FUN_REVIEW, 100, NOW.isoformat(), NOW.isoformat())
    reviewer = default_reviewer(tmp_path, run=run)
    result = reviewer(ticket, "prompt", NOW)
    assert '"verdict": "pass"' in result.text
    assert result.tokens == 5
    usage = SpendLedger(tmp_path / "factory/state/ledger.jsonl")._read()
    assert len(usage) == 1 and usage[0].station == "fun_review" and usage[0].cost_kind == "subscription"
    assert calls

    with pytest.raises(ModelNotAllowed):
        default_reviewer(tmp_path, run=run, model_id="claude-sonnet-5-5")(ticket, "prompt", NOW)
    assert len(calls) == 1
    allowlist = json.loads((ROOT / "factory/config/allowlist.json").read_text(encoding="utf-8"))
    assert allowlist["stations"]["fun_review"] == [
        {"model_id": "claude-opus-5-5", "effort": "medium", "provider": "claude_code"}
    ]

import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from factory.line import MAX_FUN_ROUNDS, FactoryLine, StationResult
from factory.state import FactoryState
from factory.stations.fun_review import (
    FUN_REVIEW_BRIEF,
    FUN_REVIEW_CHECKS,
    ReviewReply,
    fun_review_handler,
)
from factory.stations.planner import PLANNER_BRIEF
from factory.tickets import LadderRung, Station, Status, Ticket, TicketQueue

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True)


def _review_fixture(tmp_path: Path) -> tuple[Path, Path, Ticket]:
    root = tmp_path / "repo"
    root.mkdir(parents=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.invalid")
    _git(root, "config", "user.name", "Factory Test")
    (root / "scene.txt").write_text("original text\n", encoding="utf-8")
    _git(root, "add", "scene.txt")
    _git(root, "commit", "-q", "-m", "base")
    _git(root, "update-ref", "refs/remotes/origin/main", "HEAD")

    workspace = tmp_path / "workspace"
    tree = workspace / "fun-ticket" / "tree"
    tree.parent.mkdir(parents=True)
    _git(root, "worktree", "add", "-q", "--detach", str(tree), "HEAD")
    (tree / "scene.txt").write_text("delightful repair\n", encoding="utf-8")
    ticket = Ticket(
        id="fun-ticket",
        scene="scene-1",
        station=Station.FUN_REVIEW,
        token_budget=1000,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload={"merge_to_main": True, "workspace": str(workspace), "plan": {"kind": "set_text"}},
    )
    return root, tree, ticket


def _runner(argv: list[str], cwd: Path) -> tuple[int, str]:
    completed = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, check=False)
    return completed.returncode, (completed.stdout or "") + (completed.stderr or "")


def _reply(*, checks: dict[str, bool] | None = None, fun_advice: str = "") -> ReviewReply:
    return ReviewReply(
        json.dumps(
            {
                "verdict": "block" if checks and checks.get("delights_the_player") is False else "pass",
                "checks": checks or {key: True for key in FUN_REVIEW_CHECKS},
                "reasons": "Add a memorable payoff for the player.",
                "fun_advice": fun_advice,
            }
        ),
        4,
    )


def _reviewer(reply: ReviewReply):
    def review(_ticket, _prompt: str, _now: datetime) -> ReviewReply:
        return reply

    return review


def _package_loader(_root: Path):
    return SimpleNamespace(scenes=())


def test_fun_review_contract_has_eighth_delight_check_and_all_true_passes(tmp_path: Path) -> None:
    assert FUN_REVIEW_CHECKS[-1] == "delights_the_player"
    assert "Answer these eight yes/no questions" in FUN_REVIEW_BRIEF
    assert all(key in FUN_REVIEW_BRIEF for key in FUN_REVIEW_CHECKS)
    assert '"delights_the_player": true' in FUN_REVIEW_BRIEF
    assert '"fun_advice": "empty on pass; one or two plain sentences on block"' in FUN_REVIEW_BRIEF
    assert "Keep fun_advice to 300 characters or fewer." in FUN_REVIEW_BRIEF
    assert "\n\nReply with ONE JSON object and nothing else:" in FUN_REVIEW_BRIEF

    root, _tree, ticket = _review_fixture(tmp_path)
    result = fun_review_handler(
        root,
        reviewer=_reviewer(_reply(fun_advice="")),
        runner=_runner,
        package_loader=_package_loader,
    )(ticket, NOW)

    assert result.passed
    assert result.payload_updates["fun_review"]["verdict"] == "pass"
    assert result.payload_updates["fun_review"]["failed_checks"] == []


def test_delight_check_false_blocks_with_fun_advice_payload(tmp_path: Path) -> None:
    root, _tree, ticket = _review_fixture(tmp_path)
    checks = {key: True for key in FUN_REVIEW_CHECKS}
    checks["delights_the_player"] = False
    result = fun_review_handler(
        root,
        reviewer=_reviewer(_reply(checks=checks, fun_advice="Add a small twist that the player will remember.")),
        runner=_runner,
        package_loader=_package_loader,
    )(ticket, NOW)

    assert not result.passed
    assert result.payload_updates["fun_review"] == {
        "verdict": "block",
        "diff_hash": result.payload_updates["fun_review"]["diff_hash"],
        "reasons": "delights_the_player: Add a memorable payoff for the player.",
        "fun_advice": "Add a small twist that the player will remember.",
        "failed_checks": ["delights_the_player"],
        "plan": {"kind": "set_text"},
    }


def test_old_seven_check_reply_blocks_and_saved_block_reuses_payload(tmp_path: Path) -> None:
    root, _tree, ticket = _review_fixture(tmp_path)
    old_checks = {key: True for key in FUN_REVIEW_CHECKS[:-1]}
    first = fun_review_handler(
        root,
        reviewer=_reviewer(_reply(checks=old_checks, fun_advice="Try a memorable payoff.")),
        runner=_runner,
        package_loader=_package_loader,
    )(ticket, NOW)

    assert not first.passed
    assert first.payload_updates["fun_review"]["verdict"] == "block"
    assert "delights_the_player" in first.output

    second = fun_review_handler(
        root,
        reviewer=lambda *_: (_ for _ in ()).throw(AssertionError("saved review should be reused")),
        runner=_runner,
        package_loader=_package_loader,
    )(ticket, NOW)
    assert second.payload_updates == first.payload_updates
    assert second.tokens == 0


def _line_ticket(ticket_id: str, *, payload: dict | None = None) -> Ticket:
    timestamp = NOW.isoformat()
    return Ticket(
        id=ticket_id,
        scene="scene-1",
        station=Station.FUN_REVIEW,
        token_budget=1000,
        created_at=timestamp,
        updated_at=timestamp,
        payload={"merge_to_main": True, "plan": {"kind": "set_text"}, **(payload or {})},
    )


def _line(tmp_path: Path, ticket: Ticket, result: StationResult) -> tuple[FactoryLine, TicketQueue]:
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        handlers={Station.FUN_REVIEW: lambda _ticket, _now: result},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    return line, queue


def _blocked_result(fun_advice: str = "Make the payoff more memorable.") -> StationResult:
    return StationResult(
        False,
        "fun_review",
        "fun review blocked the fix: delights_the_player: repair lacks a payoff",
        payload_updates={
            "fun_review": {
                "verdict": "block",
                "diff_hash": "hash",
                "reasons": "delights_the_player: repair lacks a payoff",
                "fun_advice": fun_advice,
                "failed_checks": ["delights_the_player"],
                "plan": {"kind": "set_text", "reason": "blocked plan"},
            }
        },
    )


def test_real_fun_block_returns_to_wiring_with_feedback_and_clears_old_plan(tmp_path: Path) -> None:
    ticket = _line_ticket(
        "fun-retry",
        payload={"probe_feedback": "stale probe", "fun_review": {"verdict": "block"}, "fun_rounds": 0},
    )
    line, queue = _line(tmp_path, ticket, _blocked_result())

    assert line.step(NOW).kind == "fun_blocked"
    saved = queue.get(ticket.id)
    assert saved.station is Station.WIRING
    assert saved.status is Status.QUEUED
    assert saved.attempts == 0
    assert saved.ladder_rung is LadderRung.LUNA_RETRY
    assert saved.provider is None
    assert saved.sleep_until is None
    assert saved.return_after is None
    assert saved.payload["fun_rounds"] == 1
    assert saved.payload["feedback_plan"] == ticket.payload["plan"]
    assert saved.payload["fun_feedback"] == (
        "Failed checks: delights_the_player\n"
        "Reasons: delights_the_player: repair lacks a payoff\n"
        "fun_advice: Make the payoff more memorable."
    )
    assert "Answer these eight" not in saved.payload["fun_feedback"]
    assert "delights_the_player:" not in saved.payload["fun_feedback"].splitlines()[0]
    assert saved.payload["fun_history"] == [
        {
            "plan": ticket.payload["plan"],
            "reasons": "delights_the_player: repair lacks a payoff",
            "fun_advice": "Make the payoff more memorable.",
            "failed_checks": ["delights_the_player"],
        }
    ]
    assert "plan" not in saved.payload
    assert "probe_feedback" not in saved.payload
    assert "fun_review" not in saved.payload


def test_second_fun_block_uses_failure_ladder_and_preserves_history(tmp_path: Path) -> None:
    ticket = _line_ticket("fun-second", payload={"fun_rounds": MAX_FUN_ROUNDS - 1})
    line, queue = _line(tmp_path, ticket, _blocked_result())

    assert line.step(NOW).kind == "failed_attempt"
    saved = queue.get(ticket.id)
    assert saved.status is Status.SET_ASIDE
    assert saved.failures[-1].check == "fun_review"
    assert saved.payload["fun_rounds"] == MAX_FUN_ROUNDS
    assert saved.payload["fun_history"] == [
        {
            "plan": ticket.payload["plan"],
            "reasons": "delights_the_player: repair lacks a payoff",
            "fun_advice": "Make the payoff more memorable.",
            "failed_checks": ["delights_the_player"],
        }
    ]

    saved.station = Station.FUN_REVIEW
    saved.status = Status.QUEUED
    saved.return_after = None
    queue.save(saved)
    assert line.step(NOW).kind == "failed_attempt"
    repeated = queue.get(ticket.id)
    assert repeated.payload["fun_rounds"] == MAX_FUN_ROUNDS + 1
    assert repeated.payload["fun_history"] == saved.payload["fun_history"]

    first = _line_ticket(
        "fun-history",
        payload={"fun_rounds": 0, "fun_history": [], "plan": {"kind": "set_text", "address": "first"}},
    )
    history_line, history_queue = _line(tmp_path / "history", first, _blocked_result())
    assert history_line.step(NOW).kind == "fun_blocked"
    after_first = history_queue.get(first.id)
    after_first.station = Station.FUN_REVIEW
    after_first.status = Status.QUEUED
    after_first.payload["plan"] = {"kind": "set_text", "address": "second"}
    history_queue.save(after_first)
    assert history_line.step(NOW).kind == "failed_attempt"
    failed = history_queue.get(first.id)
    assert len(failed.payload["fun_history"]) == 2
    assert [entry["plan"]["address"] for entry in failed.payload["fun_history"]] == ["first", "second"]
    assert failed.payload["fun_history"][-1]["fun_advice"] == "Make the payoff more memorable."

    unreadable = _line_ticket("fun-unreadable")
    normal_line, normal_queue = _line(
        tmp_path / "unreadable",
        unreadable,
        StationResult(False, "fun_review", "no usable verdict from the reviewer"),
    )
    assert normal_line.step(NOW).kind == "failed_attempt"
    assert normal_queue.get(unreadable.id).attempts == 1


def test_empty_fun_failed_checks_use_the_rule_feedback_line(tmp_path: Path) -> None:
    result = _blocked_result()
    result.payload_updates["fun_review"]["failed_checks"] = []
    ticket = _line_ticket("fun-empty-checks")
    line, queue = _line(tmp_path, ticket, result)

    assert line.step(NOW).kind == "fun_blocked"
    assert (
        queue.get(ticket.id)
        .payload["fun_feedback"]
        .startswith("Failed checks: none (blocked by the rule against only moving words)\n")
    )


def _probe_line(tmp_path: Path, ticket: Ticket, result: StationResult) -> tuple[FactoryLine, TicketQueue]:
    queue = TicketQueue(tmp_path / "probe-tickets")
    queue.add(ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "probe-state.json"),
        handlers={Station.PROBE: lambda _ticket, _now: result},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    return line, queue


def test_probe_reject_carries_last_fun_advice_and_reasons(tmp_path: Path) -> None:
    ticket = Ticket(
        "probe-with-fun-history",
        "scene-1",
        Station.PROBE,
        1000,
        NOW.isoformat(),
        NOW.isoformat(),
        payload={
            "plan": {"kind": "set_text"},
            "fun_history": [
                {
                    "plan": {"kind": "set_text"},
                    "reasons": "Use the existing clue as a payoff.",
                    "fun_advice": "Make the clue matter at the reveal.",
                    "failed_checks": ["delights_the_player"],
                }
            ],
        },
    )
    result = StationResult(
        False,
        "probe",
        "probe failed",
        payload_updates={"probe": {"verdict": "reject", "feedback": "probe feedback"}},
    )
    line, queue = _probe_line(tmp_path, ticket, result)

    assert line.step(NOW).kind == "probe_rejected"
    assert queue.get(ticket.id).payload["probe_feedback"] == (
        "probe feedback\n\nEarlier fun review advice (still applies):\n"
        "Reasons: Use the existing clue as a payoff.\n"
        "fun_advice: Make the clue matter at the reveal."
    )


def test_probe_reject_without_fun_history_keeps_feedback_unchanged(tmp_path: Path) -> None:
    ticket = Ticket(
        "probe-without-fun-history",
        "scene-1",
        Station.PROBE,
        1000,
        NOW.isoformat(),
        NOW.isoformat(),
        payload={"plan": {"kind": "set_text"}},
    )
    result = StationResult(
        False,
        "probe",
        "probe failed",
        payload_updates={"probe": {"verdict": "reject", "feedback": "probe feedback"}},
    )
    line, queue = _probe_line(tmp_path, ticket, result)

    assert line.step(NOW).kind == "probe_rejected"
    assert queue.get(ticket.id).payload["probe_feedback"] == "probe feedback"


def test_probe_and_fun_pass_clear_fun_feedback(tmp_path: Path) -> None:
    probe_ticket = Ticket(
        "probe-pass",
        "scene-1",
        Station.PROBE,
        1000,
        NOW.isoformat(),
        NOW.isoformat(),
        payload={"fun_feedback": "stale advice", "merge_to_main": True},
    )
    queue = TicketQueue(tmp_path / "probe-tickets")
    queue.add(probe_ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "probe-state.json"),
        handlers={Station.PROBE: lambda _ticket, _now: StationResult(True, "probe", "ok")},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    assert line.step(NOW).kind == "advanced"
    assert "fun_feedback" not in queue.get("probe-pass").payload

    fun_ticket = _line_ticket("fun-pass", payload={"fun_feedback": "stale advice", "feedback_plan": {"old": True}})
    fun_line, fun_queue = _line(
        tmp_path / "fun-pass",
        fun_ticket,
        StationResult(True, "fun_review", "great", payload_updates={"fun_review": {"verdict": "pass"}}),
    )
    assert fun_line.step(NOW).kind == "advanced"
    assert "fun_feedback" not in fun_queue.get("fun-pass").payload
    assert "feedback_plan" not in fun_queue.get("fun-pass").payload


def test_planner_brief_prioritizes_delight_and_fun_feedback() -> None:
    collapsed = re.sub(r"\s+", " ", PLANNER_BRIEF)
    assert "choose the one the player would enjoy most" in collapsed
    assert "Fun means Freytag pacing, quality characters, and continuity in and between scenes." in collapsed
    assert "When a story editor's block is shown, treat its fun_advice as the owner's taste and follow it." in collapsed
    assert "Never resubmit the blocked fix with only its words moved around." in collapsed
    assert 'When a section named "Fun review feedback" follows' not in PLANNER_BRIEF


def test_fun_advice_is_capped_at_300_characters(tmp_path: Path) -> None:
    root, _tree, ticket = _review_fixture(tmp_path)
    advice = "a" * 301
    checks = {**{key: True for key in FUN_REVIEW_CHECKS}, "delights_the_player": False}
    result = fun_review_handler(
        root,
        reviewer=_reviewer(_reply(checks=checks, fun_advice=advice)),
        runner=_runner,
        package_loader=_package_loader,
    )(ticket, NOW)

    assert len(result.payload_updates["fun_review"]["fun_advice"]) == 300

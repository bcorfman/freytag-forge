from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from factory.lessons import lessons_path, record_lessons, render_lessons
from factory.line import FactoryLine, StationResult
from factory.state import FactoryState
from factory.stations import fix_plan
from factory.stations.planner import PLANNER_BRIEF
from factory.tickets import Station, Status, Ticket, TicketQueue

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def _ticket(
    ticket_id: str,
    *,
    scene: str = "1A",
    path: Path,
    history: list[dict] | None = None,
    plan: dict | None = None,
    station: Station = Station.FUN_REVIEW,
) -> Ticket:
    return Ticket(
        id=ticket_id,
        scene=scene,
        station=station,
        token_budget=1000,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
        payload={
            "fun_lessons_path": str(path),
            "fun_history": history or [],
            "plan": plan or {"kind": "set_text", "reason": "Precedent: concise wording; it keeps the scene moving."},
        },
    )


def _history(
    *, kind: str = "set_text", reason: str = "Precedent: concise wording; it keeps the scene moving."
) -> list[dict]:
    return [
        {
            "plan": {"kind": kind, "reason": reason},
            "reasons": "The repair does not pay off.",
            "fun_advice": "Give the detail a payoff.",
            "failed_checks": ["delights_the_player"],
        }
    ]


def _records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_recording_is_idempotent_and_keeps_only_the_record_fields(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    ticket = _ticket("ticket-1", path=path, scene="1A", history=_history())

    record_lessons(ticket, "fun_exhausted")
    record_lessons(ticket, "fun_exhausted")

    records = _records(path)
    assert len(records) == 1
    assert set(records[0]) == {
        "lesson_id",
        "ticket_id",
        "scene_id",
        "outcome",
        "fix_kind",
        "precedent",
        "failed_checks",
        "fun_round",
        "recorded_at",
    }
    assert records[0]["lesson_id"] == "ticket-1:1:blocked"
    assert records[0]["precedent"] == "concise wording"
    assert ticket.payload["fun_lessons_recorded"] == ["ticket-1:1:blocked"]


def test_no_winning_record_is_written_without_a_delivered_outcome(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    ticket = _ticket(
        "ticket-1",
        path=path,
        history=_history(),
        plan={"kind": "add_pacing_beat", "reason": "Precedent: beat; reason."},
    )

    record_lessons(ticket, "fun_exhausted")

    assert all(record["outcome"] != "won_after_block" for record in _records(path))


def test_delivered_records_the_final_plan_after_the_block(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    ticket = _ticket(
        "ticket-1",
        path=path,
        scene="2A",
        history=_history(kind="edit_claim_evidence"),
        plan={"kind": "add_pacing_beat", "reason": "Precedent: plant a clue; the detail pays off."},
    )

    record_lessons(ticket, "delivered")

    records = _records(path)
    assert [record["outcome"] for record in records] == ["blocked", "won_after_block"]
    assert records[-1]["lesson_id"] == "ticket-1:2:won_after_block"
    assert records[-1]["failed_checks"] == []
    assert records[-1]["fix_kind"] == "add_pacing_beat"


@pytest.mark.parametrize(
    ("reason", "expected"),
    [
        ("Precedent: none; list checks and the reason it does not apply.", "none"),
        ("Precedent: NONE is not applicable; explain why.", "none"),
        ("Precedent: Foo bar. More text", "Foo bar"),
        ("Precedent: line one\nline two", "line one"),
        ("Precedent: semicolon; more text", "semicolon"),
    ],
)
def test_precedent_is_normalized_when_recorded(tmp_path: Path, reason: str, expected: str) -> None:
    path = tmp_path / "lessons.jsonl"
    record_lessons(_ticket("precedent", path=path, history=_history(reason=reason)), "fun_exhausted")

    assert _records(path)[0]["precedent"] == expected


def test_plan_without_a_kind_writes_no_record(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    history = [{"plan": {"reason": "Precedent: no kind."}, "failed_checks": ["delights_the_player"]}]

    record_lessons(
        _ticket("missing-kind", path=path, history=history, plan={"reason": "Precedent: no kind."}),
        "delivered",
    )

    assert not path.exists()


def test_unknown_stored_records_are_not_rendered(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    records = []
    for outcome, ticket_id, scene_id, fun_round in (
        ("blocked", "unknown-block-1", "1A", 1),
        ("blocked", "unknown-block-2", "2A", 1),
        ("won_after_block", "unknown-win-1", "3A", 2),
        ("won_after_block", "unknown-win-2", "4A", 2),
    ):
        records.append(
            {
                "lesson_id": f"{ticket_id}:lesson",
                "ticket_id": ticket_id,
                "scene_id": scene_id,
                "outcome": outcome,
                "fix_kind": "unknown",
                "precedent": "none",
                "failed_checks": ["delights_the_player"] if outcome == "blocked" else [],
                "fun_round": fun_round,
                "recorded_at": "2026-01-01T00:00:00+00:00",
            }
        )
    path.write_text("\n".join(json.dumps(record) for record in records) + "\n", encoding="utf-8")

    assert render_lessons(path) == ""


def test_invalid_records_are_skipped_while_good_records_render(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    for ticket_id, scene in (("good-1", "1A"), ("good-2", "2A")):
        record_lessons(
            _ticket(ticket_id, path=path, scene=scene, history=_history(reason="Precedent: good lesson.")),
            "fun_exhausted",
        )
    invalid_records = [
        {"lesson_id": 1},
        {"lesson_id": "bad-list-ticket", "ticket_id": [], "scene_id": "3A"},
        {"lesson_id": "bad-outcome", "ticket_id": "bad", "scene_id": "3A", "outcome": "oops"},
        {"lesson_id": "bad-check", "ticket_id": "bad", "scene_id": "3A", "failed_checks": ["ok", 1]},
        {"lesson_id": "bad-round", "ticket_id": "bad", "scene_id": "3A", "fun_round": True},
    ]
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not-json\n")
        for record in invalid_records:
            handle.write(json.dumps(record) + "\n")

    rendered = render_lessons(path)

    assert 'Avoid: set_text via "good lesson" tends to fail delights_the_player (2 tickets, 2 scenes).' in rendered
    assert "bad-list-ticket" not in rendered


def test_lessons_path_honors_payload_and_default(tmp_path: Path) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    assert lessons_path({}) == repository_root / "factory" / "state" / "fun_lessons.jsonl"
    assert lessons_path({"fun_lessons_path": "custom/lessons.jsonl"}) == repository_root / "custom" / "lessons.jsonl"
    assert lessons_path({"fun_lessons_path": tmp_path / "lessons.jsonl"}) == tmp_path / "lessons.jsonl"
    assert lessons_path({"fun_lessons_path": None}) is None


def test_proven_threshold_and_mixed_conflict_are_rendered(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    shared_reason = "Precedent: concise wording. It works."
    for ticket_id, scene in (("b1", "1A"), ("b2", "2A")):
        ticket = _ticket(ticket_id, path=path, scene=scene, history=_history(reason=shared_reason))
        record_lessons(ticket, "fun_exhausted")
    for ticket_id, scene in (("w1", "3A"), ("w2", "4A")):
        ticket = _ticket(
            ticket_id,
            path=path,
            scene=scene,
            history=_history(reason=shared_reason),
            plan={"kind": "set_text", "reason": "Precedent: concise wording. It works."},
        )
        record_lessons(ticket, "delivered")

    rendered = render_lessons(path)

    assert "FUN REVIEW LESSONS (machine-recorded, proven across ≥2 scenes)" in rendered
    assert 'Mixed: set_text via "concise wording": 2 wins, 4 blocks on delights_the_player.' in rendered

    one_ticket = _ticket("only-one", path=path, scene="5A", history=_history(kind="edit_claim_evidence"))
    record_lessons(one_ticket, "fun_exhausted")
    assert 'edit_claim_evidence via "concise wording"' not in render_lessons(path)


def test_rendered_lessons_are_capped_and_evicted_from_the_end(tmp_path: Path) -> None:
    path = tmp_path / "lessons.jsonl"
    for index in range(40):
        for suffix in ("a", "b"):
            ticket = _ticket(
                f"ticket-{index}-{suffix}",
                path=path,
                scene=f"{index + 1}{suffix}",
                history=_history(
                    kind=f"kind-{index}", reason=f"Precedent: technique-{index}-" + ("x" * 30) + "; reason."
                ),
            )
            record_lessons(ticket, "fun_exhausted")
    rendered = render_lessons(path, cap=4000)

    assert len(rendered) <= 4000
    assert rendered.splitlines()[1].startswith("- Avoid:")
    assert rendered.splitlines()[-1].startswith("- (")
    assert "lessons not shown)" in rendered


def test_render_lessons_missing_file_is_empty(tmp_path: Path) -> None:
    assert render_lessons(tmp_path / "missing.jsonl") == ""


def test_line_records_all_three_fun_lesson_call_points(tmp_path: Path) -> None:
    history = _history()

    delivered = _ticket("delivered", path=tmp_path / "delivered.jsonl", history=history, station=Station.LIVE_PLAYTEST)
    delivered.payload["merge_to_main"] = True
    queue = TicketQueue(tmp_path / "delivered-tickets")
    queue.add(delivered)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "delivered-state.json"),
        handlers={Station.LIVE_PLAYTEST: lambda _ticket, _now: StationResult(True, "playtest", "ok")},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    assert line.step(NOW).kind == "delivered"
    assert {record["outcome"] for record in _records(tmp_path / "delivered.jsonl")} == {"blocked", "won_after_block"}

    blocked = _ticket("blocked", path=tmp_path / "blocked.jsonl", station=Station.FUN_REVIEW)
    blocked.payload["fun_rounds"] = 1
    blocked_line = FactoryLine(
        queue=(blocked_queue := TicketQueue(tmp_path / "blocked-tickets")),
        state=FactoryState.load(tmp_path / "blocked-state.json"),
        handlers={
            Station.FUN_REVIEW: lambda _ticket, _now: StationResult(
                False,
                "fun_review",
                "blocked",
                payload_updates={
                    "fun_review": {
                        "verdict": "block",
                        "plan": {"kind": "set_text", "reason": "Precedent: concise wording; reason."},
                        "reasons": "No payoff.",
                        "fun_advice": "Add one.",
                        "failed_checks": ["delights_the_player"],
                    }
                },
            )
        },
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    blocked_queue.add(blocked)
    assert blocked_line.step(NOW).kind == "failed_attempt"
    assert {record["outcome"] for record in _records(tmp_path / "blocked.jsonl")} == {"blocked"}

    triage = _ticket("triage", path=tmp_path / "triage.jsonl", history=history, station=Station.LIVE_PLAYTEST)
    triage.payload["merge_to_main"] = True
    triage_queue = TicketQueue(tmp_path / "triage-tickets")
    triage_queue.add(triage)
    triage_line = FactoryLine(
        queue=triage_queue,
        state=FactoryState.load(tmp_path / "triage-state.json"),
        handlers={
            Station.LIVE_PLAYTEST: lambda _ticket, _now: StationResult(
                False, "playtest", "bad", turns=[{"scene": "1A"}]
            )
        },
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    assert triage_line.step(NOW).kind == "to_triage"
    assert {record["outcome"] for record in _records(tmp_path / "triage.jsonl")} == {"blocked"}


def test_line_ignores_lesson_writer_errors_and_does_not_call_it_without_history(tmp_path: Path, monkeypatch) -> None:
    import factory.line as line_module

    calls: list[str] = []

    def broken(_ticket, outcome: str) -> None:
        calls.append(outcome)
        raise RuntimeError("writer failed")

    monkeypatch.setattr(line_module, "record_lessons", broken)
    ticket = _ticket("empty", path=tmp_path / "empty.jsonl", history=[], station=Station.LIVE_PLAYTEST)
    ticket.payload["merge_to_main"] = True
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    line = FactoryLine(
        queue=queue,
        state=FactoryState.load(tmp_path / "state.json"),
        handlers={Station.LIVE_PLAYTEST: lambda _ticket, _now: StationResult(True, "playtest", "ok")},
        provider_for=lambda _ticket: None,
        check_breakers=lambda _now: [],
    )
    assert line.step(NOW).kind == "delivered"
    assert calls == []

    ticket = _ticket("error", path=tmp_path / "error.jsonl", history=_history(), station=Station.LIVE_PLAYTEST)
    ticket.payload["merge_to_main"] = True
    queue.add(ticket)
    assert line.step(NOW).kind == "delivered"
    assert calls == ["delivered"]
    assert queue.get("error").status is Status.PASSED


def test_evidence_carries_fun_lessons_and_honors_the_override(tmp_path: Path) -> None:
    from tests.test_factory_fix_plan import PACKAGE, TICKET

    path = tmp_path / "lessons.jsonl"
    path.write_text(
        json.dumps(
            {
                "lesson_id": "one:1:blocked",
                "ticket_id": "one",
                "scene_id": "1A",
                "outcome": "blocked",
                "fix_kind": "set_text",
                "precedent": "concise wording",
                "failed_checks": ["delights_the_player"],
                "fun_round": 1,
                "recorded_at": NOW.isoformat(),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    ticket = dict(TICKET)
    ticket["fun_lessons_path"] = str(path)
    assert fix_plan.build_evidence(ticket, PACKAGE)["fun_lessons"] is None

    path.write_text(
        "\n".join(
            json.dumps(
                {
                    **json.loads(path.read_text(encoding="utf-8").strip()),
                    "ticket_id": str(index),
                    "scene_id": f"{index}A",
                }
            )
            for index in (1, 2)
        )
        + "\n",
        encoding="utf-8",
    )
    rendered = fix_plan.build_evidence(ticket, PACKAGE)["fun_lessons"]
    assert rendered is not None
    assert "FUN REVIEW LESSONS" in rendered


def test_planner_brief_has_the_fun_lesson_sentence() -> None:
    assert (
        "Fun review lessons describe patterns, not fixes; never repeat an Avoid pattern for a scene unless your "
        "reason names the lesson and why this scene differs."
    ) in PLANNER_BRIEF


@pytest.mark.parametrize("outcome", ["delivered", "fun_exhausted"])
def test_empty_history_never_creates_a_store(tmp_path: Path, outcome: str) -> None:
    path = tmp_path / "lessons.jsonl"
    record_lessons(_ticket("empty", path=path), outcome)
    assert not path.exists()

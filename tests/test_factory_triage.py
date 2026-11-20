import json
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

from factory.stations import build_handlers
from factory.stations.triage import (
    append_log,
    classify_turn,
    classify_turns,
    escalations,
    main,
    read_log,
    route,
    triage_handler,
    unclear_packet,
)
from factory.tickets import Station, TicketClass


def packet(key: str = "1B/r2/t5", **updates) -> dict:
    value = {"key": key, "scene": "1B"}
    value.update(updates)
    return value


def test_classify_rules_r1_to_r9() -> None:
    cases = [
        (packet(engine_error="boom"), TicketClass.ENGINE.value, "R1"),
        (packet(stuck=True), TicketClass.STORY_DATA.value, "R2"),
        (packet(stuck=True, candidates_offered=["leave"]), TicketClass.STORY_DATA.value, "R3"),
        (
            packet(stuck=True, candidates_offered=["leave"], match_issues=["bad json"]),
            TicketClass.NARRATOR_PROMPT.value,
            "R4",
        ),
        (
            packet(stuck=True, candidates_offered=["leave"], matched_candidate="leave", committed=False),
            TicketClass.ENGINE.value,
            "R5",
        ),
        (packet(stuck=True, candidates_offered=["leave"], matched_candidate="leave"), "unclear", "R6"),
        (packet(item_facts_issues=["missing owner"]), TicketClass.WORLD_MODEL.value, "R7"),
        (packet(flags=["restarts_scene"]), TicketClass.NARRATOR_PROMPT.value, "R8"),
        (packet(), "unclear", "R9"),
    ]
    for value, expected_class, expected_rule in cases:
        result = classify_turn(value)
        assert (result["class"], result["rule"]) == (expected_class, expected_rule)


def test_engine_state_outranks_flags_and_conflicts_are_unclear() -> None:
    stuck = classify_turn(packet(stuck=True, flags=["missed_change"]))
    conflict = classify_turn(packet(flags=["missed_change", "restarts_scene"]))
    unknown = classify_turn(packet(flags=["not_a_judge_flag"]))

    assert (stuck["class"], stuck["rule"]) == (TicketClass.STORY_DATA.value, "R2")
    assert conflict["class"] == unknown["class"] == "unclear"
    assert conflict["rule"] == unknown["rule"] == "R9"
    assert "conflicting" in conflict["reasons"][0]
    assert any("not_a_judge_flag" in reason for reason in unknown["reasons"])


def test_malformed_packets_are_unclear_and_keep_order() -> None:
    routed = classify_turns([{}, packet("ok", flags=["restarts_scene"]), {"key": 4, "scene": "1B"}])

    assert [item["key"] for item in routed] == ["", "ok", ""]
    assert [item["class"] for item in routed] == ["unclear", TicketClass.NARRATOR_PROMPT.value, "unclear"]
    assert routed[0]["rule"] == routed[2]["rule"] == "R9"
    assert "key" in routed[0]["reasons"][0]
    assert "key" in routed[2]["reasons"][0]


def test_unclear_packet_is_bounded_and_excludes_extra_text() -> None:
    packets = [packet(f"k{i}", narration="n" * 700, reasoning="judge text", scenario_text="secret") for i in range(3)]
    routed = classify_turns(packets)
    reduced = unclear_packet(packets, routed, max_turns=2, max_narration=600)

    assert len(reduced) == 2
    assert len(reduced[0]["narration"]) == 600
    assert "reasoning" not in reduced[0]
    assert "scenario_text" not in reduced[0]
    assert "reasons" in reduced[0]


def test_route_resolver_accepts_only_requested_valid_classes() -> None:
    turns = [packet("a"), packet("b"), packet("c"), packet("d")]

    def resolver(_asked):
        return {
            "a": TicketClass.ENGINE.value,
            "extra": TicketClass.WORLD_MODEL.value,
            "b": "not_a_ticket_class",
        }

    routed, unclear = route(turns, resolver=resolver)
    assert routed[0]["rule"] == "RM"
    assert routed[0]["class"] == TicketClass.ENGINE.value
    assert routed[1]["class"] == routed[2]["class"] == routed[3]["class"] == "unclear"
    assert len(unclear) == 3

    raised, still_unclear = route([packet()], resolver=lambda _asked: (_ for _ in ()).throw(RuntimeError("no")))
    assert raised[0]["class"] == "unclear"
    assert len(still_unclear) == 1


def test_escalations_count_distinct_keys_by_scene_and_class() -> None:
    log = [
        {"key": "a", "scene": "1A", "class": "engine"},
        {"key": "a", "scene": "1A", "class": "engine"},
        {"key": "b", "scene": "1A", "class": "engine"},
        {"key": "u", "scene": "1A", "class": "unclear"},
    ]
    routed = [
        {"key": "b", "scene": "1A", "class": "engine"},
        {"key": "c", "scene": "1A", "class": "engine"},
        {"key": "a", "scene": "1B", "class": "engine"},
        {"key": "b", "scene": "1B", "class": "engine"},
        {"key": "c", "scene": "1B", "class": "engine"},
    ]

    assert escalations(log, routed, threshold=2) == [
        {"scene": "1A", "class": "engine", "count": 3, "keys": ["a", "b", "c"]},
        {"scene": "1B", "class": "engine", "count": 3, "keys": ["a", "b", "c"]},
    ]


def test_append_log_is_idempotent_and_read_log_tolerates_corruption(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "triage.jsonl"
    routed = [
        {"key": "a", "scene": "1A", "class": "engine", "rule": "R1"},
        {"key": "u", "scene": "1A", "class": "unclear", "rule": "R9"},
    ]
    now = datetime(2026, 1, 1, tzinfo=UTC)
    append_log(path, routed, "ticket", now)
    append_log(path, routed, "ticket", now)
    with path.open("a", encoding="utf-8") as handle:
        handle.write("not json\n")

    assert len(read_log(path)) == 1
    assert read_log(tmp_path / "missing.jsonl") == []
    assert read_log(path)[0]["key"] == "a"


def make_ticket(payload: dict, ticket_id: str = "ticket") -> SimpleNamespace:
    return SimpleNamespace(id=ticket_id, payload=payload)


def test_handler_passes_writes_output_and_reports_escalation(tmp_path: Path) -> None:
    turns = [packet(f"k{i}", flags=["missed_change"]) for i in range(3)]
    log_path = tmp_path / "logs" / "triage.jsonl"
    out_path = tmp_path / "routing.json"
    result = triage_handler(tmp_path)(
        make_ticket({"turns": turns, "log_path": log_path, "out_path": out_path}),
        datetime(2026, 1, 1, tzinfo=UTC),
    )

    assert result.passed and result.tokens == 0
    assert "escalate 1B world_model 3" in result.output
    saved = json.loads(out_path.read_text(encoding="utf-8"))
    assert len(saved["routed"]) == 3
    assert saved["escalations"][0]["count"] == 3


def test_handler_failures_name_bad_input_and_unclear_keys(tmp_path: Path) -> None:
    handler = triage_handler(tmp_path)
    missing = handler(make_ticket({}), datetime.now(UTC))
    empty = handler(make_ticket({"turns": []}), datetime.now(UTC))
    unclear = handler(make_ticket({"turns": [packet()]}), datetime.now(UTC))

    assert not missing.passed and "turns" in missing.output
    assert not empty.passed and "empty" in empty.output
    assert not unclear.passed and "1B/r2/t5" in unclear.output and "model resolver" in unclear.output


def test_handler_loads_turns_file_and_caps_summary(tmp_path: Path) -> None:
    turns_path = tmp_path / "turns.json"
    turns_path.write_text(
        json.dumps([packet(f"key-{i:04d}", flags=["restarts_scene"]) for i in range(1000)]), encoding="utf-8"
    )
    result = triage_handler(tmp_path)(make_ticket({"turns": "turns.json"}), datetime.now(UTC))

    assert result.passed
    assert len(result.output) <= 4000
    assert "lines cut" in result.output


def test_handler_unreadable_file_and_cli_exit_codes(tmp_path: Path, capsys) -> None:
    missing = triage_handler(tmp_path)(make_ticket({"turns": "missing.json"}), datetime.now(UTC))
    assert not missing.passed and "could not read turns file" in missing.output

    turns_path = tmp_path / "turns.json"
    turns_path.write_text(json.dumps([packet("ok", flags=["restarts_scene"])]), encoding="utf-8")
    assert main(["--turns", str(turns_path)]) == 0
    turns_path.write_text(json.dumps([packet("unclear")]), encoding="utf-8")
    assert main(["--turns", str(turns_path)]) == 1
    assert main(["--turns", str(tmp_path / "nope.json")]) == 2
    assert capsys.readouterr().out


def test_build_handlers_contains_triage() -> None:
    assert Station.TRIAGE in build_handlers(Path("."))

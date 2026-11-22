from datetime import UTC, datetime
from pathlib import Path

from factory.followups import open_followups
from factory.line import FactoryLine, StationResult
from factory.state import FactoryState
from factory.stations.triage import triage_handler
from factory.tickets import Station, Status, Ticket, TicketClass, TicketQueue

NOW = datetime(2026, 1, 1, 12, tzinfo=UTC)


def parent(ticket_id: str = "parent") -> Ticket:
    timestamp = NOW.isoformat()
    return Ticket(
        id=ticket_id,
        scene="parent-scene",
        station=Station.TRIAGE,
        token_budget=321,
        created_at=timestamp,
        updated_at=timestamp,
        payload={"provider": "alpha"},
    )


def turn(key: str, scene: str = "1A", **fields) -> dict:
    packet = {"key": key, "scene": scene}
    packet.update(fields)
    return packet


def routing(routed: list[dict], turns: list[dict], escalations: list[dict] | None = None) -> dict:
    return {"routed": routed, "escalations": escalations or [], "turns": turns}


def routed(key: str, scene: str, class_name: str, rule: str) -> dict:
    return {"key": key, "scene": scene, "class": class_name, "rule": rule}


def test_followups_group_by_class_and_restart_at_the_expected_station(tmp_path: Path) -> None:
    turns = [turn("story"), turn("narrator"), turn("world"), turn("engine"), turn("unclear")]
    result = routing(
        [
            routed("story", "1A", "story_data", "R2"),
            routed("narrator", "1A", "narrator_prompt", "R4"),
            routed("world", "1A", "world_model", "R7"),
            routed("engine", "1A", "engine", "R1"),
            routed("unclear", "1A", "unclear", "R9"),
        ],
        turns,
    )
    queue = TicketQueue(tmp_path / "tickets")

    opened = open_followups(queue, parent(), result, NOW)

    by_class = {ticket.ticket_class: ticket for ticket in opened}
    assert by_class[TicketClass.STORY_DATA].station is Station.DIAGNOSE
    assert by_class[TicketClass.NARRATOR_PROMPT].station is Station.WIRING
    assert by_class[TicketClass.WORLD_MODEL].station is Station.WORLD_NEED
    engine = by_class[TicketClass.ENGINE]
    assert engine.status is Status.FAILED
    assert engine.station is Station.CONTRACT_REFRESH
    assert engine.payload["needs"] == "engine_plan"
    assert "merge_to_main" not in engine.payload
    assert engine.payload["failing_turns"] == [turns[3]]
    assert by_class[TicketClass.STORY_DATA].payload == {
        "parent": "parent",
        "class": "story_data",
        "failing_turns": [turns[0]],
        "rules": {"story": "R2"},
        "merge_to_main": True,
    }
    assert queue.next_ready(NOW).id != engine.id


def test_followups_are_idempotent_and_malformed_routing_is_safe(tmp_path: Path) -> None:
    queue = TicketQueue(tmp_path / "tickets")
    turns = [turn("a")]
    result = routing([routed("a", "1A", "story_data", "R2")], turns)

    assert open_followups(queue, parent(), result, NOW)
    assert open_followups(queue, parent(), result, NOW) == []
    assert open_followups(queue, parent(), {}, NOW) == []
    assert open_followups(queue, parent(), {"routed": [], "turns": []}, NOW) == []
    assert open_followups(queue, parent(), {"routed": [], "escalations": [], "turns": "bad"}, NOW) == []


def test_escalation_suppresses_story_work_only_for_its_scene(tmp_path: Path) -> None:
    turns = [turn(f"a{i}", "1A") for i in range(3)] + [turn("world", "1A"), turn("engine", "1A"), turn("other", "1B")]
    result = routing(
        [
            routed("a0", "1A", "story_data", "R2"),
            routed("a1", "1A", "story_data", "R2"),
            routed("a2", "1A", "story_data", "R2"),
            routed("world", "1A", "world_model", "R7"),
            routed("engine", "1A", "engine", "R1"),
            routed("other", "1B", "story_data", "R2"),
        ],
        turns,
        [{"scene": "1A", "class": "story_data", "count": 3, "keys": ["a0", "a1", "a2"]}],
    )
    queue = TicketQueue(tmp_path / "tickets")

    opened = open_followups(queue, parent(), result, NOW)
    ids = {ticket.id for ticket in opened}

    assert ids == {
        "parent-1A-story_data-escalation",
        "parent-1A-world_model",
        "parent-1A-engine",
        "parent-1B-story_data",
    }
    escalation = queue.get("parent-1A-story_data-escalation")
    assert escalation.station is Station.CONTRACT_REFRESH
    assert "merge_to_main" not in escalation.payload
    assert escalation.payload["failing_turns"] == turns[:3]
    assert escalation.payload["reason"] == "three failures of one class in one scene"


def test_followup_ids_replace_unsafe_characters(tmp_path: Path) -> None:
    queue = TicketQueue(tmp_path / "tickets")
    result = routing([routed("a", "scene/one?", "world_model", "R7")], [turn("a", "scene/one?")])

    opened = open_followups(queue, parent("parent/with space"), result, NOW)

    assert opened[0].id == "parent_with_space-scene_one_-world_model"
    assert (tmp_path / "tickets" / f"{opened[0].id}.json").exists()


def test_end_to_end_playtest_triage_opens_world_and_wiring_tickets(tmp_path: Path) -> None:
    turns = [turn("story-turn", "1A", stuck=True), turn("world-turn", "1A", flags=["missed_change"])]
    ticket = Ticket(
        id="playtest",
        scene="1A",
        station=Station.ACT_CONTRACTS,
        token_budget=1000,
        created_at=NOW.isoformat(),
        updated_at=NOW.isoformat(),
    )
    queue = TicketQueue(tmp_path / "tickets")
    queue.add(ticket)
    state = FactoryState.load(tmp_path / "state.json")

    def playtest_handler(ticket: Ticket, now: datetime) -> StationResult:
        if ticket.id == "playtest":
            return StationResult(False, "playtest", "two failing turns", turns=turns)
        return StationResult(True, "playtest", "clean")

    handlers = {station: (lambda ticket, now: StationResult(True, "stub", "ok")) for station in Station}
    handlers[Station.LIVE_PLAYTEST] = playtest_handler
    handlers[Station.TRIAGE] = triage_handler(tmp_path)
    state.sleep_lane("hold-followups", NOW.replace(hour=13))
    line = FactoryLine(
        queue=queue,
        state=state,
        handlers=handlers,
        provider_for=lambda ticket: None if ticket.id == "playtest" else "hold-followups",
        check_breakers=lambda now: [],
    )

    outcomes = []
    while True:
        outcome = line.step(NOW)
        outcomes.append(outcome)
        if outcome.kind == "idle":
            break

    saved = queue.get("playtest")
    assert saved.status is Status.PASSED
    assert any(outcome.kind == "triaged" for outcome in outcomes)
    assert queue.get("playtest-1A-story_data").station is Station.DIAGNOSE
    assert queue.get("playtest-1A-world_model").station is Station.WORLD_NEED
    assert queue.get("playtest-1A-story_data").payload["failing_turns"] == [turns[0]]
    assert queue.get("playtest-1A-world_model").payload["failing_turns"] == [turns[1]]
    assert all(saved.station is not Station.DELIVER for saved in queue.all())

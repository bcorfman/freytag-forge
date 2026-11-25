from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from tests.scene_harness import authored_handoff, scene_engine

ROOT = Path("data/stories/continuity-initiative")


PACKAGE = load_story_package(ROOT)
NEW_THINGS = {
    "build_record": "build record",
    "transfer_queue": "transfer queue",
}


def _scene():
    return next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2B").metadata


def _entries() -> dict:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    return {route.id: route for route in PACKAGE.storylet_routes.storylets}


def _engine(*, true_facts: tuple[str, ...] = (), turn_index: int = 0) -> tuple[RuntimeState, RuntimeEngine]:
    return scene_engine(PACKAGE, "2B", true_facts=true_facts, turn_index=turn_index)


def _handoff(engine: RuntimeEngine, state: RuntimeState, command: str):
    return authored_handoff(engine, state, command)


def test_the_build_record_and_transfer_queue_things_are_declared_plainly_and_placed_in_2b():
    items = {item.id: item for item in PACKAGE.world.items}
    for item_id, name in NEW_THINGS.items():
        assert item_id in items, f"missing world item {item_id}"
        item = items[item_id]
        assert item.name == name
        assert item.fixed is True
        assert item.kind == "thing"
        assert item.owner is None and "'s " not in item.name
        assert item_id in _scene().item_ids and item_id in _scene().item_placements, item_id
    assert items["build_record"].scoped_aliases == ("access section", "build files")
    assert items["transfer_queue"].scoped_aliases == ("queue", "transfers", "held transfers")
    placements = _scene().item_placements
    assert all(placements[item_id].text for item_id in NEW_THINGS)
    assert all(placements[item_id].parent == "janus_archive" for item_id in NEW_THINGS)
    assert {"badge_checks_read", "held_transfers_seen", "ticket_header_matched"} <= set(PACKAGE.world.facts)


def test_three_new_optional_storylets_share_their_beats_windows_and_conditions():
    routes = _routes()
    expected = {
        "SL-2B-E": (
            (0, 6, 6),
            {("audit_window_missed", False), ("kristin_file_read", True)},
            "scene-2b3--brandons-role",
        ),
        "SL-2B-F": ((0, 6, 6), {("audit_window_missed", False)}, "scene-2b2--kristin-was-bait"),
        "SL-2B-G": (
            (4, 6, 7),
            {("archive_crisis_understood", True), ("held_transfers_seen", True)},
            "scene-2b4--michelles-hidden-resistance",
        ),
    }
    for storylet_id, (window, conditions, source_beat) in expected.items():
        route = routes[storylet_id]
        assert route.scene_id == "2B"
        assert len(route.realizations) == 1
        realization = route.realizations[0]
        assert (route.earliest_turn, route.target_turn, route.latest_turn) == window
        actual = {(item.fact_id, item.equals) for item in route.activation_conditions}
        assert actual == conditions
        assert (
            realization.id == {"SL-2B-E": "SL-2B-E-R1", "SL-2B-F": "SL-2B-F-R1", "SL-2B-G": "SL-2B-G-R1"}[storylet_id]
        )
        assert realization.source_beats == (source_beat,)


def test_the_new_reveals_are_quiet_short_and_exact():
    entries = _entries()
    routes = _routes()
    expected = {
        "k_sl_2b_e_r1": (
            "SL-2B-E",
            "badge_checks_read",
            {("audit_window_missed", False), ("kristin_file_read", True)},
            (
                ["read", "look at", "check", "examine", "inspect", "study", "open", "pull up"],
                ["build record", "access section", "badge readers", "readers", "badge checks"],
            ),
            ["build_record"],
            ("kristin", "brandon", "build_record", "archive_terminals"),
            ("badge readers", "three", "brandon"),
        ),
        "k_sl_2b_f_r1": (
            "SL-2B-F",
            "held_transfers_seen",
            {("audit_window_missed", False)},
            (
                ["read", "open", "check", "look at", "examine", "inspect", "study", "pull up"],
                ["transfer queue", "queue", "transfers", "held transfers", "transfer listing"],
            ),
            ["transfer_queue"],
            ("kristin", "transfer_queue", "archive_terminals"),
            ("held", "sensor fault", "week"),
        ),
        "k_sl_2b_g_r1": (
            "SL-2B-G",
            "ticket_header_matched",
            {("archive_crisis_understood", True), ("held_transfers_seen", True)},
            (
                ["read", "look at", "check", "compare", "examine", "inspect", "study", "match"],
                ["maintenance line", "ticket header", "header", "printout"],
            ),
            ["medical_terminal"],
            ("kristin", "medical_terminal", "transfer_queue"),
            ("ticket header", "sensor fault"),
        ),
    }
    forbidden = ("rebecca", "michelle", "uprising", "broadcast", "phase two", "route")
    for entry_id, (storylet_id, fact_id, required, evidence, reach_entity_ids, entity_ids, phrases) in expected.items():
        entry = entries[entry_id]
        assert entry.audience.kind == "public" and entry.audience.player_visible is True
        assert entry.available_in_scenes == ("2B",)
        assert entry.voiceable is False and entry.relevance.priority == -1
        assert {(item.fact_id, item.equals) for item in entry.requires} == required
        assert [list(group) for group in entry.action_evidence] == [*evidence]
        assert entry.reach_entity_ids == tuple(reach_entity_ids)
        assert entry.entity_ids == entity_ids
        assert entry.must_convey and len(entry.statement) <= 90
        assert not any(word in entry.delivery_text.casefold() for word in forbidden)
        assert all(phrase in entry.delivery_text.casefold() for phrase in phrases)
        assert {(operation.fact_id, operation.value) for operation in entry.establishes} == {(fact_id, True)}
        realization = routes[storylet_id].realizations[0]
        assert realization.protected_knowledge_boundaries == ("janus_phase_two",)


def test_the_transfer_queue_and_the_build_record_are_reachable_when_earned():
    state, engine = _engine()
    handoff = _handoff(engine, state, "Read the transfer queue.")
    assert handoff is not None and handoff.candidate.id == "k_sl_2b_f_r1"
    state, engine = _engine(true_facts=("audit_window_missed",))
    handoff = _handoff(engine, state, "Read the transfer queue.")
    assert handoff is None or handoff.candidate.id != "k_sl_2b_f_r1"
    state, engine = _engine(true_facts=("kristin_file_read",))
    handoff = _handoff(engine, state, "Read the access section of the build record.")
    assert handoff is not None and handoff.candidate.id == "k_sl_2b_e_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, "Read the access section of the build record.")
    assert handoff is None or handoff.candidate.id != "k_sl_2b_e_r1"


def test_the_maintenance_line_check_waits_for_the_transfers_and_the_printout():
    command = "Read the maintenance line."
    state, engine = _engine(true_facts=("archive_crisis_understood", "held_transfers_seen"), turn_index=5)
    handoff = _handoff(engine, state, command)
    assert handoff is not None and handoff.candidate.id == "k_sl_2b_g_r1"
    for facts in (("archive_crisis_understood",), ("held_transfers_seen",), ()):
        state, engine = _engine(true_facts=facts)
        handoff = _handoff(engine, state, command)
        assert handoff is None or handoff.candidate.id != "k_sl_2b_g_r1", facts

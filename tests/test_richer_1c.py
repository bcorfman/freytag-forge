from __future__ import annotations

from pathlib import Path

import yaml

from storygame.audit import audit_package
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)
NEW_THINGS = {
    "tire_tracks": "tire tracks",
    "air_vents": "air vents",
    "water_pallets": "water pallets",
    "identification_numbers": "identification numbers",
    "overhead_speaker": "overhead speaker",
}


def _scene():
    return next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1C").metadata


def _entries() -> dict:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    data = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["storylets"]}


def _engine(*, true_facts: tuple[str, ...] = ()) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1C"
    state.phase = _scene().freytag_phase
    state._assert_scene_entry_fact("1C")
    apply_scene_placements(PACKAGE, state.facts, "1C")
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    return state, engine


def _handoff(engine: RuntimeEngine, state: RuntimeState, command: str):
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    return uniquely_matched_authored_handoff(command, candidates)


def test_the_dock_and_line_things_are_declared_plainly_and_placed_in_1c():
    items = {item.id: item for item in PACKAGE.world.items}
    for item_id, name in NEW_THINGS.items():
        assert item_id in items, f"missing world item {item_id}"
        item = items[item_id]
        assert item.name == name
        assert item.fixed is True
        assert item.owner is None and "'s " not in item.name
        assert item_id in _scene().item_ids and item_id in _scene().item_placements, item_id
    assert items["air_vents"].scoped_aliases == ("vents",)
    assert items["water_pallets"].scoped_aliases == ("pallets", "pallet")
    assert items["overhead_speaker"].scoped_aliases == ("speaker",)
    placements = _scene().item_placements
    assert placements["tire_tracks"].parent == "loading_docks"
    assert placements["air_vents"].parent == "loading_docks"
    assert placements["water_pallets"].parent == "loading_docks"
    assert placements["identification_numbers"].parent == "processing_line"
    assert placements["overhead_speaker"].parent == "processing_line"
    assert all(placements[item_id].text for item_id in NEW_THINGS)
    assert {"dock_water_matched", "brandon_watches_door", "line_broadcast_heard"} <= set(PACKAGE.world.facts)


def test_three_new_optional_storylets_share_their_beats_windows_and_conditions():
    routes = _routes()
    expected_conditions = {
        "SL-1C-E": {("transfer_window_missed", False), ("emergency_water_label_read", True)},
        "SL-1C-F": {("facility_proof", True), ("transfer_window_missed", False)},
        "SL-1C-G": {("transfer_window_missed", False)},
    }
    for storylet_id, conditions in expected_conditions.items():
        route = routes[storylet_id]
        assert route["scene_id"] == "1C"
        assert len(route["realization_options"]) == 1
        pacing = route["activation"]["pacing"]
        assert (pacing["earliest_turn"], pacing["target_turn"], pacing["latest_turn"]) == (0, 2, 3)
        actual = {(item["fact_id"], item.get("equals")) for item in route["activation"].get("conditions", [])}
        assert actual == conditions


def test_the_new_reveals_are_quiet_short_and_exact():
    entries = _entries()
    expected_evidence = {
        "k_sl_1c_e_r1": (
            ["look", "examine", "inspect", "read", "check", "search"],
            ["pallets", "pallet", "bottles", "water", "label"],
        ),
        "k_sl_1c_f_r1": (["watch", "study", "look at", "glance at", "notice"], ["Brandon"]),
        "k_sl_1c_g_r1": (
            ["listen", "hear"],
            ["vents", "speaker", "sound", "statement", "announcement", "broadcast", "hum"],
        ),
    }
    expected_requires = {
        "k_sl_1c_e_r1": {("transfer_window_missed", False), ("emergency_water_label_read", True)},
        "k_sl_1c_f_r1": {("facility_proof", True), ("transfer_window_missed", False)},
        "k_sl_1c_g_r1": {("transfer_window_missed", False)},
    }
    for entry_id, groups in expected_evidence.items():
        entry = entries[entry_id]
        assert entry.audience.kind == "public" and entry.audience.player_visible is True
        assert entry.available_in_scenes == ("1C",)
        assert entry.voiceable is False
        assert entry.relevance.priority == -1
        assert {(requirement.fact_id, requirement.equals) for requirement in entry.requires} == expected_requires[
            entry_id
        ]
        assert [list(group) for group in entry.action_evidence] == [*groups]
        assert entry.must_convey
        assert len(entry.statement) <= 90
        assert not any(
            word in entry.delivery_text.casefold() for word in ("selected", "janus", "selection", "contaminated")
        )
    assert {(operation.fact_id, operation.value) for operation in entries["k_sl_1c_e_r1"].establishes} == {
        ("dock_water_matched", True)
    }
    assert {(operation.fact_id, operation.value) for operation in entries["k_sl_1c_f_r1"].establishes} == {
        ("brandon_watches_door", True)
    }
    assert {(operation.fact_id, operation.value) for operation in entries["k_sl_1c_g_r1"].establishes} == {
        ("line_broadcast_heard", True)
    }
    assert {"emergency water", "lot number", "thermos"} <= entries["k_sl_1c_e_r1"].delivery_text.casefold()
    assert {"door", "somebody has to watch the door"} <= entries["k_sl_1c_f_r1"].delivery_text.casefold()
    assert {"speaker", "emergency statement", "word for word"} <= entries["k_sl_1c_g_r1"].delivery_text.casefold()


def test_the_water_pallets_are_earned_only_after_the_thermos_label():
    state, engine = _engine(true_facts=("emergency_water_label_read",))
    handoff = _handoff(engine, state, "Inspect the water pallets.")
    assert handoff is not None and handoff.candidate.id == "k_sl_1c_e_r1"
    for facts in ((), ("transfer_window_missed",)):
        state, engine = _engine(true_facts=("emergency_water_label_read", *facts))
        handoff = _handoff(engine, state, "Inspect the water pallets.")
        assert handoff is None or handoff.candidate.id != "k_sl_1c_e_r1"


def test_watching_brandon_and_listening_to_the_vents_reach_their_reveals():
    state, engine = _engine(true_facts=("facility_proof",))
    handoff = _handoff(engine, state, "Watch Brandon.")
    assert handoff is not None and handoff.candidate.id == "k_sl_1c_f_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, "Watch Brandon.")
    assert handoff is None or handoff.candidate.id != "k_sl_1c_f_r1"
    state, engine = _engine()
    handoff = _handoff(engine, state, "Listen to the air vents.")
    assert handoff is not None and handoff.candidate.id == "k_sl_1c_g_r1"


def test_existing_1c_commands_still_reach_their_reveals():
    checks = (
        ((), "Inspect the loading docks.", "k_sl_1c_a_r1"),
        (("facility_proof",), "Study the prisoners.", "k_sl_1c_b_r1"),
        (
            ("facility_proof", "captives_confirmed_alive"),
            "Ask Brandon about the transfer route.",
            "k_sl_1c_c_secure_route",
        ),
        (("facility_proof", "captives_confirmed_alive"), "Copy the prisoner numbers.", "k_sl_1c_c_copy_numbers"),
    )
    for facts, command, entry_id in checks:
        state, engine = _engine(true_facts=facts)
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == entry_id, command


def test_the_richer_scene_adds_no_beat_overprojection():
    findings = audit_package(ROOT)["findings"]
    overprojection = [
        finding for finding in findings if finding["check"] == "beat_overprojection" and "SL-1C-" in str(finding)
    ]
    # Measured before the richer 1C data change: there were zero such findings.
    assert len(overprojection) <= 0

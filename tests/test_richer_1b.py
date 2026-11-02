"""The richer scene 1B: the abandoned park, the looping loudspeaker, the water thermos, the keypad."""

from __future__ import annotations

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)
NEW_THINGS = {
    "park_bicycle": "bicycle",
    "picnic_blanket": "picnic blanket",
    "picnic_thermos": "thermos",
    "picnic_cups": "two cups",
    "dog_leash": "dog leash",
    "park_fence": "park fence",
    "park_loudspeaker": "loudspeaker",
    "checkpoint_barrier": "checkpoint barrier",
    "gate_keypad": "gate keypad",
}


def _scene():
    return next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B").metadata


def _entries() -> dict:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _routes() -> dict:
    data = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["storylets"]}


def _engine(*, true_facts: tuple[str, ...] = ()) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    state.phase = _scene().freytag_phase
    state._assert_scene_entry_fact("1B")
    apply_scene_placements(PACKAGE, state.facts, "1B")
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    return state, engine


def _handoff(engine: RuntimeEngine, state: RuntimeState, command: str):
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    return uniquely_matched_authored_handoff(command, candidates)


def test_the_park_things_are_declared_plainly_and_placed_in_1b():
    items = {item.id: item for item in PACKAGE.world.items}
    for item_id, name in NEW_THINGS.items():
        assert items[item_id].name == name, item_id
        assert items[item_id].owner is None and "'s " not in items[item_id].name
        assert item_id in _scene().item_ids and item_id in _scene().item_placements, item_id
    assert items["picnic_blanket"].fixed and items["park_loudspeaker"].fixed and items["gate_keypad"].fixed
    placements = _scene().item_placements
    assert placements["picnic_thermos"].parent == "picnic_blanket"
    assert placements["picnic_cups"].parent == "picnic_blanket"
    assert placements["dog_leash"].parent == "park_fence"
    assert "service gate" in placements["gate_keypad"].text
    assert "pole" in placements["park_loudspeaker"].text


def test_three_new_optional_storylets_share_their_beats_earliest_turn():
    routes = _routes()
    for storylet_id in ("SL-1B-F", "SL-1B-G", "SL-1B-H"):
        assert routes[storylet_id]["scene_id"] == "1B"
        assert routes[storylet_id]["activation"]["pacing"]["earliest_turn"] == 0
        assert len(routes[storylet_id]["realization_options"]) == 1
    conditions = {
        storylet_id: {(c["fact_id"], c.get("equals")) for c in routes[storylet_id]["activation"].get("conditions", [])}
        for storylet_id in ("SL-1B-F", "SL-1B-G", "SL-1B-H")
    }
    assert conditions["SL-1B-F"] == set()
    assert conditions["SL-1B-G"] == {("brandon_identified", False)}
    assert conditions["SL-1B-H"] == {("missing_may_be_alive", True)}


def test_the_new_deliveries_say_what_was_written_and_keep_secrets():
    entries = _entries()
    left_behind = entries["k_sl_1b_f_r1"].delivery_text
    assert "kickstand" in left_behind and "leash" in left_behind and "tipped" in left_behind
    assert "selected" not in left_behind.casefold()
    loop = entries["k_sl_1b_g_r1"].delivery_text
    assert "half-beat" in loop and "mouths" in loop
    water = entries["k_sl_1b_h_r1"].delivery_text
    assert "emergency-water label" in water and "lot number" in water
    assert "telling the truth" not in water
    for entry_id, fact in (
        ("k_sl_1b_f_r1", "park_left_behind_read"),
        ("k_sl_1b_g_r1", "stranger_knows_script"),
        ("k_sl_1b_h_r1", "emergency_water_label_read"),
    ):
        assert fact in {operation.fact_id for operation in entries[entry_id].establishes}


def test_the_gate_deliveries_show_brandons_ease_with_the_keypad():
    entries = _entries()
    assert "keypad" in entries["k_sl_1b_c_r1"].delivery_text
    assert "freshly oiled" in entries["k_sl_1b_c_r1"].delivery_text
    assert "keypad" in entries["k_sl_1b_c_r2"].delivery_text


def test_left_behind_is_earned_by_looking_at_the_picnic_the_bicycle_or_the_leash():
    state, engine = _engine()
    for command in ("Look at the picnic blanket.", "Examine the bicycle.", "Look at the dog leash."):
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == "k_sl_1b_f_r1", command


def test_the_stranger_mouthing_the_broadcast_is_only_noticed_before_he_is_identified():
    state, engine = _engine()
    handoff = _handoff(engine, state, "Watch the stranger.")
    assert handoff is not None and handoff.candidate.id == "k_sl_1b_g_r1"
    state, engine = _engine(true_facts=("brandon_identified",))
    handoff = _handoff(engine, state, "Watch the stranger.")
    assert handoff is None or handoff.candidate.id != "k_sl_1b_g_r1"


def test_the_thermos_label_waits_for_brandons_explanation():
    state, engine = _engine()
    before = _handoff(engine, state, "Examine the thermos.")
    assert before is None or before.candidate.id != "k_sl_1b_h_r1"
    state, engine = _engine(true_facts=("missing_may_be_alive",))
    after = _handoff(engine, state, "Examine the thermos.")
    assert after is not None and after.candidate.id == "k_sl_1b_h_r1"

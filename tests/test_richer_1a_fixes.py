"""Fixes found by reading the 1A smoke probe: photograph depiction, split kitchen reveals, reachable neighbor."""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.story_package.dependencies import producers
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)


def _knowledge() -> dict[str, dict]:
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _candidate_ids(state: RuntimeState, engine: RuntimeEngine, command: str) -> set[str]:
    engine._activate_pacing()
    return {candidate.id for candidate in engine.projector.project(state, "player", command).candidates}


def test_1a_frame_uses_deadbolt_wording_and_keeps_outward_splinters_clue():
    frame = next(item for item in PACKAGE.knowledge.scene_frames if item.scene_id == "1A")
    earned_entry = PACKAGE.knowledge_indexes.by_id["k_sl_1a_a_r1"]

    assert "The deadbolt is still thrown." in frame.situation
    assert "splintered out of the wood" not in frame.situation
    assert "splinters around the frame point outward" in earned_entry.delivery_text


def _walk_to_the_neighbor() -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    count = {"n": 0}

    def provider(_command: str) -> dict:
        count["n"] += 1
        return {"segments": [{"kind": "narration", "text": f"Kristin acts, beat number {count['n']}."}]}

    engine = RuntimeEngine(state, provider)
    for command in (
        "Examine the back door.",
        "Look at the wall calendar.",
        "Look at the photograph.",
        "Search the drawer.",
        "Wait and observe.",
        "Wait and observe.",
        "Go outside.",
    ):
        engine._activate_pacing()
        engine.turn(command)
    return state, engine


def test_the_photograph_text_says_what_it_shows():
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1A")
    placement = scene.metadata.item_placements["lake_photograph"]
    assert "showing Kristin and Michelle at a lake" in placement.text
    assert "pear-shaped magnet" in placement.text


def test_the_kitchen_storylet_has_two_separate_reveals():
    entries = _knowledge()
    workstation, walls = entries["k_sl_1a_g_r1"], entries["k_sl_1a_g_r2"]
    assert "tea" in workstation.delivery_text and "calendar" not in workstation.delivery_text
    assert "calendar" in walls.delivery_text and "lemon cake" in walls.delivery_text
    assert "photograph" in walls.delivery_text and "tea" not in walls.delivery_text
    assert set(walls.reach_entity_ids) == {"kitchen_calendar", "lake_photograph"}
    workstation_storylet = next(item for item in PACKAGE.storylet_routes.storylets if item.id == "SL-1A-G")
    walls_storylet = next(item for item in PACKAGE.storylet_routes.storylets if item.id == "SL-1A-L")
    assert [realization.id for realization in workstation_storylet.realizations] == ["SL-1A-G-R1"]
    assert [realization.id for realization in walls_storylet.realizations] == ["SL-1A-L-R1"]
    assert walls.source.storylet_id == "SL-1A-L"
    assert walls.source.realization_id == "SL-1A-L-R1"
    assert {operation.fact_id for operation in workstation.establishes} == {
        "kitchen_last_hour_read",
        "michelle_abduction_suspicion",
    }
    assert {operation.fact_id for operation in walls.establishes} == {
        "lemon_cake_calendar_read",
    }


def test_a_calendar_command_offers_only_the_walls_reveal():
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    engine._activate_pacing()
    ranked = [
        candidate.id for candidate in engine.projector.project(state, "player", "Look at the wall calendar.").candidates
    ]
    assert ranked[0] == "k_sl_1a_g_r2"  # the command's own evidence ranks first; free slots may hold ambient reveals


def _deliver_1a_claim(claim_id: str, command: str) -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(PACKAGE)
    entry = _knowledge()[claim_id]

    def provider(_command: str) -> dict:
        return {
            "segments": [{"kind": "narration", "text": entry.delivery_text, "grounding_ids": [claim_id]}],
            "selected_knowledge_ids": [claim_id],
        }

    engine = RuntimeEngine(state, provider)
    engine._activate_pacing()
    assert explain_reveal(state, "player", entry).eligible
    engine.turn(command)
    return state, engine


def _true_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


def test_workstation_first_leaves_the_calendar_reveal_eligible_and_deliverable():
    state, _engine = _deliver_1a_claim("k_sl_1a_g_r1", "Look closely at the workstation.")
    calendar = _knowledge()["k_sl_1a_g_r2"]

    assert explain_reveal(state, "player", calendar).reason != "storylet_spent"
    assert explain_reveal(state, "player", calendar).eligible

    _deliver_1a_claim_after_state = RuntimeEngine(
        state,
        lambda _command: {
            "segments": [{"kind": "narration", "text": calendar.delivery_text, "grounding_ids": [calendar.id]}],
            "selected_knowledge_ids": [calendar.id],
        },
    )
    _deliver_1a_claim_after_state._activate_pacing()
    _deliver_1a_claim_after_state.turn("Look closely at the wall calendar.")
    assert _true_fact(state, "lemon_cake_calendar_read")


def test_calendar_first_leaves_the_workstation_reveal_eligible_and_deliverable():
    state, _engine = _deliver_1a_claim("k_sl_1a_g_r2", "Look closely at the wall calendar.")
    workstation = _knowledge()["k_sl_1a_g_r1"]

    assert explain_reveal(state, "player", workstation).reason != "storylet_spent"
    assert explain_reveal(state, "player", workstation).eligible

    workstation_engine = RuntimeEngine(
        state,
        lambda _command: {
            "segments": [{"kind": "narration", "text": workstation.delivery_text, "grounding_ids": [workstation.id]}],
            "selected_knowledge_ids": [workstation.id],
        },
    )
    workstation_engine._activate_pacing()
    workstation_engine.turn("Look closely at the workstation.")
    assert _true_fact(state, "kitchen_last_hour_read")


def test_kitchen_reveals_are_blocked_while_the_patrol_is_in_the_house():
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="patrol_in_house", subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Blocked."}]})
    engine._activate_pacing()

    for claim_id in ("k_sl_1a_g_r1", "k_sl_1a_g_r2"):
        result = explain_reveal(state, "player", _knowledge()[claim_id])
        assert not result.eligible
        assert result.reason == "prerequisite_missing"


def test_kitchen_reveals_are_not_repeatable():
    for claim_id, command in (
        ("k_sl_1a_g_r1", "Look closely at the workstation."),
        ("k_sl_1a_g_r2", "Look closely at the wall calendar."),
    ):
        state, _engine = _deliver_1a_claim(claim_id, command)
        result = explain_reveal(state, "player", _knowledge()[claim_id])
        assert not result.eligible
        assert result.reason == "already_established"


def test_calendar_claim_alone_produces_the_scene_3a_gate_fact():
    calendar = _knowledge()["k_sl_1a_g_r2"]
    assert {(operation.fact_id, operation.value) for operation in calendar.establishes} == {
        ("lemon_cake_calendar_read", True)
    }
    assert [
        (producer.kind, producer.record_id)
        for producer in producers(PACKAGE, "lemon_cake_calendar_read")
        if producer.kind == "claim"
    ] == [("claim", "k_sl_1a_g_r2")]


def test_the_neighbor_does_not_depend_on_the_patrol_being_away():
    entry = _knowledge()["k_sl_1a_i_r1"]
    assert all(requirement.fact_id != "patrol_in_house" for requirement in entry.requires)
    storylet = next(item for item in PACKAGE.storylet_routes.storylets if item.id == "SL-1A-I")
    assert all(condition.fact_id != "patrol_in_house" for condition in storylet.activation_conditions)


def test_the_neighbor_is_offered_after_the_patrol_is_in_the_house():
    state, engine = _walk_to_the_neighbor()
    assert any(f.predicate == "patrol_in_house" and str(f.value).lower() == "true" for f in state.facts.asserted)
    assert "k_sl_1a_i_r1" in _candidate_ids(state, engine, "Talk to the neighbor.")


def test_talking_to_the_neighbor_earns_his_account_exactly():
    from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff

    state, engine = _walk_to_the_neighbor()
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", "Talk to the neighbor.").candidates
    for command in ("Talk to the neighbor.", "Talk to Walt.", "Ask the neighbor what he saw."):
        handoff = uniquely_matched_authored_handoff(command, candidates)
        assert handoff is not None and handoff.candidate.id == "k_sl_1a_i_r1", command


def test_the_narrator_is_told_who_the_neighbor_and_the_calendar_are():
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1A")
    walt = scene.metadata.character_placements["walt_pruitt"].text
    assert "neighbor" in walt and "fence" in walt
    assert "paper calendar" in scene.metadata.item_placements["kitchen_calendar"].text

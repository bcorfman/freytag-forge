from __future__ import annotations

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from tests._legacy_package import legacy_package
from tests.test_canon_journey import PACKAGE as LOADED_PACKAGE
from tests.test_canon_journey import _ScriptedProvider


def _scene_2c_first_turn() -> tuple[RuntimeState, RuntimeEngine]:
    package = legacy_package(LOADED_PACKAGE, {"k_sl_1a_a_r1"})
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "2C"
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "2C")
    state._assert_scene_entry_fact("2C")
    state.facts.assert_fact(Fact(predicate="janus_evidence", subject="story", value="true"))
    assert state.turn_index == state.scene_entered_at_turn == 0
    assert not state.facts.matching("purge_clock_started")
    engine = RuntimeEngine(state, _ScriptedProvider(package))
    engine._activate_pacing()
    return state, engine


def test_copying_janus_evidence_offers_2c_c_r1_on_turn_one() -> None:
    state, engine = _scene_2c_first_turn()

    candidates = engine.projector.project(state, "player", "Copy the JANUS evidence to my laptop.").candidates

    assert "k_sl_2c_c_r1" in {candidate.id for candidate in candidates}


def test_reading_transfer_orders_does_not_offer_2c_c_r1_on_turn_one() -> None:
    state, engine = _scene_2c_first_turn()

    projection = engine.projector.project(state, "player", "Read the transfer orders.")
    matched = uniquely_matched_authored_handoff("Read the transfer orders.", projection.candidates)

    assert matched is None or matched.candidate.id != "k_sl_2c_c_r1"

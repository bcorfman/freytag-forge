from __future__ import annotations

import pytest

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


def test_transmitting_janus_evidence_does_not_offer_2c_d_r3_before_rebecca_hears_an_answer() -> None:
    state, engine = _scene_2c_first_turn()

    candidates = engine.projector.project(
        state, "player", "Head to the uplink and transmit the copied JANUS files."
    ).candidates

    assert "k_sl_2c_d_r3" not in {candidate.id for candidate in candidates}


@pytest.mark.parametrize(
    ("facts", "expected_delivery"),
    [
        (
            ("brandon_name_kept",),
            'Rebecca answers Kristin without taking her eyes off Brandon. "Trust is a luxury. Decide quickly." '
            'Her tablet chimes. She reads it, and her face changes. "The purge order. It starts within hours, and '
            'my people are on the list." Brandon says, "Yes." He says it coldly and avoids Kristin\'s eyes. The '
            'guards stand down, and Rebecca goes to move against Charles. Brandon says, "There is no time to argue. '
            "The broadcast uplink is at one end of this corridor. We can send the evidence now. The transfer carts "
            'are at the other end. You can free a cart of captives before the guards react. Pick one, Kristin."',
        ),
        (
            ("brandon_name_erased",),
            'Rebecca answers Kristin without taking her eyes off Brandon. "Trust is a luxury. Decide quickly." '
            'Her tablet chimes. She reads it, and her face changes. "The purge order. It starts within hours, and '
            'my people are on the list." Brandon says, "Yes." He glances at Kristin as he says it. The guards stand '
            'down, and Rebecca goes to move against Charles. Brandon says, "There is no time to argue. The broadcast '
            "uplink is at one end of this corridor. We can send the evidence now. The transfer carts are at the other "
            'end. You can free a cart of captives before the guards react. Pick one, Kristin."',
        ),
        (
            (),
            'Rebecca answers Kristin without taking her eyes off Brandon. "Trust is a luxury. Decide quickly." Her '
            'tablet chimes. She reads it, and her face changes. "The purge order. It starts within hours, and my '
            'people are on the list." Brandon looks at Kristin, then says, "Yes." The guards stand down, and Rebecca '
            'goes to move against Charles. Brandon says, "There is no time to argue. The broadcast uplink is at one '
            "end of this corridor. We can send the evidence now. The transfer carts are at the other end. You can free "
            'a cart of captives before the guards react. Pick one, Kristin."',
        ),
        (("brandon_name_kept", "brandon_name_erased"), None),
    ],
)
def test_brandon_ledger_colours_the_single_rebecca_observation_delivery(
    facts: tuple[str, ...], expected_delivery: str | None
) -> None:
    state, engine = _scene_2c_first_turn()
    for fact_id in facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    command = "Tell Rebecca my answer to her offer."
    projection = engine.projector.project(state, "player", command)
    matched = uniquely_matched_authored_handoff(command, projection.candidates)

    observation_ids = tuple(
        candidate.id for candidate in projection.candidates if candidate.id.startswith("k_sl_2c_c_r")
    )
    if expected_delivery is None:
        assert matched is None
        assert observation_ids == ()
    else:
        assert observation_ids == ("k_sl_2c_c_r1",)
        assert matched is not None
        assert matched.candidate.id == "k_sl_2c_c_r1"
        assert matched.delivery_text == expected_delivery


def test_reading_transfer_orders_does_not_offer_2c_d_r3_on_turn_one() -> None:
    state, engine = _scene_2c_first_turn()

    projection = engine.projector.project(state, "player", "Read the transfer orders.")
    matched = uniquely_matched_authored_handoff("Read the transfer orders.", projection.candidates)

    assert matched is None or matched.candidate.id != "k_sl_2c_d_r3"

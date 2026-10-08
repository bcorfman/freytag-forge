from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactPredicate, RouteOperation

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state_1a(package=PACKAGE) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    state.turn_index = 0
    return state


def _package_gating_all_reveals_for_1a(package=PACKAGE, *, remove_costs: bool = False, retract_costs: bool = False):
    knowledge = package.knowledge.model_copy(
        update={
            "knowledge": tuple(
                item.model_copy(update={"requires": (FactPredicate(fact_id="cue_gate", equals=True),)})
                if "1A" in item.available_in_scenes
                and any(
                    effect.op == "assert" and effect.fact_id == "continuity_initiative_known"
                    for effect in item.establishes
                )
                else item
                for item in package.knowledge.knowledge
            )
        }
    )
    delivery = next(item for item in package.deliveries if item.fact_id == "continuity_initiative_known")
    if remove_costs:
        delivery = delivery.model_copy(update={"costs": ()})
    elif retract_costs:
        delivery = delivery.model_copy(
            update={"costs": (RouteOperation(op="retract", fact_id="memory_card_recovered", value=True),)}
        )
    deliveries = tuple(delivery if item.fact_id == delivery.fact_id else item for item in package.deliveries)
    return package.model_copy(update={"knowledge": knowledge, "deliveries": deliveries})


def _state_1b(package=PACKAGE) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "1B")
    state._assert_scene_entry_fact("1B")
    state.scene_entered_at_turn = 0
    state.turn_index = 2
    state.facts.assert_fact(Fact(predicate="park_pursuit_resolved", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="trust_brandon", subject="story", value="true"))
    return state


def _package_gating_all_reveals_for(fact_id: str, gate_fact: str):
    knowledge = PACKAGE.knowledge.model_copy(
        update={
            "knowledge": tuple(
                item.model_copy(update={"requires": (FactPredicate(fact_id=gate_fact, equals=True),)})
                if "1B" in item.available_in_scenes
                and any(effect.op == "assert" and effect.fact_id == fact_id for effect in item.establishes)
                else item
                for item in PACKAGE.knowledge.knowledge
            )
        }
    )
    return PACKAGE.model_copy(update={"knowledge": knowledge})


def test_unavailable_first_ranked_cue_skips_to_next_available_cue() -> None:
    baseline = RuntimeEngine(_state_1b(), lambda _input: {"segments": []})._ranked_cue_fact_ids()
    package = _package_gating_all_reveals_for(baseline[0], "cue_gate")
    state = _state_1b(package)

    RuntimeEngine(state, lambda _input: {"segments": []})._activate_pacing()

    assert state.staged_cue_fact_id == baseline[1]


def test_1a_cue_is_available_from_its_assert_cost() -> None:
    state = _state_1a()

    assert RuntimeEngine(state, lambda _input: {"segments": []})._cue_reveal_available("continuity_initiative_known")


def test_1a_turn_1_stages_continuity_initiative_cue() -> None:
    state = _state_1a()
    state.turn_index = 1

    RuntimeEngine(state, lambda _input: {"segments": []})._activate_pacing()

    assert state.staged_cue_fact_id == "continuity_initiative_known"


def test_gated_own_fact_without_assert_cost_stays_hidden() -> None:
    package = _package_gating_all_reveals_for_1a(remove_costs=True)
    state = _state_1a(package)

    assert not RuntimeEngine(state, lambda _input: {"segments": []})._cue_reveal_available(
        "continuity_initiative_known"
    )


def test_retract_cost_does_not_widen_cue_availability() -> None:
    package = _package_gating_all_reveals_for_1a(retract_costs=True)
    state = _state_1a(package)

    assert not RuntimeEngine(state, lambda _input: {"segments": []})._cue_reveal_available(
        "continuity_initiative_known"
    )


def test_withheld_cue_stages_after_required_fact_is_asserted() -> None:
    baseline = RuntimeEngine(_state_1b(), lambda _input: {"segments": []})._ranked_cue_fact_ids()
    package = _package_gating_all_reveals_for(baseline[0], "cue_gate")
    state = _state_1b(package)
    engine = RuntimeEngine(state, lambda _input: {"segments": []})

    engine._activate_pacing()
    assert state.staged_cue_fact_id == baseline[1]

    state.facts.assert_fact(Fact(predicate="cue_gate", subject="story", value="true"))
    state.staged_cue_fact_id = None
    engine._activate_pacing()

    assert state.staged_cue_fact_id == baseline[0]


def test_delivery_fact_without_scene_reveal_is_staged() -> None:
    knowledge = PACKAGE.knowledge.model_copy(
        update={
            "knowledge": tuple(
                item.model_copy(
                    update={"available_in_scenes": tuple(scene for scene in item.available_in_scenes if scene != "1B")}
                )
                for item in PACKAGE.knowledge.knowledge
            )
        }
    )
    state = _state_1b(PACKAGE.model_copy(update={"knowledge": knowledge}))
    engine = RuntimeEngine(state, lambda _input: {"segments": []})

    engine._activate_pacing()

    assert state.staged_cue_fact_id == engine._ranked_cue_fact_ids()[0]


def test_staged_cue_with_unavailable_reveal_is_dropped() -> None:
    baseline = RuntimeEngine(_state_1b(), lambda _input: {"segments": []})._ranked_cue_fact_ids()
    package = _package_gating_all_reveals_for(baseline[0], "cue_gate")
    state = _state_1b(package)
    state.staged_cue_fact_id = baseline[0]

    RuntimeEngine(state, lambda _input: {"segments": []})._activate_pacing()

    assert state.staged_cue_fact_id == baseline[1]


def test_real_1b_does_not_stage_storm_drain_cue_before_brandon_is_identified() -> None:
    state = _state_1b()
    state.facts.retract_fact(Fact(predicate="park_pursuit_resolved", subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": []})

    engine._activate_pacing()

    assert state.staged_cue_fact_id != "park_pursuit_resolved"

    state.facts.assert_fact(Fact(predicate="brandon_identified", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="missing_may_be_alive", subject="story", value="true"))
    state.delivered_cue_ids = ("transport_route_identified",)
    state.staged_cue_fact_id = None
    engine._activate_pacing()

    assert state.staged_cue_fact_id == "park_pursuit_resolved"

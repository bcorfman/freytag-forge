from __future__ import annotations

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import NarrationSegment, TurnProposal
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.models import FactDelivery, RevealSource
from tests.test_boarding_engine_text import _real_boarding_engine, _synthetic_boarding_package
from tests.test_place_scoped_feed import _synthetic_package

BASE_CUE = "A clue waits in the workstation."


def _cue_package(*, reachable: bool = True, boarding: bool = False):
    package = _synthetic_boarding_package() if boarding else _synthetic_package()
    knowledge = package.knowledge.knowledge[0].model_copy(
        update={
            "source": RevealSource(kind="storylet_realization", storylet_id="SL-1A-A", realization_id="r1"),
            "reach_entity_ids": ("remote_statue",) if reachable else (),
        }
    )
    delivery = FactDelivery(
        fact_id="statue_known",
        scene_id="1A",
        source_kind="observation",
        must_convey=(("statue",), ("mark",)),
        fallback_text="The statue bears a blue mark.",
        cue_text=BASE_CUE,
    )
    return package.model_copy(
        update={
            "knowledge": package.knowledge.model_copy(update={"knowledge": (knowledge,)}),
            "knowledge_indexes": package.knowledge_indexes.model_copy(update={"by_id": {knowledge.id: knowledge}}),
            "deliveries": (delivery,),
        }
    )


def _stage(state: RuntimeState) -> None:
    state.active_event_ids.add("SL-1A-A")
    state.staged_cue_fact_id = "statue_known"
    state.staged_cue_stage = 1


def _narrator(state: RuntimeState) -> CloudflareTurnProvider:
    return CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)


def _item_provider(state: RuntimeState) -> ItemFactsProvider:
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider._selected_names = list(provider.item_facts)
    return provider


def test_staged_cue_is_suppressed_until_the_reveal_is_reachable() -> None:
    package = _cue_package()
    state = RuntimeState.bootstrap(package)
    _stage(state)
    provider = _narrator(state)
    proposal = TurnProposal(segments=(NarrationSegment(kind="narration", text="A quiet room."),))

    assert BASE_CUE in provider._compose_staged_cue(proposal).narration
    assert world_for(package, state.facts).move("hero", "yard").ok

    suppressed = provider._compose_staged_cue(proposal)
    assert BASE_CUE not in suppressed.narration
    assert state.staged_cue_fact_id == "statue_known"
    assert "statue_known" not in state.delivered_cue_ids

    assert world_for(package, state.facts).move("hero", "room").ok
    assert BASE_CUE in provider._compose_staged_cue(proposal).narration


def test_engine_text_path_keeps_an_unreachable_cue_staged() -> None:
    package = _cue_package(boarding=True)
    state = RuntimeState.bootstrap(package)
    _stage(state)
    assert world_for(package, state.facts).move("hero", "yard").ok
    provider = _item_provider(state)
    provider.command_consumed = True
    provider.prior_steps = ("Ari settles into the blue car.",)
    result = provider("Get in.")

    assert BASE_CUE not in TurnProposal.model_validate(result).narration
    assert state.staged_cue_fact_id == "statue_known"
    assert "statue_known" not in state.delivered_cue_ids

    assert world_for(package, state.facts).move("hero", "room").ok
    provider.command_consumed = True
    provider.prior_steps = ("Ari returns to the room.",)
    returned = provider("Return.")
    assert BASE_CUE in TurnProposal.model_validate(returned).narration


def test_cue_without_reach_requirement_is_unchanged() -> None:
    package = _cue_package(reachable=False)
    state = RuntimeState.bootstrap(package)
    _stage(state)
    assert world_for(package, state.facts).move("hero", "yard").ok

    proposal = TurnProposal(segments=(NarrationSegment(kind="narration", text="A quiet room."),))
    assert BASE_CUE in _narrator(state)._compose_staged_cue(proposal).narration


def test_continuity_cue_is_hidden_in_the_truck_but_available_in_the_house() -> None:
    state, provider, engine = _real_boarding_engine()
    package = state.package
    delivery = next(item for item in package.deliveries if item.fact_id == "continuity_initiative_known")
    state.staged_cue_fact_id = delivery.fact_id
    state.staged_cue_stage = 1

    result = engine.turn("Get in.")

    assert delivery.cue_text not in result.narration
    assert state.staged_cue_fact_id == delivery.fact_id
    assert delivery.fact_id not in state.delivered_cue_ids

    assert world_for(package, state.facts).move("kristin", "mcgehee_home").ok
    proposal = TurnProposal(segments=(NarrationSegment(kind="narration", text="The house is quiet."),))
    assert delivery.cue_text in provider._compose_staged_cue(proposal).narration

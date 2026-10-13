from __future__ import annotations

from pathlib import Path

from storygame.runtime.capture import WorldCapture
from storygame.runtime.fixed_refusal import refuse_fixed_move
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.jev_questions import relocates_thing
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state_and_world():
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "kitchen").ok
    return state, world


def _refusal(answer):
    state, world = _state_and_world()
    return (
        state,
        world,
        refuse_fixed_move(world, state.package, "Carry the workstation to the truck.", lambda *_: answer),
    )


def _provider(state):
    return ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )


def test_fixed_move_is_refused_without_changing_world():
    state, world, result = _refusal(True)
    assert result.steps == ("Kristin tried to move the workstation. It is fixed in place and did not move.",)
    assert result.refused == ("workstation",)
    assert world.parent("michelle_workstation") == "kitchen"


def test_fixed_move_false_and_unanswered_do_not_add_steps():
    _, _, false_result = _refusal(False)
    assert false_result.steps == ()
    assert false_result.refused == ()
    _, _, unanswered = _refusal(None)
    assert unanswered.steps == ()
    assert unanswered.issues == ("fixed move question unanswered for 'workstation'",)


def test_only_named_fixed_things_are_asked():
    state, world = _state_and_world()
    asked: list[str] = []

    def answer(_command, name):
        asked.append(name)
        return True

    result = refuse_fixed_move(world, state.package, "Carry my laptop.", answer)
    assert result.steps == ()
    assert asked == []

    result = refuse_fixed_move(world, state.package, "Carry the workstation and back door.", answer)
    assert len(result.steps) == 2
    assert asked == ["back door", "workstation"]


def test_relocates_thing_reads_noul_answer():
    def ask(_state, questions):
        key = next(iter(questions))
        return {key: {"noul": 0.8}}

    assert relocates_thing(ask, "Carry the workstation.", "workstation") is True
    assert (
        relocates_thing(lambda *_: {"relocates_thing": {"noul": 0.2}}, "Read the workstation.", "workstation") is False
    )
    assert relocates_thing(lambda *_: {}, "Read the workstation.", "workstation") is None


def test_capture_fixed_refusal_skips_other_prerequisites():
    state, world = _state_and_world()
    provider = _provider(state)
    requested: list[str] = []

    def ask(_state, questions):
        key = next(iter(questions))
        requested.append(key)
        return {key: {"noul": 0.8}}

    record = WorldCapture(provider, ask, fixed_refusal=True).before_turn("Carry the workstation to the truck.")
    step = "Kristin tried to move the workstation. It is fixed in place and did not move."
    assert record["steps"][0] == step
    assert provider.prior_steps[0] == step
    assert requested == ["relocates_thing"]
    assert world.parent("michelle_workstation") == "kitchen"


def test_capture_default_does_not_ask_relocation():
    state, _ = _state_and_world()
    provider = _provider(state)
    requested: list[str] = []

    def ask(_state, questions):
        key = next(iter(questions))
        requested.append(key)
        return {key: {"noul": 0.8}}

    WorldCapture(provider, ask).before_turn("Carry the workstation to the truck.")
    assert "relocates_thing" not in requested

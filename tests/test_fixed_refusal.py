from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.fixed_refusal import refuse_fixed_move
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.jev_questions import relocates_thing
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
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


def _real_scene_1a(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example/t")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "x")
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1A"
    apply_scene_placements(PACKAGE, state.facts, "1A")
    provider = build_capture_provider(state)
    provider._ensure_scene_seeded()
    return provider, provider._world()


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


def test_real_scene_1a_same_area_is_the_legacy_fixed_scope(monkeypatch: pytest.MonkeyPatch):
    provider, world = _real_scene_1a(monkeypatch)

    assert world.area(provider.state.package.protagonist_id) != world.area(world.resolve("workstation"))
    result = refuse_fixed_move(world, provider.state.package, "Carry the workstation to the truck.", lambda *_: True)
    assert result.asked is False


@pytest.mark.parametrize(
    ("command", "name", "expected_steps"),
    [
        (
            "Carry the workstation to the truck.",
            "workstation",
            ("Kristin tried to move the workstation. It is fixed in place and did not move.",),
        ),
        (
            "Detach the driver's seat from the truck.",
            "driver's seat",
            ("Kristin tried to move driver's seat. It is fixed in place and did not move.",),
        ),
        (
            "Extract the drawer from the workstation.",
            "drawer",
            (
                "Kristin tried to move the drawer. It is fixed in place and did not move.",
                "Kristin tried to move the workstation. It is fixed in place and did not move.",
            ),
        ),
    ],
)
def test_real_scene_1a_in_scope_refuses_fixed_moves(monkeypatch: pytest.MonkeyPatch, command, name, expected_steps):
    provider, world = _real_scene_1a(monkeypatch)
    result = refuse_fixed_move(
        world,
        provider.state.package,
        command,
        lambda *_: True,
        in_scope=lambda item_id: provider._name_in_scene_scope(world, world.name(item_id)),
    )

    assert result.steps == expected_steps
    assert any(name in step for step in result.steps)


def test_capture_real_scene_1a_fixed_refusal_precedes_other_questions(monkeypatch: pytest.MonkeyPatch):
    provider, world = _real_scene_1a(monkeypatch)
    requested: list[str] = []

    def ask(_state, questions):
        key = next(iter(questions))
        requested.append(key)
        return {key: {"noul": 1.0}}

    with patch.object(CloudflareTurnProvider, "_request", return_value={"refers": ["workstation"], "same_as": {}}):
        capture = WorldCapture(provider, ask, fixed_refusal=True)
        record = capture.before_turn("Carry the workstation to the truck.")

    step = "Kristin tried to move the workstation. It is fixed in place and did not move."
    assert record["steps"][0] == step
    assert provider.prior_steps[:1] == (step,)
    prompt = provider.assemble_turn_prompt("Carry the workstation to the truck.")
    rendered = prompt.get("user") or provider._section_user_prompt(prompt["context"])
    assert "Just before this: Kristin tried to move the workstation." in rendered
    assert requested == ["relocates_thing"]
    assert world.parent("michelle_workstation") == "kitchen"


def test_real_scene_1a_false_fixed_refusal_does_not_prepend_prompt(monkeypatch: pytest.MonkeyPatch):
    provider, _ = _real_scene_1a(monkeypatch)

    def ask(_state, questions):
        key = next(iter(questions))
        return {key: {"noul": 0.0}}

    with patch.object(CloudflareTurnProvider, "_request", return_value={"refers": ["workstation"], "same_as": {}}):
        capture = WorldCapture(provider, ask, fixed_refusal=True)
        capture.before_turn("Examine the workstation.")

    prompt = provider.assemble_turn_prompt("Examine the workstation.")
    rendered = prompt.get("user") or provider._section_user_prompt(prompt["context"])
    assert "Just before this:" not in rendered

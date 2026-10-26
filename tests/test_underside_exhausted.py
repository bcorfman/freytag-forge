from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package import load_story_package
from storygame.story_package.models import ItemPlacement
from tests.test_observation_preview import _synthetic_package
from tests.test_voiceable_knowledge import _real_recovery_state

ROOT = Path(__file__).parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
UNDERSIDE_LINE = "- Nothing else is under the {name}. Searching under the {name} finds nothing more."


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _synthetic_underside_package(*, under: bool = True):
    package = _synthetic_package()
    scene = package.scenes[0]
    placements = dict(scene.metadata.item_placements)
    placements["lens"] = ItemPlacement(parent="tray", under=under)
    metadata = scene.metadata.model_copy(update={"item_placements": placements})
    updated_scene = scene.model_copy(update={"metadata": metadata})
    return package.model_copy(update={"scenes": (updated_scene,)})


def _provider(package, focus: str):
    state = RuntimeState.bootstrap(package)
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.observation_request = ObservationRequest(f"Search beneath the {focus}.", "look", focus)
    return state, provider


def _prompt(provider: ItemFactsProvider) -> str:
    return provider._section_user_prompt({})


def test_synthetic_under_item_keeps_underside_open_until_moved() -> None:
    state, provider = _provider(_synthetic_underside_package(), "tray")
    world = world_for(state.package, state.facts)

    assert UNDERSIDE_LINE.format(name="survey tray") not in _prompt(provider)
    assert world.move("lens", "hero").ok
    prompt = _prompt(provider)
    assert prompt.count(UNDERSIDE_LINE.format(name="survey tray")) == 1


def test_synthetic_item_moved_back_under_focus_removes_underside_line() -> None:
    state, provider = _provider(_synthetic_underside_package(), "tray")
    world = world_for(state.package, state.facts)

    assert world.move("lens", "hero").ok
    assert UNDERSIDE_LINE.format(name="survey tray") in _prompt(provider)
    assert world.move("lens", "tray", under=True).ok
    assert UNDERSIDE_LINE.format(name="survey tray") not in _prompt(provider)


def test_synthetic_other_focus_and_scene_without_under_placements_never_get_line() -> None:
    state, provider = _provider(_synthetic_underside_package(), "room")
    world = world_for(state.package, state.facts)
    assert world.move("lens", "hero").ok
    assert UNDERSIDE_LINE.format(name="survey tray") not in _prompt(provider)

    state, provider = _provider(_synthetic_underside_package(under=False), "tray")
    world = world_for(state.package, state.facts)
    assert world.move("lens", "hero").ok
    assert UNDERSIDE_LINE.format(name="survey tray") not in _prompt(provider)


def test_continuity_drawer_underside_is_derived_from_current_world() -> None:
    state, provider = _provider(PACKAGE, "michelle_drawer")
    world = world_for(state.package, state.facts)
    line = UNDERSIDE_LINE.format(name="drawer")

    assert line not in _prompt(provider)
    assert world.reveal("memory_card").ok
    assert world.move("memory_card", "kristin").ok
    assert _prompt(provider).count(line) == 1
    assert world.move("memory_card", "michelle_drawer", under=True).ok
    assert line not in _prompt(provider)


@pytest.mark.parametrize("focus", ("michelle_workstation", "kristin_truck"))
def test_continuity_unrelated_focus_never_gets_drawer_underside_line(focus: str) -> None:
    state, provider = _provider(PACKAGE, focus)
    world = world_for(state.package, state.facts)
    assert world.reveal("memory_card").ok
    assert world.move("memory_card", "kristin").ok

    assert UNDERSIDE_LINE.format(name="drawer") not in _prompt(provider)


def test_another_thing_still_under_the_focus_keeps_underside_open() -> None:
    state, provider = _provider(_synthetic_underside_package(), "tray")
    world = world_for(state.package, state.facts)
    assert world.move("lens", "hero").ok
    assert world.move("remote_marker", "tray", under=True).ok

    assert UNDERSIDE_LINE.format(name="survey tray") not in _prompt(provider)


def test_no_observation_request_never_gets_underside_line() -> None:
    state, provider = _provider(_synthetic_underside_package(), "tray")
    world = world_for(state.package, state.facts)
    assert world.move("lens", "hero").ok
    provider.observation_request = None

    assert "Nothing else is under" not in _prompt(provider)


def test_complete_empty_scope_and_exhausted_underside_give_both_lines_in_order() -> None:
    package = _synthetic_underside_package()
    items = tuple(
        item.model_copy(update={"contents_complete": True}) if item.id == "tray" else item
        for item in package.world.items
    )
    package = package.model_copy(update={"world": package.world.model_copy(update={"items": items})})
    state, provider = _provider(package, "tray")
    world = world_for(state.package, state.facts)
    assert world.move("lens", "hero").ok

    prompt = _prompt(provider)
    scope_line = "- Nothing is left in or under the survey tray. Searching the survey tray finds nothing."
    underside_line = UNDERSIDE_LINE.format(name="survey tray")
    assert prompt.count(scope_line) == 1
    assert prompt.count(underside_line) == 1
    assert prompt.index(scope_line) < prompt.index(underside_line)


def test_real_recovered_drawer_prompt_has_underside_line_and_no_recovery_cue() -> None:
    state = _real_recovery_state(witnessed=True)
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.observation_request = ObservationRequest("Feel under the drawer.", "look", "michelle_drawer")

    context = provider.assemble_turn_prompt("Feel under the drawer.")["context"]
    prompt = provider._section_user_prompt(context)

    assert UNDERSIDE_LINE.format(name="drawer") in prompt
    assert "may say this aloud: Kristin finds Michelle" not in prompt

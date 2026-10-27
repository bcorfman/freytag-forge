from __future__ import annotations

import pytest

from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_verifier import relations_from_context
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.models import Item, ItemPlacement
from tests.test_observation_preview import _synthetic_package
from tests.test_observation_prompt import PACKAGE, _capture_drawer_observation_prompt, boarding_probe

OPEN_LINE = "- If the drawer opens, show what is inside it: binder clips, pens, spare batteries, stapler."


@pytest.fixture(autouse=True)
def fake_worker_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example")


def _provider(package, request: ObservationRequest | None):
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
    provider.observation_request = request
    return state, provider


def _synthetic_locker_package(*, contents: bool = True):
    package = _synthetic_package()
    scene = package.scenes[0]
    items = list(package.world.items)
    locker_contents = ["field manual", "copper key"] if contents else []
    items[0] = items[0].model_copy(
        update={
            "name": "iron locker",
            "kind": "container",
            "openable": True,
            "open": False,
            "contents": locker_contents,
        }
    )
    items.append(Item(id="sealed_blueprint", name="sealed blueprint", hidden=True))
    world = package.world.model_copy(update={"items": items})
    metadata = scene.metadata.model_copy(
        update={
            "item_ids": ("tray", "sealed_blueprint"),
            "item_placements": {
                "tray": ItemPlacement(parent="room"),
                "remote_marker": ItemPlacement(parent="yard"),
                "sealed_blueprint": ItemPlacement(parent="tray", under=True),
            },
        }
    )
    scene = scene.model_copy(update={"metadata": metadata})
    return package.model_copy(update={"world": world, "scenes": (scene,)})


def test_closed_real_drawer_gets_conditional_public_contents_line() -> None:
    _state, provider = _provider(
        PACKAGE,
        ObservationRequest("Open the drawer.", "open", "michelle_drawer"),
    )
    user = provider._section_user_prompt({})

    assert OPEN_LINE in user
    assert "- Show these in your reply:" not in user
    assert "Michelle's memory card" not in user
    assert user.index(OPEN_LINE) > user.index("CONSTRAINTS:")


def test_open_real_drawer_uses_normal_required_line_only() -> None:
    state, provider = _provider(PACKAGE, ObservationRequest("Open the drawer.", "open", "michelle_drawer"))
    world = world_for(PACKAGE, state.facts)
    assert world.set_axis("michelle_drawer", "open").ok

    prompt = provider._section_user_prompt({})

    assert "- Show these in your reply: binder clips, pens, spare batteries, stapler." in prompt
    assert "If the drawer opens" not in prompt


def test_only_open_requests_get_conditional_line() -> None:
    for request in (
        ObservationRequest("Look at the drawer.", "look", "michelle_drawer"),
        ObservationRequest("Enter the drawer.", "enter", "michelle_drawer"),
    ):
        _state, provider = _provider(PACKAGE, request)
        assert "If the drawer opens" not in provider._section_user_prompt({})


def test_closed_container_without_public_contents_gets_no_line() -> None:
    _state, provider = _provider(
        _synthetic_locker_package(contents=False),
        ObservationRequest("Open the locker.", "open", "tray"),
    )

    assert "If the iron locker opens" not in provider._section_user_prompt({})


def test_synthetic_closed_locker_names_public_contents_and_omits_hidden_item() -> None:
    _state, provider = _provider(
        _synthetic_locker_package(),
        ObservationRequest("Open the locker.", "open", "tray"),
    )

    prompt = provider._section_user_prompt({})

    assert "- If the iron locker opens, show what is inside it: copper key, field manual." in prompt
    assert "sealed blueprint" not in prompt
    assert "- Show these in your reply:" not in prompt


def test_closed_container_contents_are_conditional_not_visible_before_opening() -> None:
    _state, provider = _provider(
        _synthetic_locker_package(),
        ObservationRequest("Open the locker.", "open", "tray"),
    )

    before_constraints = provider._section_user_prompt({}).split("CONSTRAINTS:", 1)[0]

    assert "field manual" not in before_constraints
    assert "copper key" not in before_constraints


def test_post_open_required_relations_match_open_obligation() -> None:
    state, provider = _provider(
        _synthetic_locker_package(),
        ObservationRequest("Open the locker.", "open", "tray"),
    )
    world = world_for(state.package, state.facts)
    assert world.set_axis("tray", "open").ok

    context = provider._observation_context(world)
    relations = relations_from_context(context)

    assert context.required == ("copper key", "field manual")
    assert tuple(relation.thing for relation in relations) == ("copper key", "field manual")


def test_observation_mode_off_keeps_prompt_unchanged(tmp_path) -> None:
    user, package = _capture_drawer_observation_prompt(
        tmp_path,
        contents_complete=False,
        request=None,
    )
    expected = boarding_probe._control_prompt(package, "kitchen", "Search beneath the drawer.")["user"]

    assert user == expected

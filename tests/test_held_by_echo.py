from __future__ import annotations

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from tests.test_place_scoped_feed import _synthetic_package


def _provider(monkeypatch: pytest.MonkeyPatch) -> ItemFactsProvider:
    package = _synthetic_package()
    state = RuntimeState.bootstrap(package)
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: {"same_as": {}})
    return ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
        state_axes={"lamp": {"dark": [], "bright": []}},
    )


def test_unchanged_place_echo_keeps_custody_and_applies_state(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider(monkeypatch)
    world = provider._world()
    assert world.parent("lamp") == "room"

    facts, issues = provider.apply_item_facts(
        {
            "lamp": {
                "place": "room",
                "held_by": "Ari",
                "state": "bright",
                "condition": ["warm"],
            }
        }
    )

    assert issues == []
    world = provider._world()
    assert world.parent("lamp") == "room"
    assert facts["lamp"]["place"] == "the room"
    assert facts["lamp"]["condition"] == ["bright", "warm"]
    assert world.axis_values("lamp")["dark"] == "bright"
    assert world.conditions("lamp") == ("warm",)


@pytest.mark.parametrize("place", [None, "Ari"])
def test_real_pickup_still_moves_item_to_holder(place: str | None, monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider(monkeypatch)
    world = provider._world()
    entry = {"held_by": "Ari"}
    if place is not None:
        entry["place"] = place

    facts, issues = provider.apply_item_facts({"lamp": entry})

    assert issues == []
    world = provider._world()
    assert world.parent("lamp") == "hero"
    assert facts["lamp"]["place"] == "Ari"


def test_held_by_with_different_place_still_moves_to_that_place(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider(monkeypatch)
    world = provider._world()

    facts, issues = provider.apply_item_facts({"lamp": {"place": "yard", "held_by": "Ari"}})

    assert issues == []
    world = provider._world()
    assert world.parent("lamp") == "yard"
    assert facts["lamp"]["place"] == "the yard"


def test_unchanged_place_echo_drops_unknown_holder(monkeypatch: pytest.MonkeyPatch) -> None:
    provider = _provider(monkeypatch)

    facts, issues = provider.apply_item_facts({"lamp": {"place": "room", "held_by": "Mira", "state": "bright"}})

    assert issues == []
    world = provider._world()
    assert world.parent("lamp") == "room"
    assert facts["lamp"]["place"] == "the room"

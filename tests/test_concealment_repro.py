"""Characterization of the memory-card discovery, custody, and visibility paths."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CARD_NAME = "Michelle's memory card"


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _narration_response(text: str = "The scene continues.") -> dict[str, str]:
    return {"narration": json.dumps({"segments": [{"kind": "narration", "text": text}], "selected_knowledge_ids": []})}


def _discovered_state(monkeypatch: pytest.MonkeyPatch) -> tuple[RuntimeState, list[dict[str, object]]]:
    requests: list[dict[str, object]] = []

    def urlopen(request: object, **_kwargs: object) -> _Response:
        requests.append(json.loads(request.data))
        return _Response(_narration_response())

    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", urlopen)
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.update({"SL-1A-E", "SL-1A-F"})
    world = world_for(PACKAGE, state.facts)
    assert {
        "hidden": world.is_hidden("memory_card"),
        "parent": world.parent("memory_card"),
        "relation": world.relation("memory_card"),
        "visible": world.is_visible("memory_card"),
    } == {"hidden": True, "parent": "michelle_drawer", "relation": "under", "visible": False}

    result = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    ).turn("Search the gap beneath the drawer.")

    assert result.selected_knowledge_ids == ("k_sl_1a_b_r0",)
    return state, requests


def _card_facts(state: RuntimeState) -> tuple[tuple[str, str | None, str | None, str | None], ...]:
    return tuple(
        sorted(
            (fact.predicate, fact.subject, fact.object, fact.value)
            for fact in state.facts.asserted
            if fact.subject == "memory_card" or fact.predicate == "memory_card_recovered"
        )
    )


def test_discovery_removes_hidden_fact_and_carries_card(monkeypatch: pytest.MonkeyPatch) -> None:
    state, requests = _discovered_state(monkeypatch)
    world = world_for(PACKAGE, state.facts)

    assert _card_facts(state) == (
        ("memory_card_recovered", "story", None, "true"),
        ("wk_parent", "memory_card", None, "kristin"),
        ("wk_place_text", "memory_card", None, "with Kristin"),
        ("wk_relation", "memory_card", None, "carried_by"),
    )
    assert {
        "hidden": world.is_hidden("memory_card"),
        "parent": world.parent("memory_card"),
        "relation": world.relation("memory_card"),
        "holder": world.holder("memory_card"),
        "visible": world.is_visible("memory_card"),
    } == {
        "hidden": False,
        "parent": "kristin",
        "relation": "carried_by",
        "holder": "kristin",
        "visible": True,
    }
    assert len(requests) == 1


def test_item_facts_move_card_without_rehiding(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _requests = _discovered_state(monkeypatch)
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )

    taken, take_issues = provider.apply_item_facts(
        {CARD_NAME: {"held_by": "Kristin"}},
        player_input="Kristin pockets the memory card.",
        story="Kristin pockets the memory card.",
    )
    world = world_for(PACKAGE, state.facts)
    assert take_issues == []
    assert taken[CARD_NAME]["place"] == "Kristin"
    assert (world.parent("memory_card"), world.relation("memory_card"), world.is_hidden("memory_card")) == (
        "kristin",
        "carried_by",
        False,
    )

    under_seat, under_issues = provider.apply_item_facts(
        {CARD_NAME: {"place": "passenger seat", "under": True}},
        player_input="Kristin hides the card under the passenger seat.",
        story="Kristin hides the card under the passenger seat.",
    )
    world = world_for(PACKAGE, state.facts)
    assert under_issues == []
    assert under_seat[CARD_NAME]["place"] == "passenger seat"
    assert (world.parent("memory_card"), world.relation("memory_card"), world.is_hidden("memory_card")) == (
        "truck_passenger_seat",
        "under",
        False,
    )
    assert world.is_visible("memory_card")


def test_unresolved_glovebox_is_created_as_normal_container_move(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _requests = _discovered_state(monkeypatch)

    def urlopen(_request: object, **_kwargs: object) -> _Response:
        return _Response({"same_as": {"glovebox": "new"}, "kind": {"glovebox": "thing"}})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", urlopen)
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )

    facts, issues = provider.apply_item_facts(
        {CARD_NAME: {"place": "glovebox"}},
        player_input="Kristin hides the card in the glovebox.",
        story="Kristin hides the card in the glovebox.",
    )
    world = world_for(PACKAGE, state.facts)
    glovebox = world.resolve("glovebox")

    assert issues == []
    assert facts[CARD_NAME]["place"] == "glovebox"
    assert glovebox is not None
    assert world.parent("memory_card") == glovebox
    assert world.relation("memory_card") == "in"
    assert not world.is_hidden("memory_card")
    assert world.is_visible("memory_card")


def test_authored_place_operation_cannot_restore_discovery_hidden_fact(monkeypatch: pytest.MonkeyPatch) -> None:
    state, _requests = _discovered_state(monkeypatch)
    world = world_for(PACKAGE, state.facts)

    result = world.place("memory_card", "michelle_drawer", under=True)

    assert result.ok
    assert not world.is_hidden("memory_card")
    assert not any(fact.predicate == "wk_hidden" and fact.subject == "memory_card" for fact in state.facts.asserted)
    assert not hasattr(world, "hide")


def test_1b_narrator_request_omits_carried_card_and_npc_card_knowledge(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state, requests = _discovered_state(monkeypatch)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    apply_scene_placements(PACKAGE, state.facts, "1B")
    world = world_for(PACKAGE, state.facts)
    assert world.parent("memory_card") == "kristin"
    assert world.is_visible("memory_card")

    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    assembled = provider.assemble_turn_prompt("Talk to Brandon.")
    speaker_context = assembled["context"]["knowledge_context"]["speakers"]
    assert speaker_context["brandon"] == {"sayable_knowledge": []}
    assert CARD_NAME.casefold() not in json.dumps(speaker_context).casefold()

    provider("Talk to Brandon.")
    narrator_request = requests[-1]
    user_prompt = narrator_request["user"]
    assert "- Kristin. Place: Los Angeles park." in user_prompt
    assert "- Transit token. Place: park bench." in user_prompt
    assert CARD_NAME.casefold() not in user_prompt.casefold()

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider, capture_prompt_variant
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import RuntimeContractError
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from storygame.web_demo import create_demo_app

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _provider(state: RuntimeState, *responses: object) -> ItemFactsProvider:
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider._test_responses = list(responses)
    return provider


def _stub_request(monkeypatch: pytest.MonkeyPatch) -> None:
    def request(provider: ItemFactsProvider, _payload: object) -> object:
        return provider._test_responses.pop(0)

    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)


def _capture(state: RuntimeState, provider: ItemFactsProvider) -> WorldCapture:
    return WorldCapture(provider, lambda _state, questions: {next(iter(questions)): True})


def _turn(text: str = "The search continues.") -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": text}]}


def _state_1b() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    return state


def test_capture_off_changes_nothing() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = state.snapshot()
    result = RuntimeEngine(state, lambda _command: _turn()).turn("Search the kitchen.")

    assert result.narration == "The search continues."
    assert state.turn_index == before.turn_index + 1
    assert state.current_scene_id == before.current_scene_id
    assert state.pending_capture is None


def test_pickup_reaches_next_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _provider(
        state,
        {"refers": ["Michelle's phone"], "same_as": {}},
        {
            **_turn("Kristin picks up Michelle's phone."),
            "item_facts": {"Michelle's phone": {"held_by": "Kristin"}},
        },
        {"refers": ["Michelle's phone"], "same_as": {}},
        _turn("Kristin checks her pocket."),
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    engine.turn("Pick up Michelle's phone.")
    engine.turn("Check that I still have Michelle's phone.")

    assert "Michelle's phone" in provider._things_block(narration=True)
    assert "Held by: Kristin" in provider._things_block(narration=True)


def test_after_commit_records_facts_after(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _provider(
        state,
        {"refers": ["Michelle's phone"], "same_as": {}},
        {**_turn("Kristin finds Michelle's phone."), "item_facts": {"Michelle's phone": {"place": "kitchen"}}},
    )
    capture = _capture(state, provider)

    RuntimeEngine(state, provider, capture=capture).turn("Inspect Michelle's phone.")

    assert capture.last_after["facts_after"]["Michelle's phone"]["place"] == "kitchen"


def test_rejected_turn_changes_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "kitchen").ok
    assert world.move("kristin_laptop", "kitchen").ok
    before = state.snapshot()
    capture_provider = _provider(
        state,
        {"refers": ["Kristin's laptop"], "same_as": {}},
    )
    engine = RuntimeEngine(state, lambda _command: {"not": "a valid turn"}, capture=_capture(state, capture_provider))

    with pytest.raises(RuntimeContractError):
        engine.turn("Read the files on my laptop.")

    assert state.facts == before.facts
    assert state.snapshot() == before
    assert capture_provider.prior_steps == ()


def test_malformed_item_facts_are_recorded(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _provider(
        state,
        {"refers": ["Michelle's phone"], "same_as": {}},
        {**_turn(), "item_facts": {"Michelle's phone": {"place": {"bad": True}}}},
    )
    before = state.facts.clone()
    RuntimeEngine(state, provider, capture=_capture(state, provider)).turn("Inspect Michelle's phone.")

    assert world_for(PACKAGE, state.facts).parent("kristin") == world_for(PACKAGE, before).parent("kristin")
    assert any("Michelle's phone" in issue for issue in state.last_turn_delivery.capture_issues)


def test_game_break_proceed_applies_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _provider(
        state,
        {"refers": ["Michelle's phone"], "same_as": {}},
        {**_turn("Kristin picks up Michelle's phone."), "item_facts": {"Michelle's phone": {"held_by": "Kristin"}}},
    )
    capture = _capture(state, provider)
    engine = RuntimeEngine(state, provider, capture=capture)
    monkeypatch.setattr(engine.validator, "validate", lambda *_args: ("brandon",))

    proposal = engine.turn("Pick up Michelle's phone.")
    assert proposal.game_break is not None
    assert state.pending_capture is not None

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://example.invalid")
    resumed_provider = build_capture_provider(state)
    resumed = RuntimeEngine(state, lambda _command: _turn(), capture=_capture(state, resumed_provider))
    resumed.resolve_break("proceed")

    assert world_for(PACKAGE, state.facts).holder("michelle_phone") == "kristin"
    assert state.pending_capture is None


def test_captured_unavailable_pole_raises_game_break(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    provider = _provider(
        state,
        {"refers": ["Transit token"], "same_as": {}},
        {**_turn(), "item_facts": {"Transit token": {"state": "destroyed"}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    proposal = engine.turn("Inspect the transit token.")

    assert proposal.game_break is not None
    assert "transit_card" in proposal.game_break.affected_ids
    assert world_for(PACKAGE, state.facts).axis_values("transit_card")["intact"] == "intact"
    assert state.pending_break is not None


def test_captured_npc_unavailable_pole_raises_game_break(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    provider = _provider(
        state,
        {"refers": ["the man watching Kristin"], "same_as": {}},
        {**_turn(), "item_facts": {"the man watching Kristin": {"state": "unconscious"}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    proposal = engine.turn("Ask the man who he is.")

    assert proposal.game_break is not None
    assert "brandon" in proposal.game_break.affected_ids
    assert world_for(PACKAGE, state.facts).axis_values("brandon")["conscious"] == "conscious"


def test_captured_npc_conscious_state_raises_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    provider = _provider(
        state,
        {"refers": ["the man watching Kristin"], "same_as": {}},
        {**_turn(), "item_facts": {"the man watching Kristin": {"state": "conscious"}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    proposal = engine.turn("Ask the man who he is.")

    assert proposal.game_break is None
    assert state.pending_break is None


def test_list_state_sets_pole(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    provider = _provider(
        state,
        {"refers": ["Transit token"], "same_as": {}},
        {**_turn(), "item_facts": {"Transit token": {"state": ["broken"]}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    engine.turn("Inspect the transit token.")
    engine.resolve_break("proceed")

    assert world_for(PACKAGE, state.facts).axis_values("transit_card")["intact"] == "destroyed"


def test_list_state_unmatched_becomes_condition(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    provider = _provider(
        state,
        {"refers": ["Transit token"], "same_as": {}},
        {**_turn(), "item_facts": {"Transit token": {"state": ["broken into two pieces"]}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    proposal = engine.turn("Inspect the transit token.")

    assert proposal.game_break is None
    world = world_for(PACKAGE, state.facts)
    assert world.axis_values("transit_card")["intact"] == "intact"
    assert "broken into two pieces" in world.conditions("transit_card")


def test_captured_unavailable_pole_proceed_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    provider = _provider(
        state,
        {"refers": ["Transit token"], "same_as": {}},
        {**_turn(), "item_facts": {"Transit token": {"state": "destroyed"}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    engine.turn("Inspect the transit token.")
    engine.resolve_break("proceed")

    assert world_for(PACKAGE, state.facts).axis_values("transit_card")["intact"] == "destroyed"
    assert state.pending_break is None


def test_captured_non_dependency_axis_raises_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    provider = _provider(
        state,
        {"refers": ["Transit token"], "same_as": {}},
        {**_turn(), "item_facts": {"Transit token": {"state": "intact"}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    proposal = engine.turn("Inspect the transit token.")

    assert proposal.game_break is None
    assert state.pending_break is None


def test_already_unavailable_dependency_does_not_break_again(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = _state_1b()
    world_for(PACKAGE, state.facts).set_axis("transit_card", "destroyed")
    provider = _provider(state, {"refers": [], "same_as": {}}, _turn())
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))

    proposal = engine.turn("Search the park.")

    assert proposal.game_break is None
    assert state.pending_break is None


def test_game_break_return_discards_capture(monkeypatch: pytest.MonkeyPatch) -> None:
    _stub_request(monkeypatch)
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _provider(
        state,
        {"refers": ["Michelle's phone"], "same_as": {}},
        {**_turn(), "item_facts": {"Michelle's phone": {"held_by": "Kristin"}}},
    )
    engine = RuntimeEngine(state, provider, capture=_capture(state, provider))
    monkeypatch.setattr(engine.validator, "validate", lambda *_args: ("brandon",))
    before = state.facts.clone()

    engine.turn("Pick up Michelle's phone.")
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://example.invalid")
    resumed_provider = build_capture_provider(state)
    RuntimeEngine(state, lambda _command: _turn(), capture=_capture(state, resumed_provider)).resolve_break(
        "return_to_scene"
    )

    assert world_for(PACKAGE, state.facts).holder("michelle_phone") == world_for(PACKAGE, before).holder(
        "michelle_phone"
    )
    assert state.pending_capture is None


def test_capture_prompt_variant_matches_bench_default() -> None:
    variation = json.loads(Path("bench/variations/item-facts-world-two-scene.json").read_text())
    expected = {
        "include_output_example": True,
        "output_example": variation["system_prompt"]["output_example"],
        "beat_delivery": "details",
        "auto_select_unambiguous_candidates": True,
        "positive_selection_example": False,
        "model_grounding": True,
        "narrow_to_shadow_match": False,
        "constant_rules_in_system": True,
    }
    assert capture_prompt_variant(PACKAGE) == expected


def test_web_capture_flag(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    from storygame import web_demo

    class SpyCapture:
        made = 0

        def __init__(self, *_args: object) -> None:
            type(self).made += 1

        def before_turn(self, _command: str) -> dict[str, object]:
            return {}

        def discard(self) -> None:
            pass

        def after_commit(self, *_args: object, **_kwargs: object) -> dict[str, object]:
            return {"issues": [], "unplaced": [], "changed": []}

        def context(self) -> dict[str, object]:
            return {}

    monkeypatch.setattr(web_demo, "WorldCapture", SpyCapture)
    monkeypatch.setattr(web_demo, "build_capture_provider", lambda state: _provider(state))
    monkeypatch.setattr(
        web_demo,
        "JevClient",
        type("Jev", (), {"from_environment": staticmethod(lambda: type("C", (), {"ask": lambda *_: {}})())}),
    )

    monkeypatch.delenv("FREYTAG_WORLD_CAPTURE", raising=False)
    create_demo_app(store_path=tmp_path / "off.sqlite", provider_factory=lambda _state: lambda _command: _turn())
    assert SpyCapture.made == 0

    monkeypatch.setenv("FREYTAG_WORLD_CAPTURE", "1")
    create_demo_app(store_path=tmp_path / "on.sqlite", provider_factory=lambda _state: lambda _command: _turn())
    # Construction is lazy; exercise the endpoint that creates the engine.
    from fastapi.testclient import TestClient

    app = create_demo_app(
        store_path=tmp_path / "on2.sqlite",
        provider_factory=lambda _state: lambda _command: _turn(),
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/session", json={"story_id": "continuity_initiative"})
    assert response.status_code == 200
    assert SpyCapture.made > 0


def test_provider_gets_typed_command_not_added_steps() -> None:
    class StepCapture:
        def before_turn(self, command: str) -> dict[str, object]:
            return {"command": f"Kristin sat down. {command}", "steps": ["Kristin sat down."], "issues": []}

        def after_commit(self, *_args: object, **_kwargs: object) -> dict[str, object]:
            return {"issues": [], "unplaced": [], "changed": []}

        def context(self) -> dict[str, object]:
            return {}

        def discard(self) -> None:
            pass

    received: list[str] = []
    state = RuntimeState.bootstrap(PACKAGE)

    def provider(command: str) -> dict[str, object]:
        received.append(command)
        return _turn()

    RuntimeEngine(state, provider, capture=StepCapture()).turn("Read the files on my laptop.")

    assert received == ["Read the files on my laptop."]
    assert state.last_turn_delivery.capture_steps == ("Kristin sat down.",)

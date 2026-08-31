"""Two-stage pacing delivery and authored transition coverage."""

from __future__ import annotations

import json
from pathlib import Path

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState, TurnDelivery
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import ActivationRule

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _state_1b() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    state._assert_scene_entry_fact("1B")
    state.scene_entered_at_turn = 0
    state.turn_index = 2
    state.facts.assert_fact(Fact(predicate="park_pursuit_resolved", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="trust_brandon", subject="story", value="true"))
    return state


def _state_2a() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "2A"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "2A")
    state._assert_scene_entry_fact("2A")
    return state


def _fallback_delivery_text(state: RuntimeState) -> str:
    deliveries = {delivery.fact_id: delivery for delivery in PACKAGE.deliveries}
    return " ".join(deliveries[fact_id].fallback_text for fact_id in state.staged_handoff_fact_ids)


def test_ordinary_turn_records_no_delivery_recovery_or_fallback() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.last_turn_delivery = TurnDelivery(must_convey_misses=("previous_fact",), recovery_used=True)
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "I listen."}]})

    engine.turn("I listen.")

    assert state.last_turn_delivery == TurnDelivery()


def test_activation_rule_minimal_undelivered_facts_is_small_stable_and_non_repeating() -> None:
    rule = ActivationRule(
        all_facts_true=("mandatory_a", "mandatory_b"),
        any_of=("pool_a", "pool_b", "pool_c"),
        at_least=2,
    )

    assert rule.minimal_undelivered_facts({"mandatory_a", "pool_a"}) == ("mandatory_b", "pool_b")
    assert rule.minimal_undelivered_facts({"mandatory_a", "mandatory_b", "pool_a", "pool_b"}) == ()
    assert ActivationRule(any_of=("pool_a", "pool_b"), at_least=1).minimal_undelivered_facts(set()) == ("pool_a",)
    assert rule.minimal_undelivered_facts({"mandatory_a"}) == ("mandatory_b", "pool_a", "pool_b")
    assert rule.minimal_undelivered_facts({"mandatory_a"}) == rule.minimal_undelivered_facts({"mandatory_a"})


def test_hint_then_handoff_delivers_only_missing_facts_costs_and_transition() -> None:
    state = _state_1b()
    responses = iter(({"segments": [{"kind": "narration", "text": "A clue catches my attention."}]},))
    calls = 0

    def provider(_input: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return next(responses)
        return {"segments": [{"kind": "narration", "text": _fallback_delivery_text(state)}]}

    engine = RuntimeEngine(state, provider)

    hint = engine.turn("I wait and listen.")
    assert state.staged_hint_fact_ids == ("transport_route_identified", "brandon_identified")
    assert state.staged_handoff_fact_ids == ()
    assert not state.facts.has("transport_route_identified", "story", value="true")
    assert hint.segments[0].text == "A clue catches my attention."
    assert state.last_turn_delivery.hint_staged is True
    assert state.last_turn_delivery.handoff_staged is False

    handoff = engine.turn("I keep watching the park.")
    assert state.current_scene_id == "1C"
    assert not state.facts.has("trust_brandon", "story", value="true")
    assert state.facts.has("transport_route_identified", "story", value="true")
    assert state.facts.has("brandon_identified", "story", value="true")
    assert state.facts.has("transport_route_departure_ready", "story", value="true")
    assert state.staged_hint_fact_ids == ()
    assert state.staged_handoff_fact_ids == ()
    assert state.last_turn_delivery.hint_staged is True
    assert state.last_turn_delivery.handoff_staged is True
    texts = [segment.text for segment in handoff.segments]
    source_bridge = next(
        scene.metadata.bridge_text["t_1b_1c"] for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B"
    )
    target_entry = next(scene.metadata.entry_text for scene in PACKAGE.scenes if scene.metadata.scene_id == "1C")
    assert texts.index(source_bridge) < texts.index(target_entry)


def test_scene_2a_handoff_asserts_hidden_bridge_fact_without_projecting_it() -> None:
    state = _state_2a()
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "I wait."}]})

    engine.turn("I wait at the facility entrance.")
    engine.turn("I keep watching the security desk.")
    handoff = engine.turn("I wait for an opening.")

    assert state.current_scene_id == "2B"
    assert state.facts.has("false_identities_ready", "story", value="true")
    assert state.facts.has("rebecca_observing_infiltrators", "story", value="true")
    assert "bridge_2a_restricted_access" in state.fired_event_ids
    assert state.last_turn_delivery.handoff_staged is True
    assert any("false credentials" in segment.text.casefold() for segment in handoff.segments)

    projection = KnowledgeProjector().project(state, "player", "I look around.")
    projected_ids = {item.id for item in (*projection.committed_knowledge, *projection.candidates)}
    assert "k_sl_2a_c_r2_rebecca_observes" not in projected_ids
    assert "rebecca_observing_infiltrators" not in projection.model_dump_json()


def test_projected_handoff_contract_is_player_safe_and_prompt_preserves_agency(monkeypatch) -> None:
    state = _state_1b()
    state.staged_hint_fact_ids = ("transport_route_identified",)
    state.staged_handoff_fact_ids = ("transport_route_identified",)
    captured: dict[str, object] = {}

    def open_request(request, **_kwargs: object) -> _Response:
        captured["payload"] = json.loads(request.data)
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"I keep watch."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider("I keep watch.")
    projection = KnowledgeProjector().project(state, "player", "I keep watch.")
    assert [item.fact_id for item in projection.hinted_deliveries] == ["transport_route_identified"]
    assert [item.fact_id for item in projection.handoff_deliveries] == ["transport_route_identified"]
    serialized = json.dumps(captured["payload"]).casefold()
    assert "rebecca_observing_infiltrators" not in serialized
    assert "this is a handoff turn" in captured["payload"]["system"].casefold()
    assert "do not claim that the player took an action they did not take" in captured["payload"]["system"].casefold()
    state.staged_handoff_fact_ids = ()
    provider("I keep watch.")
    assert "this is a hint turn" in captured["payload"]["system"].casefold()


def test_conveying_handoff_uses_one_worker_request_without_recovery_or_fallback(monkeypatch) -> None:
    state = _state_1b()
    state.staged_handoff_fact_ids = ("transport_route_identified",)
    payloads: list[dict[str, object]] = []
    delivery = next(item for item in PACKAGE.deliveries if item.fact_id == "transport_route_identified")

    def open_request(request, **_kwargs: object) -> _Response:
        payloads.append(json.loads(request.data))
        return _Response(
            {"narration": json.dumps({"segments": [{"kind": "narration", "text": delivery.fallback_text}]})}
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    response = provider("I keep watching the park.")

    assert len(payloads) == 1
    assert response["segments"][0]["text"] == delivery.fallback_text
    assert state.last_turn_delivery.must_convey_misses == ()
    assert state.last_turn_delivery.recovery_used is False
    assert state.last_turn_delivery.fallback_used is False
    assert state.last_turn_delivery.handoff_staged is True


def test_handoff_recovery_names_missed_groups_and_falls_back_to_authored_text(monkeypatch) -> None:
    state = _state_1b()
    state.staged_handoff_fact_ids = ("transport_route_identified",)
    payloads: list[dict[str, object]] = []
    delivery = next(item for item in PACKAGE.deliveries if item.fact_id == "transport_route_identified")

    def open_request(request, **_kwargs: object) -> _Response:
        payloads.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"I wait."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    response = provider("I wait.")
    assert len(payloads) == 2
    assert delivery.must_convey[0][0] in payloads[1]["system"]
    assert response["segments"][0]["text"] == delivery.fallback_text
    assert state.last_turn_delivery.must_convey_misses == (delivery.fact_id,)
    assert state.last_turn_delivery.recovery_used is True
    assert state.last_turn_delivery.fallback_used is True
    assert state.last_turn_delivery.handoff_staged is True


def test_valid_handoff_recovery_is_accepted_once_and_keeps_direct_response(monkeypatch) -> None:
    state = _state_1b()
    state.staged_handoff_fact_ids = ("transport_route_identified",)
    payloads: list[dict[str, object]] = []
    delivery = next(item for item in PACKAGE.deliveries if item.fact_id == "transport_route_identified")
    text = "I search the route. " + delivery.fallback_text

    def open_request(request, **_kwargs: object) -> _Response:
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response({"narration": '{"segments":[{"kind":"narration","text":"I search the route."}]}'})
        return _Response({"narration": json.dumps({"segments": [{"kind": "narration", "text": text}]})})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    response = provider("I search the route.")
    assert len(payloads) == 2
    assert response["segments"][0]["text"] == text

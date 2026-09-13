"""Two-stage pacing delivery and authored transition coverage."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import ResolvedTurnProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState, TurnDelivery
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    ActivationRule,
    FactPredicate,
    PacingEvent,
    PacingRealization,
    RouteOperation,
    RouteRealization,
    StoryletRoute,
)

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
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Listen."}]})

    engine.turn("Listen.")

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


def _synthetic_pacing_package(realizations: tuple[PacingRealization, ...], when: tuple[FactPredicate, ...] = ()):
    event = PacingEvent(
        id="synthetic_pressure",
        scene_id="1A",
        at_turn=1,
        effects=(FactPredicate(fact_id="patrol_return_pressure", equals=True),),
        when=when,
        realizations=realizations,
    )
    pacing = PACKAGE.pacing.model_copy(update={"events": (event,)})
    return PACKAGE.model_copy(update={"pacing": pacing})


def test_pacing_realization_selects_first_matching_entry_and_default_fallback() -> None:
    realizations = (
        PacingRealization(
            when=(FactPredicate(fact_id="memory_card_in_kristins_custody", equals=True),),
            text="The first pressure is visible.",
        ),
        PacingRealization(
            when=(FactPredicate(fact_id="memory_card_in_kristins_custody", equals=True),),
            text="The second pressure is visible.",
        ),
        PacingRealization(text="The default pressure is visible."),
    )

    matching_package = _synthetic_pacing_package(realizations)
    matching_state = RuntimeState.bootstrap(matching_package)
    matching_state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    RuntimeEngine(
        matching_state, lambda _input: {"segments": [{"kind": "narration", "text": "Search the kitchen."}]}
    ).turn("Search the kitchen.")
    assert matching_state.last_turn_delivery.complication_text == "The first pressure is visible."

    fallback_state = RuntimeState.bootstrap(_synthetic_pacing_package(realizations))
    RuntimeEngine(
        fallback_state, lambda _input: {"segments": [{"kind": "narration", "text": "Search the kitchen."}]}
    ).turn("Search the kitchen.")
    assert fallback_state.last_turn_delivery.complication_text == "The default pressure is visible."


def test_guarded_pacing_event_waits_for_its_predicates_even_after_at_turn() -> None:
    package = _synthetic_pacing_package(
        (PacingRealization(text="The guarded pressure is visible."),),
        when=(FactPredicate(fact_id="memory_card_in_kristins_custody", equals=True),),
    )
    state = RuntimeState.bootstrap(package)
    state.turn_index = 2
    engine = RuntimeEngine(state, lambda _input: {"segments": []})

    engine._activate_pacing(realize_complications=True)

    assert "synthetic_pressure" not in state.fired_event_ids
    assert Fact(predicate="patrol_return_pressure", subject="story", value="true") not in state.facts.asserted
    assert state.last_turn_delivery.complication_text is None

    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    engine._activate_pacing(realize_complications=True)

    assert "synthetic_pressure" in state.fired_event_ids
    assert Fact(predicate="patrol_return_pressure", subject="story", value="true") in state.facts.asserted
    assert state.last_turn_delivery.complication_text == "The guarded pressure is visible."


def test_guarded_pacing_event_never_fires_before_at_turn() -> None:
    package = _synthetic_pacing_package(
        (PacingRealization(text="The guarded pressure is visible."),),
        when=(FactPredicate(fact_id="memory_card_in_kristins_custody", equals=True),),
    )
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": []})

    engine._activate_pacing(realize_complications=True)

    assert "synthetic_pressure" not in state.fired_event_ids
    assert state.last_turn_delivery.complication_text is None

    state.turn_index = 1
    engine._activate_pacing(realize_complications=True)

    assert "synthetic_pressure" in state.fired_event_ids


@pytest.mark.parametrize(
    ("facts", "expected_index"),
    [
        ((), 0),
        ((("memory_card_in_kristins_custody", True),), 2),
        (
            (
                ("memory_card_in_kristins_custody", True),
                ("michelle_lead_actionable", True),
            ),
            1,
        ),
    ],
)
def test_pressure_1a_prompt_carries_one_matching_realization_for_one_turn(
    monkeypatch, facts: tuple[tuple[str, bool], ...], expected_index: int
) -> None:
    captured: list[str] = []

    def open_request(request, **_kwargs: object) -> _Response:
        captured.append(request.data.decode())
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The house is quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    for fact_id, value in facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value=str(value).lower()))
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )

    expected = PACKAGE.pacing.events[0].realizations[expected_index].text
    all_texts = tuple(realization.text for realization in PACKAGE.pacing.events[0].realizations)
    engine.turn("Search the kitchen.")
    engine.turn("Check the back door.")
    engine.turn("Inspect the overturned chair.")

    assert all(text not in captured[0] for text in all_texts)
    assert captured[1].count(expected) == 1
    assert all(text not in captured[1] for text in all_texts if text != expected)
    assert expected not in captured[2]


def test_pressure_1a_lead_actionable_realization_precedes_custody() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="michelle_lead_actionable", subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Search the kitchen."}]})

    engine.turn("Search the kitchen.")
    engine.turn("Check the back door.")
    assert state.last_turn_delivery.complication_text == PACKAGE.pacing.events[0].realizations[1].text


def test_resolution_pacing_realization_reaches_narrator_when_escalation_is_gated(monkeypatch) -> None:
    captured: list[str] = []

    def open_request(request, **_kwargs: object) -> _Response:
        captured.append(request.data.decode())
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"Keep moving."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3C")
    state = RuntimeState(package=PACKAGE, current_scene_id="3C", phase=scene.metadata.freytag_phase)
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )

    engine.turn("Keep moving toward the stairs.")
    engine.turn("Help the captives up the stairs.")

    assert PACKAGE.pacing.events[4].realizations[0].text in captured[1]


def test_unfired_pacing_event_does_not_cross_a_scene_exit() -> None:
    event = PacingEvent(
        id="late_pressure",
        scene_id="1A",
        at_turn=2,
        effects=(FactPredicate(fact_id="patrol_return_pressure", equals=True),),
        realizations=(PacingRealization(text="A late pressure appears."),),
    )
    package = PACKAGE.model_copy(update={"pacing": PACKAGE.pacing.model_copy(update={"events": (event,)})})
    state = RuntimeState.bootstrap(package)
    state.active_event_ids.add("SL-1A-A")
    state.apply_proposal(
        ResolvedTurnProposal(
            segments=({"kind": "narration", "text": "Leave the house."},),
            transition={"transition_id": "t_1a_1b"},
        )
    )
    RuntimeEngine(state, lambda _input: {"segments": []})._activate_pacing(realize_complications=True)

    assert "SL-1A-A" not in state.active_event_ids
    assert "late_pressure" not in state.fired_event_ids
    assert state.last_turn_delivery.complication_text is None


def test_cue_ranking_uses_eligible_source_windows_and_activation_conditions() -> None:
    def source(
        route_id: str, fact_id: str, latest_turn: int, conditions: tuple[FactPredicate, ...] = ()
    ) -> StoryletRoute:
        return StoryletRoute(
            id=route_id,
            scene_id="1B",
            title=f"Source for {fact_id}",
            activation_conditions=conditions,
            earliest_turn=0,
            target_turn=1,
            latest_turn=latest_turn,
            pressure_role="cue source",
            realizations=(
                RouteRealization(
                    id="R1",
                    dramatic_intent="show the source",
                    operations=(RouteOperation(op="assert", fact_id=fact_id, value=True),),
                ),
            ),
        )

    routes = PACKAGE.storylet_routes.model_copy(
        update={
            "storylets": (
                source("SL-1B-A", "transport_route_identified", 7),
                source(
                    "SL-1B-B",
                    "brandon_identified",
                    3,
                    (FactPredicate(fact_id="source_ready", equals=True),),
                ),
                source("SL-1B-C", "park_pursuit_resolved", 5),
            )
        }
    )
    package = PACKAGE.model_copy(update={"storylet_routes": routes})
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1B")
    state = RuntimeState(package=package, current_scene_id="1B", phase=scene.metadata.freytag_phase)
    state.facts.assert_fact(Fact(predicate="source_ready", subject="story", value="true"))

    engine = RuntimeEngine(state, lambda _input: {"segments": []})

    assert engine._ranked_cue_fact_ids() == (
        "brandon_identified",
        "park_pursuit_resolved",
        "transport_route_identified",
    )


def test_hint_then_handoff_delivers_only_missing_facts_costs_and_transition() -> None:
    state = _state_1b()
    state.turn_index = 3
    responses = iter(({"segments": [{"kind": "narration", "text": "A clue catches my attention."}]},))
    calls = 0

    def provider(_input: str) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            return next(responses)
        return {"segments": [{"kind": "narration", "text": _fallback_delivery_text(state)}]}

    engine = RuntimeEngine(state, provider)

    cue = engine.turn("Search the desk.")
    assert state.delivered_cue_ids == ("transport_route_identified",)
    assert state.staged_cue_fact_id == "brandon_identified"
    assert state.staged_handoff_fact_ids == ()
    assert Fact(predicate="transport_route_identified", subject="story", value="true") not in state.facts.asserted
    assert cue.segments[0].text == "A clue catches my attention."
    assert state.last_turn_delivery.cue_fact_id == "transport_route_identified"
    assert state.last_turn_delivery.handoff_staged is False

    handoff = engine.turn("Search the park.")
    assert state.current_scene_id == "1C"
    assert Fact(predicate="trust_brandon", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="transport_route_identified", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="brandon_identified", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="transport_route_departure_ready", subject="story", value="true") in state.facts.asserted
    assert state.staged_cue_fact_id is None
    assert state.staged_handoff_fact_ids == ()
    assert state.last_turn_delivery.cue_fact_id == "brandon_identified"
    assert state.last_turn_delivery.handoff_staged is True
    texts = [segment.text for segment in handoff.segments]
    source_bridge = next(
        scene.metadata.bridge_text["t_1b_1c"] for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B"
    )
    target_entry = next(scene.metadata.entry_text for scene in PACKAGE.scenes if scene.metadata.scene_id == "1C")
    assert texts.index(source_bridge) < texts.index(target_entry)


def test_scene_2a_handoff_asserts_hidden_bridge_fact_without_projecting_it() -> None:
    state = _state_2a()
    engine = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": "Wait."}]})

    engine.turn("Approach the facility entrance.")
    engine.turn("Inspect the security desk.")
    engine.turn("Watch the security desk.")
    handoff = engine.turn("Watch the guard rotation.")

    assert state.current_scene_id == "2B"
    assert Fact(predicate="false_identities_ready", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="rebecca_observing_infiltrators", subject="story", value="true") in state.facts.asserted
    assert "bridge_2a_restricted_access" in state.fired_event_ids
    assert state.last_turn_delivery.handoff_staged is True
    assert any("false credentials" in segment.text.casefold() for segment in handoff.segments)

    projection = KnowledgeProjector().project(state, "player", "Look around.")
    projected_ids = {item.id for item in (*projection.committed_knowledge, *projection.candidates)}
    assert "k_sl_2a_c_r2_rebecca_observes" not in projected_ids
    assert "rebecca_observing_infiltrators" not in projection.model_dump_json()


def test_projected_handoff_contract_is_player_safe_and_prompt_preserves_agency(monkeypatch) -> None:
    state = _state_1b()
    state.staged_cue_fact_id = "transport_route_identified"
    state.staged_handoff_fact_ids = ("transport_route_identified",)
    captured: dict[str, object] = {}

    def open_request(request, **_kwargs: object) -> _Response:
        captured["payload"] = json.loads(request.data)
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"Keep watch."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    provider("Inspect the security desk.")
    projection = KnowledgeProjector().project(state, "player", "Inspect the security desk.")
    assert [item.fact_id for item in projection.handoff_deliveries] == ["transport_route_identified"]
    serialized = json.dumps(captured["payload"]).casefold()
    assert "rebecca_observing_infiltrators" not in serialized
    assert "handoff event" in captured["payload"]["user"].casefold()
    assert "do not say the player did something they did not do" in captured["payload"]["user"].casefold()
    state.staged_handoff_fact_ids = ()
    provider("Inspect the security desk.")
    assert "hint at the evidence" not in captured["payload"]["user"].casefold()
    assert (
        next(item.cue_text for item in PACKAGE.deliveries if item.fact_id == "transport_route_identified")
        in (captured["payload"]["user"])
    )


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
    response = provider("Search the park.")

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
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"Wait."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    response = provider("Search the route.")
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
    text = "Search the route. " + delivery.fallback_text

    def open_request(request, **_kwargs: object) -> _Response:
        payloads.append(json.loads(request.data))
        if len(payloads) == 1:
            return _Response({"narration": '{"segments":[{"kind":"narration","text":"Search the route."}]}'})
        return _Response({"narration": json.dumps({"segments": [{"kind": "narration", "text": text}]})})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    response = provider("Search the route.")
    assert len(payloads) == 2
    assert response["segments"][0]["text"] == text

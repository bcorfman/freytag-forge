from __future__ import annotations

import copy

from storygame.runtime.capture import WorldCapture
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.observation import ObservationRequest
from storygame.runtime.observation_verifier import (
    ObservationVerifier,
    Relation,
    _question_for,
    relations_from_context,
)
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from tests.test_observation_mode import PACKAGE, _state_at
from tests.test_observation_preview import _set_raw, _synthetic_package


def _provider_context(state: RuntimeState, request: ObservationRequest):
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
    context = provider._observation_context(world_for(state.package, state.facts))
    assert context is not None
    return provider, context


def _relation_by_name(context, name: str) -> Relation:
    return next(relation for relation in relations_from_context(context) if relation.thing == name)


def _question_text(relation: Relation) -> str:
    question = _question_for(relation)
    return " ".join(value for value in question.values() if isinstance(value, str))


def test_shipped_context_mentions_held_item_without_holder_and_keeps_seat_place() -> None:
    state = _state_at("outside_house", already_aboard=True)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin_laptop", PACKAGE.world.protagonist_id).ok
    assert world.move("michelle_phone", "truck_passenger_seat").ok
    _provider, context = _provider_context(
        state,
        ObservationRequest("Inspect the truck.", "look", "kristin_truck"),
    )

    held = _relation_by_name(context, "Kristin's laptop")
    seated = _relation_by_name(context, "Michelle's phone")

    assert held == Relation(thing="Kristin's laptop")
    assert seated == Relation(thing="Michelle's phone", place="passenger seat")


def test_synthetic_context_uses_mention_only_for_held_item() -> None:
    package = _synthetic_package()
    state = RuntimeState.bootstrap(package)
    world = world_for(package, state.facts)
    assert world.move("lens", "hero").ok
    assert world.move("remote_marker", "tray").ok
    _provider, held_context = _provider_context(
        state,
        ObservationRequest("Inspect the lens.", "look", "lens"),
    )
    _provider, seated_context = _provider_context(
        state,
        ObservationRequest("Inspect the survey tray.", "look", "tray"),
    )

    held = _relation_by_name(held_context, "calibrated lens")
    seated = _relation_by_name(seated_context, "remote marker")

    assert held == Relation(thing="calibrated lens")
    assert seated == Relation(thing="remote marker", place="survey tray")


def test_mention_only_question_has_no_location_text() -> None:
    text = _question_text(Relation(thing="calibrated lens"))

    assert "held by" not in text
    assert "at place" not in text


def test_equal_place_and_holder_render_as_held_by_only() -> None:
    text = _question_text(Relation(thing="calibrated lens", place="Ari", holder="Ari"))

    assert "held by Ari" in text
    assert "at place Ari" not in text


def test_distinct_place_and_holder_render_both() -> None:
    text = _question_text(Relation(thing="calibrated lens", place="tray", holder="Ari"))

    assert "at place tray" in text
    assert "held by Ari" in text


def test_place_only_and_holder_only_keep_rendering() -> None:
    place_text = _question_text(Relation(thing="calibrated lens", place="tray"))
    holder_text = _question_text(Relation(thing="calibrated lens", holder="Ari"))

    assert "at place tray" in place_text
    assert "held by" not in place_text
    assert "held by Ari" in holder_text
    assert "at place" not in holder_text


def _mention_fake_ask(held_name: str):
    def ask(state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        narration = state["narration"]
        score = 1.0 if held_name in narration else 0.0
        return {key: {"noul": score} for key in questions}

    return ask


def _synthetic_observation_capture():
    state = RuntimeState.bootstrap(_synthetic_package())
    world = world_for(state.package, state.facts)
    assert world.move("lens", "hero").ok
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    provider.observation_request = ObservationRequest("Inspect the lens.", "look", "lens")
    _set_raw(provider, {})
    ask = _mention_fake_ask("calibrated lens")
    return state, provider, ask


def test_shadow_record_rejects_omitted_held_item_and_accepts_mention() -> None:
    for narration, expected in (
        ("The survey tray is quiet.", False),
        ("The calibrated lens catches the light.", True),
    ):
        _state, provider, ask = _synthetic_observation_capture()
        context = provider._observation_context(world_for(provider.state.package, provider.state.facts))
        assert context is not None
        capture = WorldCapture(provider, ask)
        capture.shadow_verifier = ObservationVerifier(ask)

        record = capture.after_commit("Inspect the lens.", narration, entered_scene=False)

        shadow = record["observation_shadow"]
        assert shadow["accepted"] is expected
        assert len(shadow["verdicts"]) == len(context.required)


def test_enforcement_preview_rejects_omitted_held_item_and_accepts_mention() -> None:
    for narration, expected in (
        ("The survey tray is quiet.", False),
        ("The calibrated lens catches the light.", True),
    ):
        state, provider, ask = _synthetic_observation_capture()
        context = provider._observation_context(world_for(provider.state.package, provider.state.facts))
        assert context is not None
        capture = WorldCapture(provider, ask)
        capture.enforcing_verifier = ObservationVerifier(ask)

        result = capture.preview_commit("Inspect the lens.", narration, copy.deepcopy(state), entered_scene=False)

        assert result.accepted is expected
        assert len(result.verdicts) == len(context.required)

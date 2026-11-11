"""Scene 1A's optional departure hold contract."""

from __future__ import annotations

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.delivery_text import resolve_delivery_text, true_fact_ids
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(ROOT)
KNOWLEDGE_ID = "k_sl_1a_k_r1"
STORYLET_ID = "SL-1A-K"
BASE_TEXT = (
    "Kristin does not pull away yet. If anyone is watching the street, driving to the park now would lead them "
    "straight to the bench. She waits to see what the street does."
)
ON_SCENE_TEXT = (
    "Kristin does not pull away yet. The patrol is still at the house, and the truck would be the first thing they "
    "follow. If she drives to the park now, she leads them straight to the bench. She waits to see what the patrol "
    "does."
)
DEPARTED_TEXT = (
    "Kristin does not pull away yet. The patrol has only just left, and it could be waiting around the corner. If she "
    "drives to the park now, she may lead it straight to the bench. She waits to see what the street does."
)


def _routes() -> dict[str, object]:
    data = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    return {item["id"]: item for item in data["storylets"]}


def _knowledge():
    return {entry.id: entry for entry in PACKAGE.knowledge.knowledge}


def _state(*, truck: bool = False, lead: bool = True, turn_index: int = 8, **facts: bool) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.turn_index = turn_index
    for fact_id, value in {"michelle_lead_actionable": lead, **facts}.items():
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value=str(value).lower()))
    if truck:
        world = world_for(PACKAGE, state.facts)
        assert world.move("kristin", "outside_house").ok
        assert world.move("kristin", "truck_driver_seat").ok
    apply_world_effects(PACKAGE, state.facts)
    return state


def _candidate_ids(command: str, *, truck: bool = True, lead: bool = True, **facts: bool) -> set[str]:
    state = _state(truck=truck, lead=lead, **facts)
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "The street waits."}]})
    engine._activate_pacing()
    return {candidate.id for candidate in engine.projector.project(state, "player", command).candidates}


def _handoff_id(command: str, *, truck: bool = True, lead: bool = True, **facts: bool) -> str | None:
    state = _state(truck=truck, lead=lead, **facts)
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "The street waits."}]})
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    handoff = uniquely_matched_authored_handoff(command, candidates)
    return handoff.candidate.id if handoff else None


def test_departure_hold_storylet_is_declared() -> None:
    storylet = _routes()[STORYLET_ID]
    assert storylet["scene_id"] == "1A"
    assert [option["id"] for option in storylet["realization_options"]] == ["SL-1A-K-R1"]
    pacing = storylet["activation"]["pacing"]
    assert (pacing["earliest_turn"], pacing["target_turn"], pacing["latest_turn"]) == (4, 10, 12)
    assert storylet["activation"]["conditions"] == [{"fact_id": "michelle_lead_actionable", "equals": True}]


def test_departure_held_fact_is_declared_everywhere() -> None:
    routes = yaml.safe_load((ROOT / "storylet-routes.yaml").read_text(encoding="utf-8"))
    assert "departure_held" in {fact.id for fact in PACKAGE.knowledge.facts}
    assert "departure_held" in PACKAGE.world.facts
    declaration = next(item for item in routes["new_fact_ids"] if item["id"] == "departure_held")
    assert declaration["used_by_storylets"] == [STORYLET_ID]


def test_the_hold_answers_a_departure_command_at_the_truck() -> None:
    for command in (
        "Drive to the park.",
        "Drive the truck to the park.",
        "Head for the park.",
        "Pull away and go to the park bench.",
    ):
        assert _handoff_id(command, memory_card_recovered=True) == KNOWLEDGE_ID


def test_the_hold_stays_quiet_for_other_commands_and_places() -> None:
    assert _knowledge()[KNOWLEDGE_ID].id == KNOWLEDGE_ID
    for command in ("Start the truck.", "Go out to the truck.", "Get in the truck."):
        assert _handoff_id(command) != KNOWLEDGE_ID
    assert _handoff_id("Drive to the park.", truck=False) != KNOWLEDGE_ID
    assert _handoff_id("Drive to the park.", lead=False) != KNOWLEDGE_ID


def test_the_hold_text_is_the_approved_wording_for_each_patrol_state() -> None:
    entry = _knowledge()[KNOWLEDGE_ID]
    assert resolve_delivery_text(entry, true_fact_ids(_state().facts)) == BASE_TEXT
    assert resolve_delivery_text(entry, true_fact_ids(_state(patrol_on_scene=True).facts)) == ON_SCENE_TEXT
    assert resolve_delivery_text(entry, true_fact_ids(_state(patrol_departed=True).facts)) == DEPARTED_TEXT


def test_the_hold_can_repeat() -> None:
    assert _handoff_id("Drive to the park.", memory_card_recovered=True, departure_held=True) == KNOWLEDGE_ID


def test_the_hold_sets_only_its_own_fact() -> None:
    entry = _knowledge()[KNOWLEDGE_ID]
    assert {(operation.fact_id, operation.value) for operation in entry.establishes} == {("departure_held", True)}
    protected = {
        "memory_card_recovered",
        "michelle_lead_actionable",
        "patrol_return_pressure",
        "patrol_departed",
        "michelle_warning_known",
    }
    assert not protected & {operation.fact_id for operation in entry.establishes}
    assert entry.voiceable is False
    assert "kristin_truck" in entry.reach_entity_ids


def test_the_hold_text_conveys_every_required_group_and_leaks_nothing() -> None:
    entry = _knowledge()[KNOWLEDGE_ID]
    protected = ("janus", "brandon", "memory card", "recording", "dead drop", "continuity initiative")
    for facts, expected in (
        ({}, BASE_TEXT),
        ({"patrol_on_scene": True}, ON_SCENE_TEXT),
        ({"patrol_departed": True}, DEPARTED_TEXT),
    ):
        text = resolve_delivery_text(entry, true_fact_ids(_state(**facts).facts))
        assert text == expected
        lowered = text.casefold()
        assert all(any(term.casefold() in lowered for term in group) for group in entry.must_convey)
        assert not any(term in lowered for term in protected)


def _open_request(request, **_kwargs: object):
    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def read(self) -> bytes:
            return b'{"narration":"{\\"segments\\":[{\\"kind\\":\\"narration\\",\\"text\\":\\"The street waits.\\"}]}"}'

    return _Response()


def test_an_early_drive_command_keeps_the_scene_and_shows_the_hold(monkeypatch) -> None:
    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", _open_request)
    for facts, expected in (
        ({}, BASE_TEXT),
        ({"patrol_on_scene": True}, ON_SCENE_TEXT),
        ({"patrol_departed": True}, DEPARTED_TEXT),
    ):
        state = _state(truck=True, memory_card_recovered=True, **facts)
        engine = RuntimeEngine(
            state, CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
        )
        result = engine.turn("Drive to the park.")
        assert state.current_scene_id == "1A"
        assert sum(segment.text.count(expected) for segment in result.segments) == 1
        assert _has_true(state, "departure_held")


def test_the_scene_still_leaves_once_the_floor_and_triggers_hold() -> None:
    state = _state(
        turn_index=13,
        memory_card_recovered=True,
        patrol_return_pressure=True,
    )
    engine = RuntimeEngine(state, lambda _command: {"segments": []})
    assert {transition.id for transition in engine.validator.eligible_transitions(state)} == {"t_1a_1b"}
    assert engine._apply_authored_transition() is not None
    assert state.current_scene_id == "1B"


def _has_true(state: RuntimeState, fact_id: str) -> bool:
    return Fact(predicate=fact_id, subject="story", value="true") in state.facts.asserted

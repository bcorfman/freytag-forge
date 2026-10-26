"""Scene 1A officer demand and patrol-departure acknowledgement contract."""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
COMMAND = "Feel under the drawer."
WITNESSED_CARD_REVEAL = "k_sl_1a_b_r0w"
PRESS_TEXT = (
    "The officer plants himself between her and the front door and holds out a gloved hand. "
    "\"Whatever you just took from that desk. Let's see it, ma'am. Right now.\""
)
ACKNOWLEDGING_DEPARTURE_TEXT = (
    "The officer's radio crackles with a description that is hers. He backs out through the front door, "
    "eyes on her the whole way, and the patrol pulls away from the curb."
)
PLAIN_DEPARTURE_TEXT = "The patrol pulls away from the curb."


def _neutral_provider(_command: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": "The room is quiet."}]}


def _has_true(state: RuntimeState, fact_id: str) -> bool:
    return Fact(predicate=fact_id, subject="story", value="true") in state.facts.asserted


def _state(
    *,
    turn_index: int = 0,
    patrol_on_scene: bool = False,
    patrol_in_house: bool = False,
    card_challenged: bool = False,
    officer_demanded_card: bool = False,
) -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.turn_index = turn_index
    for fact_id, value in (
        ("patrol_on_scene", patrol_on_scene),
        ("patrol_in_house", patrol_in_house),
        ("card_challenged", card_challenged),
        ("officer_demanded_card", officer_demanded_card),
    ):
        if value:
            state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    if patrol_on_scene:
        state.fired_event_ids.add("patrol_arrives_1a")
    if patrol_in_house:
        state.fired_event_ids.add("patrol_enters_1a")
    apply_world_effects(PACKAGE, state.facts)
    return state


def test_witnessed_recovery_then_next_turn_shows_one_officer_press(monkeypatch) -> None:
    state = _state(patrol_on_scene=True, patrol_in_house=True)
    state.active_event_ids.add("SL-1A-E")

    def open_request(request, **_kwargs: object):
        class _Response:
            def __enter__(self):
                return self

            def __exit__(self, *_args: object) -> None:
                return None

            def read(self) -> bytes:
                return (
                    b'{"narration":"{\\"segments\\":[{\\"kind\\":\\"narration\\",'
                    b'\\"text\\":\\"The room is quiet.\\"}]}"}'
                )

        return _Response()

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    engine = RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )
    recovery = engine.turn(COMMAND)
    assert recovery.selected_knowledge_ids == (WITNESSED_CARD_REVEAL,)
    assert _has_true(state, "card_challenged")

    # The recovery is already committed; place the following player turn at the event's turn.
    state.turn_index = 5
    result = engine.turn("Answer the officer.")

    assert sum(segment.text.count(PRESS_TEXT) for segment in result.segments) == 1
    assert _has_true(state, "officer_demanded_card")


def test_recovery_before_arrival_reaches_plain_departure_without_press() -> None:
    state = _state()
    engine = RuntimeEngine(state, _neutral_provider)
    results = []
    for turn in range(1, 8):
        results.append(engine.turn(COMMAND if turn == 1 else "Wait."))

    texts = [segment.text for result in results for segment in result.segments]
    assert PRESS_TEXT not in texts
    assert texts.count(PLAIN_DEPARTURE_TEXT) == 1
    assert not _has_true(state, "officer_demanded_card")


def test_unwitnessed_run_reaches_plain_departure_without_press() -> None:
    state = _state(turn_index=6, patrol_on_scene=True, patrol_in_house=True)
    engine = RuntimeEngine(state, _neutral_provider)

    engine.turn("Wait.")

    assert state.last_turn_delivery.complication_text == PLAIN_DEPARTURE_TEXT
    assert not _has_true(state, "officer_demanded_card")


def test_departure_after_demand_acknowledges_the_officer() -> None:
    state = _state(
        turn_index=6,
        patrol_on_scene=True,
        patrol_in_house=True,
        card_challenged=True,
        officer_demanded_card=True,
    )
    state.fired_event_ids.add("officer_presses_1a")

    result = RuntimeEngine(state, _neutral_provider).turn("Wait.")
    texts = [segment.text for segment in result.segments]

    assert texts.count(ACKNOWLEDGING_DEPARTURE_TEXT) == 1
    assert PLAIN_DEPARTURE_TEXT not in texts


def test_officer_demand_does_not_change_card_custody_or_transition_trigger() -> None:
    state = _state(
        turn_index=5,
        patrol_on_scene=True,
        patrol_in_house=True,
        card_challenged=True,
        officer_demanded_card=False,
    )
    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)
    expected_transition_triggers = {
        trigger.fact_id
        for trigger in next(
            transition for transition in PACKAGE.pacing.transitions if transition.id == "t_1a_1b"
        ).triggers
    }
    expected_transition_triggers.discard("officer_demanded_card")

    RuntimeEngine(state, _neutral_provider).turn("Wait.")

    assert _has_true(state, "officer_demanded_card")
    assert world_for(PACKAGE, state.facts).parent("memory_card") == "kristin"
    transition = next(transition for transition in PACKAGE.pacing.transitions if transition.id == "t_1a_1b")
    assert {trigger.fact_id for trigger in transition.triggers} == expected_transition_triggers
    assert not any(trigger.fact_id == "officer_demanded_card" for trigger in transition.triggers)

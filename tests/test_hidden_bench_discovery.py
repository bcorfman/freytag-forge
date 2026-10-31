from __future__ import annotations

import json

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects, world_for
from tests.test_scene_1b_grounding import PACKAGE, _scene_1b_state

DISCOVERY = "k_sl_1b_d_r1"
POINTER = "k_sl_1b_e_r1"
CLUES = ("transit_card", "number_sequence", "michelle_photograph")
RECOVERY_FACT = "bench_clues_recovered"
POINTER_FACT = "bench_underside_pointed_out"
INTERPRETATION_FACTS = ("brandon_face_known", "brandon_identified", "transport_route_identified")


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _fresh_1b_state(*, recovered: bool = False) -> RuntimeState:
    state = _scene_1b_state()
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    state._assert_scene_entry_fact("1B")
    state.active_event_ids.update({"SL-1B-A", "SL-1B-B", "SL-1B-D", "SL-1B-E"})
    if recovered:
        state.facts.assert_fact(Fact(predicate=RECOVERY_FACT, subject="story", value="true"))
        apply_world_effects(PACKAGE, state.facts)
    return state


def _engine(monkeypatch: pytest.MonkeyPatch, state: RuntimeState) -> RuntimeEngine:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")

    def transport(_request: object, **_kwargs: object) -> _Response:
        return _Response(
            {
                "narration": json.dumps(
                    {
                        "segments": [{"kind": "narration", "text": "The scene continues."}],
                        "selected_knowledge_ids": [],
                    }
                )
            }
        )

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", transport)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider)


def _has_fact(state: RuntimeState, fact_id: str) -> bool:
    return any(fact.predicate == fact_id and fact.value == "true" for fact in state.facts.asserted)


@pytest.mark.parametrize(
    "player_input",
    (
        "Look under the park bench.",
        "Search beneath the bench.",
        "Inspect the underside of the park bench.",
        "Check under the bench.",
    ),
)
def test_underside_commands_recover_all_hidden_bench_clues(monkeypatch: pytest.MonkeyPatch, player_input: str) -> None:
    # An explicit underside investigation earns the non-voiceable discovery only.
    state = _fresh_1b_state()
    result = _engine(monkeypatch, state).turn(player_input)
    world = world_for(PACKAGE, state.facts)

    assert result.selected_knowledge_ids == (DISCOVERY,)
    assert POINTER not in result.selected_knowledge_ids
    assert _has_fact(state, RECOVERY_FACT)
    assert not _has_fact(state, POINTER_FACT)
    assert all(world.parent(item_id) == "kristin" and not world.is_hidden(item_id) for item_id in CLUES)
    assert not any(_has_fact(state, fact_id) for fact_id in INTERPRETATION_FACTS)


@pytest.mark.parametrize(
    "player_input",
    (
        "Inspect the park bench.",
        "Search the park bench.",
        "Check the park bench.",
        "Sit on the park bench.",
        "Inspect the storm drain.",
    ),
)
def test_general_bench_and_nearby_commands_do_not_recover_clues(
    monkeypatch: pytest.MonkeyPatch, player_input: str
) -> None:
    # A general inspection or an unrelated nearby action is not an underside find.
    state = _fresh_1b_state()
    result = _engine(monkeypatch, state).turn(player_input)
    world = world_for(PACKAGE, state.facts)

    assert DISCOVERY not in result.selected_knowledge_ids
    assert not _has_fact(state, RECOVERY_FACT)
    assert all(world.parent(item_id) == "park_bench" and world.is_hidden(item_id) for item_id in CLUES)


@pytest.mark.parametrize("player_input", ("Sit on the park bench.", "Inspect the storm drain."))
def test_unrelated_bench_and_nearby_commands_earn_nothing(monkeypatch: pytest.MonkeyPatch, player_input: str) -> None:
    state = _fresh_1b_state()
    result = _engine(monkeypatch, state).turn(player_input)

    assert result.selected_knowledge_ids == ()
    assert not _has_fact(state, RECOVERY_FACT)


@pytest.mark.parametrize(
    "player_input",
    (
        "Inspect the park bench.",
        "Search the park bench.",
        "Check the park bench.",
        "Look at the park bench.",
        "Examine the park bench.",
    ),
)
def test_general_bench_commands_earn_the_repeatable_pointer(monkeypatch: pytest.MonkeyPatch, player_input: str) -> None:
    state = _fresh_1b_state()
    engine = _engine(monkeypatch, state)

    first = engine.turn(player_input)
    second = engine.turn(player_input)

    assert first.selected_knowledge_ids == (POINTER,)
    assert second.selected_knowledge_ids == ()
    assert [segment.text for segment in second.segments].count(
        PACKAGE.knowledge_indexes.by_id[POINTER].delivery_text
    ) == 1
    assert _has_fact(state, POINTER_FACT)
    assert not _has_fact(state, RECOVERY_FACT)


def test_raw_language_negation_does_not_recover_bench_clues(monkeypatch: pytest.MonkeyPatch) -> None:
    # Raw-language negation follows the existing negation corpus boundary.
    state = _fresh_1b_state()
    result = _engine(monkeypatch, state).turn("Do not search beneath the park bench.")

    assert result.selected_knowledge_ids == ()
    assert not _has_fact(state, RECOVERY_FACT)


def test_unrelated_actions_do_not_compose_evidence_groups(monkeypatch: pytest.MonkeyPatch) -> None:
    # Each command is matched independently even when their words could combine.
    state = _fresh_1b_state()
    engine = _engine(monkeypatch, state)

    first = engine.turn("Look at the sky.")
    second = engine.turn("Go under the bridge near the park bench.")

    assert first.selected_knowledge_ids == ()
    assert second.selected_knowledge_ids == ()
    assert not _has_fact(state, RECOVERY_FACT)


@pytest.mark.parametrize(
    "player_input",
    (
        "Examine Michelle's photograph.",
        "Compare the transit token with the number sequence.",
        "Show Michelle's photograph to the man.",
    ),
)
def test_interpretation_commands_are_gated_until_recovery(monkeypatch: pytest.MonkeyPatch, player_input: str) -> None:
    # Guessing hidden clue names cannot bypass the recovery prerequisite.
    state = _fresh_1b_state()
    result = _engine(monkeypatch, state).turn(player_input)

    assert result.selected_knowledge_ids == ()
    assert not _has_fact(state, RECOVERY_FACT)
    assert not any(_has_fact(state, fact_id) for fact_id in INTERPRETATION_FACTS)


def test_questioning_the_man_remains_ungated_before_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    # The authored question route remains available without the recovered clues.
    state = _fresh_1b_state()
    result = _engine(monkeypatch, state).turn("Ask the man about Michelle.")

    assert result.selected_knowledge_ids == ("k_sl_1b_b_r2",)
    assert _has_fact(state, "brandon_identified")
    assert not _has_fact(state, RECOVERY_FACT)


@pytest.mark.parametrize(
    ("player_input", "knowledge_id", "fact_id"),
    (
        ("Examine Michelle's photograph.", "k_sl_1b_a_r2", "brandon_face_known"),
        ("Compare the transit token with the number sequence.", "k_sl_1b_a_r1", "transport_route_identified"),
        ("Show Michelle's photograph to the man.", "k_sl_1b_b_r1", "brandon_identified"),
    ),
)
def test_recovered_clues_enable_each_interpretation_from_fresh_state(
    monkeypatch: pytest.MonkeyPatch, player_input: str, knowledge_id: str, fact_id: str
) -> None:
    # Every interpretation starts from a fresh recovered state and earns one beat.
    state = _fresh_1b_state(recovered=True)
    result = _engine(monkeypatch, state).turn(player_input)

    assert result.selected_knowledge_ids == (knowledge_id,)
    assert _has_fact(state, RECOVERY_FACT)
    assert _has_fact(state, fact_id)


def test_recovered_bench_find_is_not_rediscovered(monkeypatch: pytest.MonkeyPatch) -> None:
    # Repeat look is deterministic; putting an item down needs an observation/model path, so it is not exercised.
    state = _fresh_1b_state(recovered=True)
    result = _engine(monkeypatch, state).turn("Look under the park bench.")

    assert result.selected_knowledge_ids == ()
    assert _has_fact(state, RECOVERY_FACT)


def test_recovered_bench_pointer_is_gated_off(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _fresh_1b_state(recovered=True)
    result = _engine(monkeypatch, state).turn("Inspect the park bench.")

    assert result.selected_knowledge_ids == ()
    assert _has_fact(state, RECOVERY_FACT)
    assert not _has_fact(state, POINTER_FACT)


def test_bench_pointer_package_shape_is_safe_and_repeatable() -> None:
    pointer = PACKAGE.knowledge_indexes.by_id[POINTER]

    assert pointer.voiceable is False
    assert pointer.repeatable is True
    assert tuple((requirement.fact_id, requirement.equals) for requirement in pointer.requires) == (
        (RECOVERY_FACT, False),
    )
    assert {effect.fact_id for effect in pointer.establishes} == {POINTER_FACT}
    text = f"{pointer.statement} {pointer.delivery_text}".casefold()
    assert not any(term in text for term in ("transit", "token", "number", "photograph", "photo", "seat"))


def test_bench_pointer_has_independent_source_and_is_outside_departure_bridge() -> None:
    pointer = PACKAGE.knowledge_indexes.by_id[POINTER]
    source_ids = {
        realization.id
        for storylet in PACKAGE.storylet_routes.storylets
        if storylet.id in {"SL-1B-A", "SL-1B-D"}
        for realization in storylet.realizations
    }
    departure = next(event for event in PACKAGE.storylet_routes.bridge_events if event.id == "bridge_1b_departure")

    assert pointer.source.storylet_id == "SL-1B-E"
    assert pointer.source.realization_id == "SL-1B-E-R1"
    assert pointer.source.realization_id not in source_ids
    assert "SL-1B-E" not in departure.realization_storylets
    assert POINTER_FACT not in (*departure.activation.all_facts_true, *departure.activation.any_of)


def test_scene_1b_storylet_routes_keep_the_authored_order() -> None:
    assert [storylet.id for storylet in PACKAGE.storylet_routes.storylets if storylet.scene_id == "1B"] == [
        "SL-1B-D",
        "SL-1B-A",
        "SL-1B-E",
        "SL-1B-B",
        "SL-1B-C",
    ]


def test_hidden_bench_package_shape_and_handoff_contract() -> None:
    # The authored package keeps discovery, later interpretations, and departure separate.
    discovery = PACKAGE.knowledge_indexes.by_id[DISCOVERY]
    assert discovery.voiceable is False
    assert discovery.source.storylet_id == "SL-1B-D"
    assert discovery.source.realization_id == "SL-1B-D-R1"
    assert discovery.source.realization_id not in {
        realization.id
        for storylet in PACKAGE.storylet_routes.storylets
        if storylet.id == "SL-1B-A"
        for realization in storylet.realizations
    }
    departure = next(event for event in PACKAGE.storylet_routes.bridge_events if event.id == "bridge_1b_departure")
    assert "SL-1B-D" not in departure.realization_storylets

    state = _fresh_1b_state()
    world = world_for(PACKAGE, state.facts)
    assert all(
        world.parent(item_id) == "park_bench" and world.relation(item_id) == "under" and world.is_hidden(item_id)
        for item_id in CLUES
    )

    banned = ("transit token", "number sequence", "photograph", "photo")
    for fact_id in ("transport_route_identified", "brandon_identified"):
        handoff = next(item for item in PACKAGE.deliveries if item.fact_id == fact_id)
        assert all(term not in text.lower() for text in (handoff.cue_text, handoff.fallback_text) for term in banned)
        if fact_id == "transport_route_identified":
            assert "freight terminal" in handoff.must_convey[1]
        else:
            assert "Brandon" in handoff.must_convey[0]

"""Offline characterization of a drawer-avoiding 1A playthrough."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
DRAWER_REVEAL_IDS = {"k_sl_1a_b_r0", "k_sl_1a_f_r1", "k_sl_1a_f_r2"}
NON_DRAWER_COMMANDS = (
    "Look around.",
    "Examine Michelle's phone.",
    "Search the truck.",
    "Walk around the building.",
)
EXPECTED_HANDOFFS = {
    "1A": ("continuity_initiative_known",),
    "1B": ("park_pursuit_resolved", "transport_route_identified", "brandon_identified", "missing_may_be_alive"),
    "1C": ("facility_proof", "captives_confirmed_alive", "national_detention_network_known"),
}


def _true_fact_ids(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if str(fact.value).lower() == "true"}


def _drawer_dependency_graph() -> tuple[set[str], set[str]]:
    """Return 1A drawer-dependent reveal IDs and facts from the loaded package."""

    knowledge = tuple(item for item in PACKAGE.knowledge.knowledge if "1A" in item.available_in_scenes)
    dependent_ids = set(DRAWER_REVEAL_IDS)
    dependent_facts: set[str] = set()
    changed = True
    while changed:
        changed = False
        for item in knowledge:
            if item.id not in dependent_ids and not any(
                requirement.fact_id in dependent_facts for requirement in item.requires
            ):
                continue
            if item.id not in dependent_ids:
                dependent_ids.add(item.id)
                changed = True
            for effect in item.establishes:
                if effect.op == "assert" and effect.value is True and effect.fact_id not in dependent_facts:
                    dependent_facts.add(effect.fact_id)
                    changed = True

    # "Only" excludes facts that also have a non-drawer 1A source, such as
    # michelle_abduction_suspicion from k_sl_1a_a_r1.
    establishers = {
        fact_id: {
            item.id
            for item in knowledge
            if any(
                effect.op == "assert" and effect.value is True and effect.fact_id == fact_id
                for effect in item.establishes
            )
        }
        for fact_id in dependent_facts
    }
    only_dependent_facts = {
        fact_id for fact_id, sources in establishers.items() if sources and sources <= dependent_ids
    }
    return dependent_ids, only_dependent_facts


def test_static_drawer_dependencies_have_no_later_scene_dependents() -> None:
    dependent_ids, drawer_only_facts = _drawer_dependency_graph()

    assert dependent_ids == {
        "k_sl_1a_b_r0",
        "k_sl_1a_b_r1",
        "k_sl_1a_b_r2",
        "k_sl_1a_c_r1",
        "k_sl_1a_c_r2",
        "k_sl_1a_d_r1",
        "k_sl_1a_f_r1",
        "k_sl_1a_f_r2",
    }
    assert drawer_only_facts == {
        "continuity_initiative_known",
        "drawer_gap_pointed_out",
        "house_marked_for_return",
        "memory_card_recovered",
        "michelle_lead_actionable",
        "michelle_warning_known",
        "official_interest_in_michelle_known",
        "patrol_return_pressure",
    }
    assert "michelle_abduction_suspicion" not in drawer_only_facts

    later_reveals = tuple(
        item.id
        for item in PACKAGE.knowledge.knowledge
        if any(scene != "1A" for scene in item.available_in_scenes)
        and any(requirement.fact_id in drawer_only_facts for requirement in item.requires)
    )
    later_storylets = tuple(
        item.id
        for item in PACKAGE.storylet_routes.storylets
        if item.scene_id != "1A"
        and any(condition.fact_id in drawer_only_facts for condition in item.activation_conditions)
    )
    later_handoffs = tuple(
        item.id
        for item in (*PACKAGE.storylet_routes.bridge_events, *PACKAGE.storylet_routes.resolution_events)
        if item.scene_id != "1A"
        and any(fact_id in drawer_only_facts for fact_id in (*item.activation.all_facts_true, *item.activation.any_of))
    )
    later_routes = tuple(
        item.id
        for item in PACKAGE.pacing.transitions
        if item.source_scene_id != "1A" and any(trigger.fact_id in drawer_only_facts for trigger in item.triggers)
    )
    later_deliveries = tuple(
        item.fact_id
        for item in PACKAGE.deliveries
        if item.scene_id != "1A" and any(cost.fact_id in drawer_only_facts for cost in item.costs)
    )

    assert later_reveals == ()
    assert later_storylets == ()
    assert later_handoffs == ()
    assert later_routes == ()
    assert later_deliveries == ()


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _engine(monkeypatch: pytest.MonkeyPatch, state: RuntimeState) -> RuntimeEngine:
    monkeypatch.setenv("FREYTAG_SEMANTIC_REVEAL", "0")

    def fake_urlopen(_request: object, **_kwargs: object) -> _Response:
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

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", fake_urlopen)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    return RuntimeEngine(state, provider)


def _world_fact(state: RuntimeState, predicate: str, subject: str) -> str | None:
    return next(
        (
            fact.value if fact.value is not None else fact.object
            for fact in state.facts.asserted
            if fact.predicate == predicate and fact.subject == subject
        ),
        None,
    )


def _play_until_scene_changes(
    engine: RuntimeEngine, state: RuntimeState, scene_id: str
) -> tuple[int, tuple[str, ...], tuple[str, ...], str, str]:
    start_turn = state.turn_index
    selected: list[str] = []
    handoff_ids: tuple[str, ...] = ()
    handoff_text = ""
    while state.current_scene_id == scene_id and state.turn_index - start_turn < 60:
        command = NON_DRAWER_COMMANDS[(state.turn_index - start_turn) % len(NON_DRAWER_COMMANDS)]
        result = engine.turn(command)
        selected.extend(result.selected_knowledge_ids)
        if state.current_scene_id != scene_id:
            assert engine.last_projection is not None
            handoff_ids = tuple(delivery.fact_id for delivery in engine.last_projection.handoff_deliveries)
            handoff_text = result.narration
            assert engine.last_attempt is not None
            return (
                state.turn_index - start_turn,
                tuple(selected),
                handoff_ids,
                handoff_text,
                engine.last_attempt.transition_cause,
            )
    pytest.fail(f"{scene_id} did not change within the 60-turn cap")


def test_non_drawer_replay_forces_1a_1b_1c_and_reaches_3c(monkeypatch: pytest.MonkeyPatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = _engine(monkeypatch, state)
    engine.opening()

    exits: dict[str, tuple[int, tuple[str, ...], tuple[str, ...], str, str]] = {}
    exits["1A"] = _play_until_scene_changes(engine, state, "1A")

    assert exits["1A"][:3] == (13, (), EXPECTED_HANDOFFS["1A"])
    assert state.current_scene_id == "1B"
    assert "memory_card_recovered" in _true_fact_ids(state)
    assert "drawer_gap_pointed_out" not in _true_fact_ids(state)
    assert _world_fact(state, "wk_parent", "memory_card") == "kristin"
    assert _world_fact(state, "wk_relation", "memory_card") == "carried_by"

    for scene_id in ("1B", "1C"):
        exits[scene_id] = _play_until_scene_changes(engine, state, scene_id)

    assert exits["1B"][:3] == (13, (), EXPECTED_HANDOFFS["1B"])
    assert exits["1C"][:3] == (11, (), EXPECTED_HANDOFFS["1C"])
    assert all(exit_data[4] == "forced" for exit_data in exits.values())
    assert "recovers Michelle's memory card" in exits["1A"][3]
    assert "Continuity Initiative" in exits["1A"][3]
    assert state.current_scene_id == "2A"

    # The same null-action script can traverse every remaining scene by the
    # package's authored forced handoffs, without opening or searching a drawer.
    remaining_exits: dict[str, str] = {}
    for scene_id in ("2A", "2B", "2C", "3A", "3B"):
        _turns, selected, _handoff_ids, _text, cause = _play_until_scene_changes(engine, state, scene_id)
        remaining_exits[scene_id] = cause
        assert selected == ()
    assert remaining_exits == {scene_id: "forced" for scene_id in ("2A", "2B", "2C", "3A", "3B")}
    assert state.current_scene_id == "3C"

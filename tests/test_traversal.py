from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.engine import EngineRefusalTurn, RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.traversal import match_traversal_command
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import StoryPackageError, load_story_package

FIXTURE = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"
ROOT = FIXTURE.parent


def provider(_input: str):
    return {"segments": [{"kind": "narration", "text": "Ada waits."}]}


def state_and_engine() -> tuple[RuntimeState, RuntimeEngine]:
    state = RuntimeState.bootstrap(load_story_package(FIXTURE))
    return state, RuntimeEngine(state, provider)


def test_movement_commands_match_destination_or_unique_route_entity() -> None:
    state, _engine = state_and_engine()
    world = world_for(state.package, state.facts)
    assert match_traversal_command(state.package, state.facts, world, "Go to the service level") == "service_level"
    assert (
        match_traversal_command(state.package, state.facts, world, "Take the sea chest to the service level")
        == "service_level"
    )
    assert match_traversal_command(state.package, state.facts, world, "Go to the logbook") is None


def test_turn_wires_closed_movement_to_refusal_without_calling_provider() -> None:
    state = RuntimeState.bootstrap(load_story_package(FIXTURE))
    calls: list[str] = []

    def recording_provider(command: str):
        calls.append(command)
        return provider(command)

    result = RuntimeEngine(state, recording_provider).turn("Go to the service level")
    assert isinstance(result, EngineRefusalTurn)
    assert result.narration == "access_closed"
    assert calls == []


def test_unrelated_movement_falls_through_to_provider() -> None:
    state = RuntimeState.bootstrap(load_story_package(FIXTURE))
    calls: list[str] = []

    def recording_provider(command: str):
        calls.append(command)
        return provider(command)

    RuntimeEngine(state, recording_provider).turn("Go to the logbook")
    assert calls == ["Go to the logbook"]


def true_facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if fact.subject == "story" and fact.value == "true"}


def test_gated_connection_refuses_then_arrives_after_access_fact() -> None:
    state, engine = state_and_engine()
    before = state.snapshot()
    refusal = engine.follow_connection("service_level")
    assert isinstance(refusal, EngineRefusalTurn)
    assert refusal.narration == "access_closed"
    assert state.snapshot() == before

    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))
    result = engine.follow_connection("service_level")
    assert result.narration == "Ada reaches the service level."


def test_legal_traversal_is_one_accepted_turn_with_consequences() -> None:
    state, engine = state_and_engine()
    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))
    result = engine.follow_connection("service_level")

    assert result.narration == "Ada reaches the service level."
    assert world_for(state.package, state.facts).parent("ada") == "service_level"
    assert "route_traversed" in true_facts(state)
    assert state.turn_index == 1


@pytest.mark.parametrize("destination", ["logbook", "lamp_room"])
def test_unrelated_entity_and_sibling_without_connection_refuse(destination: str) -> None:
    state, engine = state_and_engine()
    before = state.snapshot()
    refusal = engine.follow_connection(destination)
    assert isinstance(refusal, EngineRefusalTurn)
    assert refusal.narration == "no_route"
    assert state.snapshot() == before


def test_already_there_refuses_without_mutation() -> None:
    state, engine = state_and_engine()
    before = state.snapshot()
    refusal = engine.follow_connection("cottage")
    assert isinstance(refusal, EngineRefusalTurn)
    assert refusal.narration == "already_there"
    assert state.snapshot() == before


def test_traversal_burns_pressure_and_refusal_does_not() -> None:
    state, engine = state_and_engine()
    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))
    engine.follow_connection("service_level")
    assert "tide_has_turned" not in true_facts(state)
    engine.turn("Wait.")
    assert "tide_has_turned" in true_facts(state)

    state, engine = state_and_engine()
    engine.follow_connection("lamp_room")
    assert state.turn_index == 0
    engine.turn("Wait.")
    assert state.turn_index == 1
    assert "tide_has_turned" not in true_facts(state)


def test_save_restore_after_traversal_keeps_place_and_consequence_once() -> None:
    state, engine = state_and_engine()
    state.facts.assert_fact(Fact(predicate="brass_key_found", subject="story", value="true"))
    engine.follow_connection("service_level")
    snapshot = state.snapshot()
    state.facts.retract_fact(Fact(predicate="route_traversed", subject="story", value="true"))
    state.restore_snapshot(snapshot)

    assert world_for(state.package, state.facts).parent("ada") == "service_level"
    assert list(state.facts.matching("route_traversed", "story")) == [
        Fact(predicate="route_traversed", subject="story", value="true")
    ]


def copied_fixture(tmp_path: Path) -> Path:
    destination = tmp_path / "lighthouse-incident"
    shutil.copytree(FIXTURE, destination)
    return destination


@pytest.mark.parametrize(
    ("connections", "needle"),
    [
        ([{"id": "same", "from_place_id": "cottage", "to_place_id": "shore", "arrival_text": "x"}] * 2, "same"),
        ([{"id": "bad_route", "from_place_id": "missing", "to_place_id": "shore", "arrival_text": "x"}], "bad_route"),
        ([{"id": "bad_route", "from_place_id": "cottage", "to_place_id": "missing", "arrival_text": "x"}], "bad_route"),
        ([{"id": "bad_route", "from_place_id": "cottage", "to_place_id": "cottage", "arrival_text": "x"}], "bad_route"),
        (
            [
                {
                    "id": "bad_route",
                    "from_place_id": "cottage",
                    "to_place_id": "shore",
                    "via_id": "missing",
                    "arrival_text": "x",
                }
            ],
            "bad_route",
        ),
        (
            [
                {
                    "id": "bad_route",
                    "from_place_id": "cottage",
                    "to_place_id": "shore",
                    "access_fact_id": "missing",
                    "arrival_text": "x",
                }
            ],
            "bad_route",
        ),
        (
            [
                {
                    "id": "bad_route",
                    "from_place_id": "cottage",
                    "to_place_id": "shore",
                    "consequences": [{"op": "assert", "fact_id": "missing", "value": True}],
                    "arrival_text": "x",
                }
            ],
            "bad_route",
        ),
        ([{"id": "bad_route", "from_place_id": "cottage", "to_place_id": "shore", "arrival_text": "   "}], "bad_route"),
    ],
)
def test_loader_rejects_connection_declarations(tmp_path: Path, connections: list[dict], needle: str) -> None:
    package = copied_fixture(tmp_path)
    (package / "connections.yaml").write_text(yaml.safe_dump({"connections": connections}), encoding="utf-8")
    with pytest.raises(StoryPackageError, match=needle):
        load_story_package(package)


def test_loader_rejects_non_mapping_connections_yaml(tmp_path: Path) -> None:
    package = copied_fixture(tmp_path)
    (package / "connections.yaml").write_text("[]\n", encoding="utf-8")
    with pytest.raises(StoryPackageError, match="connection '<unknown>'"):
        load_story_package(package)


def test_package_without_connections_loads_with_empty_connections() -> None:
    assert load_story_package(ROOT / "lighthouse-keeper").connections == ()

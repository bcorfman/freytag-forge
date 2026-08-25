from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from storygame.authoring.causal_contracts import validate_causal_compiled_story
from storygame.authoring.compiler import _causal_story_as_compiled_story
from storygame.persistence.runtime_state_sqlite import RuntimeStateSqliteStore
from storygame.runtime.context import RuntimeContextBuilder
from storygame.runtime.facts import Fact
from storygame.runtime.narrative import RuntimeNarrativeProjection, narrative_package_from_story
from storygame.runtime.state import bootstrap_runtime_state
from tests.test_causal_spatial_projection_phase2 import _interaction_story


def _projection() -> RuntimeNarrativeProjection:
    raw = _interaction_story()
    raw["party_knowledge"] = [{"participant_id": "engineer", "truth_ids": ["failure"]}]
    story = validate_causal_compiled_story(raw)
    return RuntimeNarrativeProjection(_causal_story_as_compiled_story(story), narrative_package_from_story(story))


def test_runtime_package_retains_immutable_phase_four_declarations() -> None:
    package = _projection().narrative_package

    assert [item.id for item in package.participants] == ["engineer", "navigator"]
    assert [item.id for item in package.npc_performance_profiles] == ["engineer_manner"]
    assert [item.id for item in package.locations] == ["dock", "relay"]
    assert [item.id for item in package.connected_routes] == ["dock_relay"]
    assert [item.id for item in package.movement_plans] == ["engineer_to_relay"]
    assert [item.id for item in package.scene_subjects] == ["dock_console"]
    assert [item.id for item in package.evidence_realizations] == [
        "scan_console",
        "relay_log",
        "repair_record",
        "crew_testimony_realization",
    ]
    assert [item.id for item in package.group_encounters] == ["dock_watch"]
    assert [item.id for item in package.interaction_frames] == ["engineer_warning"]
    with pytest.raises(FrozenInstanceError):
        package.storylets = ()  # type: ignore[misc]


def test_bootstrap_projects_spatial_and_interaction_markers_as_facts() -> None:
    state = bootstrap_runtime_state(_projection())

    assert state.facts.has("at", "engineer", "dock")
    assert state.facts.has("present", "engineer", "dock")
    assert state.facts.has("public_name", "engineer", value="Iris Vale")
    assert state.facts.has("public_role", "engineer", value="systems engineer")
    assert state.facts.has("npc_availability", "engineer", value="present")
    assert state.facts.has("at", "dock_console", "dock")
    assert state.facts.has("inspectable", "dock_console", value="true")
    assert state.facts.has("at", "scan_console", "dock")
    assert state.facts.has("custody", "scan_console", "engineer")
    assert state.facts.has("evidence_discovered", "scan_console", value="false")
    for predicate in (
        "interaction_active",
        "interaction_completed",
        "interaction_aborted",
        "interaction_recently_used",
    ):
        assert state.facts.has(predicate, "engineer_warning", value="false")


def test_context_filters_off_scene_targets_and_scopes_private_speaker_knowledge() -> None:
    state = bootstrap_runtime_state(_projection())
    state.facts.assert_fact(Fact(predicate="motive", subject="engineer", value="Keep the crew safe."))
    state.facts.assert_fact(Fact(predicate="stance", subject="engineer", value="urgent"))
    state.facts.assert_fact(Fact(predicate="relationship", subject="engineer", object="player", value="trusting"))

    payload = RuntimeContextBuilder().build(state, "I examine the room.").payload

    assert [item["id"] for item in payload["current_targets"]["participants"]] == ["engineer", "navigator"]
    assert [item["id"] for item in payload["current_targets"]["scene_subjects"]] == ["dock_console"]
    assert [item["id"] for item in payload["current_targets"]["evidence"]] == ["scan_console"]
    assert "relay_log" not in str(payload["current_targets"])
    assert "failure" not in str(payload["facts"])
    speaker = payload["speaker_private_context"]["engineer"]
    assert speaker["known_truth_ids"] == ["failure"]
    assert speaker["performance_profile"]["id"] == "engineer_manner"
    assert {item["predicate"] for item in speaker["private_facts"]} >= {"motive", "relationship", "stance"}


def test_active_interaction_precedes_other_storylets_and_keeps_freeform_play() -> None:
    state = bootstrap_runtime_state(_projection())
    state.world.location = "relay"
    state.facts.retract_fact(Fact(predicate="at", subject="player", object="dock"))
    state.facts.assert_fact(Fact(predicate="at", subject="player", object="relay"))
    state.facts.retract_fact(Fact(predicate="at", subject="engineer", object="dock"))
    state.facts.retract_fact(Fact(predicate="present", subject="engineer", object="dock"))
    state.facts.assert_fact(Fact(predicate="at", subject="engineer", object="relay"))
    state.facts.assert_fact(Fact(predicate="present", subject="engineer", object="relay"))
    state.facts.assert_fact(Fact(predicate="knows", subject="player", object="failure"))
    state.facts.retract_fact(Fact(predicate="scene_pressure", subject="scene", value="0"))
    state.facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value="20"))
    state.facts.retract_fact(Fact(predicate="interaction_active", subject="engineer_warning", value="false"))
    state.facts.assert_fact(Fact(predicate="interaction_active", subject="engineer_warning", value="true"))
    for beat_id in ("setup", "rise"):
        state.beat_runtime[beat_id].completed_tags.add(f"{beat_id}_completed")

    opportunity = RuntimeContextBuilder().build(state, "I try an unrelated idea.").payload["narrative_opportunities"]

    assert opportunity["active_interaction"]["id"] == "engineer_warning"
    assert opportunity["active_interaction"]["response_obligations"] == ["answer direct concerns about crew safety"]
    assert [item["id"] for item in opportunity["storylets"]] == ["engineer_faces_cost"]
    assert opportunity["freeform_allowed"] is True


def test_phase_four_projection_survives_save_load_without_mutating_package(tmp_path) -> None:
    projection = _projection()
    state = bootstrap_runtime_state(projection)
    store = RuntimeStateSqliteStore(tmp_path / "runtime.db", namespace="phase-four")
    try:
        store.save("session", state)
        restored = store.load("session", projection)
    finally:
        store.close()

    assert restored.facts.has("custody", "scan_console", "engineer")
    restored_package = restored.narrative_package
    assert restored_package is projection.narrative_package
    assert restored_package is not None
    assert restored_package.movement_plans == projection.narrative_package.movement_plans

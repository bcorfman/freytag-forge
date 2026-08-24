"""Phase-5 deterministic storylet simulation coverage."""

from __future__ import annotations

import json
from copy import deepcopy

import pytest

from storygame.authoring.causal_contracts import validate_causal_compiled_story
from storygame.authoring.compiler import _causal_story_as_compiled_story
from storygame.authoring.storylet_simulation import (
    SIMULATION_POLICIES,
    simulate_storylets,
    write_simulation_report,
)
from storygame.authoring.storylet_simulation_cli import main as simulation_main
from storygame.runtime.facts import Fact
from storygame.runtime.narrative import RuntimeNarrativeProjection, narrative_package_from_story
from storygame.runtime.state import bootstrap_runtime_state
from tests.test_storylet_contract_phase1 import _storylet_story


def _projection(genre: str = "sci-fi") -> RuntimeNarrativeProjection:
    raw = deepcopy(_storylet_story())
    raw["genre"] = genre
    raw["profile"] = genre
    story = validate_causal_compiled_story(raw)
    return RuntimeNarrativeProjection(_causal_story_as_compiled_story(story), narrative_package_from_story(story))


def _state_factory():
    state = bootstrap_runtime_state(_projection())
    state.world.location = "relay"
    state.facts.retract_fact(Fact(predicate="at", subject="player", object="dock"))
    state.facts.assert_fact(Fact(predicate="at", subject="player", object="relay"))
    state.facts.assert_fact(Fact(predicate="present", subject="engineer", object="relay"))
    state.facts.assert_fact(Fact(predicate="knows", subject="player", object="failure"))
    state.facts.retract_fact(Fact(predicate="scene_pressure", subject="scene", value="0"))
    state.facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value="20"))
    for beat_id in ("setup", "rise"):
        state.beat_runtime[beat_id].completed_tags.add(f"{beat_id}_completed")
    return state


@pytest.mark.parametrize("genre", ("mystery", "fantasy", "sci-fi", "relationship"))
def test_simulation_drives_all_generic_policies_without_a_model_and_records_quality_metrics(genre: str) -> None:
    report = simulate_storylets(_projection(genre), _state_factory, max_turns=4)

    assert report.schema_version == "storylet-simulation-v1"
    assert report.source_id == "signal"
    assert tuple(case.policy for case in report.cases) == SIMULATION_POLICIES
    assert all(case.provider_request_count == 0 for case in report.cases)
    assert report.metrics.ending_reachability > 0
    assert report.metrics.selection_diversity > 0
    assert report.metrics.distinct_paths_to_climax >= 2
    assert report.metrics.protected_revelation_violations == 0
    assert report.metrics.storylet_reuse >= 0
    assert report.metrics.blocked_action_rate >= 0


def test_simulation_report_is_versioned_immutable_non_runtime_evidence(tmp_path) -> None:
    report = simulate_storylets(_projection(), _state_factory, max_turns=2)
    output = tmp_path / "signal.simulation.json"

    write_simulation_report(output, report)

    assert json.loads(output.read_text(encoding="utf-8"))["schema_version"] == "storylet-simulation-v1"
    with pytest.raises(ValueError, match="SIMULATION_OUTPUT_EXISTS"):
        write_simulation_report(output, report)


def test_simulation_cli_emits_non_runtime_evidence_for_a_reviewed_fixture(tmp_path) -> None:
    output = tmp_path / "vale.simulation.json"

    assert simulation_main(["--genre", "mystery", "--output", str(output), "--max-turns", "1"]) == 0

    assert json.loads(output.read_text(encoding="utf-8"))["source_id"] == "vale_mansion_rebuild"

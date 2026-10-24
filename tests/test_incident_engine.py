from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.incidents import resolved_incident_outcome
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

FIXTURE = Path(__file__).parent / "fixtures" / "stories" / "lighthouse-incident"


def _package():
    return load_story_package(FIXTURE)


def _provider(knowledge_id: str | None = None, text: str = "Ada waits."):
    def provide(_player_input: str):
        payload = {"segments": [{"kind": "narration", "text": text}]}
        if knowledge_id is not None:
            payload["segments"][0]["grounding_ids"] = [knowledge_id]
            payload["selected_knowledge_ids"] = [knowledge_id]
        return payload

    return provide


def _true_facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if fact.subject == "story" and fact.value == "true"}


def test_copy_chart_resolves_and_completes_without_min_turn_floor() -> None:
    state = RuntimeState.bootstrap(_package())
    RuntimeEngine(state, _provider("k_copy_chart", "Ada copies the chart.")).turn("Copy the chart.")

    facts = _true_facts(state)
    assert state.current_scene_id == "1B"
    assert {"chart_copied", "chart_page_torn", "incident_outcome_resolved"} <= facts
    assert "boat_route_known" not in facts


def test_learn_route_resolves_without_chart_cost() -> None:
    state = RuntimeState.bootstrap(_package())
    RuntimeEngine(state, _provider("k_find_key", "Ada finds the brass key and learns the boat route.")).turn(
        "Learn the boat route."
    )

    facts = _true_facts(state)
    assert state.current_scene_id == "1B"
    assert "boat_route_known" in facts
    assert "chart_page_torn" not in facts
    assert "chart_copied" not in facts


def test_scene_without_incident_keeps_min_turn_floor() -> None:
    package = _package().model_copy(update={"incidents": ()})
    state = RuntimeState.bootstrap(package)
    state.facts.assert_fact(Fact(predicate="incident_outcome_resolved", subject="story", value="true"))
    engine = RuntimeEngine(state, _provider())

    engine.turn("Wait.")
    assert state.current_scene_id == "1A"
    engine.turn("Wait again.")
    assert state.current_scene_id == "1B"


def test_unresolved_incident_misses_window_without_advantage_or_successor() -> None:
    state = RuntimeState.bootstrap(_package())
    engine = RuntimeEngine(state, _provider())

    for command in ("Wait.", "Wait again.", "Keep waiting."):
        engine.turn(command)

    facts = _true_facts(state)
    assert state.current_scene_id == "1A"
    assert "tide_has_turned" in facts
    assert not {"chart_copied", "chart_page_torn", "boat_route_known"} & facts


def test_incident_outcomes_are_exclusive_after_one_fires() -> None:
    state = RuntimeState.bootstrap(_package())
    RuntimeEngine(state, _provider("k_copy_chart", "Ada copies the chart.")).turn("Copy the chart.")

    facts = _true_facts(state)
    assert "chart_copied" in facts
    assert "boat_route_known" not in facts


def test_resolved_incident_outcome_none_a_b_and_first_when_both_true() -> None:
    incident = _package().incidents[0]
    facts = FactStore()
    assert resolved_incident_outcome(incident, facts) is None

    facts.assert_fact(Fact(predicate="chart_copied", subject="story", value="true"))
    assert resolved_incident_outcome(incident, facts).id == "copy_chart"

    facts = FactStore()
    facts.assert_fact(Fact(predicate="boat_route_known", subject="story", value="true"))
    assert resolved_incident_outcome(incident, facts).id == "learn_route"

    facts.asserted.add(Fact(predicate="chart_copied", subject="story", value="true"))
    assert resolved_incident_outcome(incident, facts).id == "copy_chart"


def test_completes_scene_false_keeps_floor(tmp_path: Path) -> None:
    package_dir = tmp_path / "lighthouse-incident"
    shutil.copytree(FIXTURE, package_dir)
    incident_path = package_dir / "incidents.yaml"
    incidents = yaml.safe_load(incident_path.read_text(encoding="utf-8"))
    incidents["incidents"][0]["completes_scene"] = False
    incident_path.write_text(yaml.safe_dump(incidents, sort_keys=False), encoding="utf-8")

    package = load_story_package(package_dir)
    state = RuntimeState.bootstrap(package)
    RuntimeEngine(state, _provider("k_copy_chart", "Ada copies the chart.")).turn("Copy the chart.")

    assert state.current_scene_id == "1A"

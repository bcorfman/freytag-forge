from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import load_story_package
from storygame.story_package.loader import StoryPackageError

ROOT = Path(__file__).parent / "fixtures" / "stories"
FIXTURE = ROOT / "lighthouse-incident"


def _copy_fixture(tmp_path: Path) -> Path:
    destination = tmp_path / "lighthouse-incident"
    shutil.copytree(FIXTURE, destination)
    return destination


def _read_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _write_yaml(path: Path, value: object) -> None:
    path.write_text(yaml.safe_dump(value, sort_keys=False), encoding="utf-8")


def _incident(package: Path) -> dict:
    incidents = _read_yaml(package / "incidents.yaml")
    return incidents["incidents"][0]


def _outcome(package: Path, index: int) -> dict:
    return _incident(package)["outcomes"][index]


def _duplicate_scene(package: Path) -> str:
    incidents = _read_yaml(package / "incidents.yaml")
    duplicate = dict(incidents["incidents"][0])
    duplicate["id"] = "tide_window_two"
    incidents["incidents"].append(duplicate)
    _write_yaml(package / "incidents.yaml", incidents)
    return "1A"


def _unknown_scene(package: Path) -> str:
    incident = _incident(package)
    incident["scene_id"] = "9Z"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "9Z"


def _unknown_outcome_storylet(package: Path) -> str:
    incident = _incident(package)
    incident["outcomes"][0]["storylet_id"] = "SL-1B-A"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "SL-1B-A"


def _nonexclusive(package: Path) -> str:
    incident = _incident(package)
    outcome = incident["outcomes"][1]
    outcome["realization_id"] = "r1"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "r1"


def _unknown_advantage(package: Path) -> str:
    incident = _incident(package)
    outcome = incident["outcomes"][0]
    outcome["advantages"] = ["unknown_advantage"]
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "unknown_advantage"


def _unasserted_fact(package: Path) -> str:
    incident = _incident(package)
    outcome = incident["outcomes"][1]
    outcome["advantages"] = ["chart_copied"]
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "chart_copied"


def _unknown_event(package: Path) -> str:
    incident = _incident(package)
    incident["missed_window_event_id"] = "missing_event"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "missing_event"


def _event_forces_successor(package: Path) -> str:
    pacing = _read_yaml(package / "pacing.yaml")
    pacing["events"][0]["transition_id"] = "t_1a_1b"
    _write_yaml(package / "pacing.yaml", pacing)
    return "t_1a_1b"


def _unknown_transition(package: Path) -> str:
    incident = _incident(package)
    incident["successor_transition_id"] = "missing_transition"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "missing_transition"


def _unknown_observation(package: Path) -> str:
    incident = _incident(package)
    incident["observation_knowledge_ids"] = ["missing_knowledge"]
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "missing_knowledge"


def _overlapping_delivery_cost(package: Path) -> str:
    handoffs = _read_yaml(package / "handoffs.yaml")
    handoffs["deliveries"][0]["costs"] = [{"op": "assert", "fact_id": "chart_page_torn", "value": True}]
    _write_yaml(package / "handoffs.yaml", handoffs)
    return "chart_page_torn"


REJECTIONS = [
    (
        "duplicate incident id",
        lambda package: _write_yaml(
            package / "incidents.yaml", {"incidents": [_incident(package), _incident(package)]}
        ),
        "tide_window",
    ),
    ("second incident in scene", _duplicate_scene, "1A"),
    ("unknown scene", _unknown_scene, "9Z"),
    ("unknown outcome storylet", _unknown_outcome_storylet, "SL-1B-A"),
    ("non-exclusive realizations", _nonexclusive, "r1"),
    ("unknown advantage", _unknown_advantage, "unknown_advantage"),
    ("unasserted outcome fact", _unasserted_fact, "chart_copied"),
    ("unknown missed-window event", _unknown_event, "missing_event"),
    ("missed-window successor", _event_forces_successor, "t_1a_1b"),
    ("unknown successor transition", _unknown_transition, "missing_transition"),
    ("unknown observation knowledge", _unknown_observation, "missing_knowledge"),
    ("delivery cost overlaps outcome", _overlapping_delivery_cost, "chart_page_torn"),
]


def test_incident_fixture_loads_with_two_outcomes() -> None:
    package = load_story_package(FIXTURE)
    assert len(package.incidents) == 1
    assert [outcome.id for outcome in package.incidents[0].outcomes] == ["copy_chart", "learn_route"]


def test_existing_packages_have_no_incidents() -> None:
    assert load_story_package(ROOT.parent.parent.parent / "data" / "stories" / "continuity-initiative").incidents == ()
    assert load_story_package(ROOT / "lighthouse-keeper").incidents == ()


@pytest.mark.parametrize("case_name, mutate, offending", REJECTIONS, ids=[case[0] for case in REJECTIONS])
def test_incident_rejections_include_incident_and_offending_id(
    tmp_path: Path, case_name, mutate, offending: str
) -> None:
    package = _copy_fixture(tmp_path)
    mutate(package)
    message_pattern = rf"tide_window.*{re.escape(offending)}|{re.escape(offending)}.*tide_window"
    with pytest.raises(StoryPackageError, match=message_pattern):
        load_story_package(package)


def test_incidents_yaml_requires_an_incidents_list(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    (package / "incidents.yaml").write_text("[]\n", encoding="utf-8")
    with pytest.raises(StoryPackageError, match="incidents.yaml.*mapping"):
        load_story_package(package)


def test_incidents_yaml_requires_a_list_value(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    (package / "incidents.yaml").write_text("incidents: {id: tide_window}\n", encoding="utf-8")
    with pytest.raises(StoryPackageError, match="incidents.yaml.*list"):
        load_story_package(package)


def test_delivery_cost_without_incident_cost_overlap_is_valid(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    handoffs = _read_yaml(package / "handoffs.yaml")
    handoffs["deliveries"][0]["costs"] = [{"op": "assert", "fact_id": "tide_has_turned", "value": True}]
    _write_yaml(package / "handoffs.yaml", handoffs)
    assert len(load_story_package(package).incidents) == 1

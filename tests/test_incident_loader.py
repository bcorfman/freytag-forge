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
    outcome["costs"] = ["brass_key_found"]
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


def _unknown_recovery_storylet(package: Path) -> str:
    incident = _incident(package)
    incident["recovery_storylet_id"] = "SL-1A-C"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "SL-1A-C"


def _recovery_in_other_scene(package: Path) -> str:
    routes = _read_yaml(package / "storylet-routes.yaml")
    recovery = dict(next(item for item in routes["storylets"] if item["id"] == "SL-1A-B"))
    recovery["id"] = "SL-1B-A"
    recovery["scene_id"] = "1B"
    recovery["activation"]["pacing"]["target_turn"] = 1
    recovery["activation"]["pacing"]["latest_turn"] = 1
    routes["storylets"].append(recovery)
    incident = _incident(package)
    incident["recovery_storylet_id"] = "SL-1B-A"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    _write_yaml(package / "storylet-routes.yaml", routes)
    knowledge = _read_yaml(package / "knowledge.yaml")
    recovery_knowledge = next(item for item in knowledge["knowledge"] if item["id"] == "k_recover_chart")
    recovery_knowledge["available_in_scenes"] = ["1B"]
    recovery_knowledge["source"]["storylet_id"] = "SL-1B-A"
    _write_yaml(package / "knowledge.yaml", knowledge)
    storylets = (package / "storylets.md").read_text(encoding="utf-8")
    storylets += """

### SL-1B-A — Recover the Chart Elsewhere

**Source beats:** [The Search](plot.md#scene-1a1--the-search)

**Allowed scene:** `1B`

**Available when**
- The tide has turned.

**Participants / items**
- Ada Lovell and the logbook.

**Dramatic purpose**
- Restore the missed opportunity.

**Possible realizations**
- Ada recovers the chart.

**Effects**
- Establishes `chart_copied`.

**Completion**
- The chart is recovered.

**Abort**
- Ada leaves.

**Protected boundary**
- None.

**Pacing window**
- earliest: `turn 0`
- target: `turn 1`
- latest: `turn 1`
"""
    (package / "storylets.md").write_text(storylets, encoding="utf-8")
    return "1B"


def _recovery_reuses_shared_storylet(package: Path) -> str:
    incident = _incident(package)
    incident["recovery_storylet_id"] = "SL-1A-A"
    _write_yaml(package / "incidents.yaml", {"incidents": [incident]})
    return "SL-1A-A"


def _recovery_has_no_qualifying_realization(package: Path) -> str:
    routes = _read_yaml(package / "storylet-routes.yaml")
    recovery = next(item for item in routes["storylets"] if item["id"] == "SL-1A-B")
    recovery["realization_options"][0]["operations"] = [
        {"op": "assert", "fact_id": "chart_copied", "value": True},
        {"op": "assert", "fact_id": "chart_page_torn", "value": True},
    ]
    _write_yaml(package / "storylet-routes.yaml", routes)
    knowledge = _read_yaml(package / "knowledge.yaml")
    next(item for item in knowledge["knowledge"] if item["id"] == "k_recover_chart")["establishes"] = [
        {"op": "assert", "fact_id": "chart_copied", "value": True},
        {"op": "assert", "fact_id": "chart_page_torn", "value": True},
    ]
    _write_yaml(package / "knowledge.yaml", knowledge)
    return "SL-1A-B"


def _recovery_awards_both_outcomes(package: Path) -> str:
    routes = _read_yaml(package / "storylet-routes.yaml")
    recovery = next(item for item in routes["storylets"] if item["id"] == "SL-1A-B")
    recovery["realization_options"][0]["operations"] = [
        {"op": "assert", "fact_id": "chart_copied", "value": True},
        {"op": "assert", "fact_id": "chart_page_torn", "value": True},
        {"op": "assert", "fact_id": "boat_route_known", "value": True},
        {"op": "assert", "fact_id": "recovery_cost_paid", "value": True},
    ]
    _write_yaml(package / "storylet-routes.yaml", routes)
    knowledge = _read_yaml(package / "knowledge.yaml")
    next(item for item in knowledge["knowledge"] if item["id"] == "k_recover_chart")["establishes"] = [
        {"op": "assert", "fact_id": "chart_copied", "value": True},
        {"op": "assert", "fact_id": "chart_page_torn", "value": True},
        {"op": "assert", "fact_id": "boat_route_known", "value": True},
        {"op": "assert", "fact_id": "recovery_cost_paid", "value": True},
    ]
    _write_yaml(package / "knowledge.yaml", knowledge)
    return "SL-1A-B"


def _recovery_asserts_only_extra_fact(package: Path) -> str:
    routes = _read_yaml(package / "storylet-routes.yaml")
    recovery = next(item for item in routes["storylets"] if item["id"] == "SL-1A-B")
    recovery["realization_options"][0]["operations"] = [
        {"op": "assert", "fact_id": "recovery_cost_paid", "value": True}
    ]
    _write_yaml(package / "storylet-routes.yaml", routes)
    knowledge = _read_yaml(package / "knowledge.yaml")
    next(item for item in knowledge["knowledge"] if item["id"] == "k_recover_chart")["establishes"] = [
        {"op": "assert", "fact_id": "recovery_cost_paid", "value": True}
    ]
    _write_yaml(package / "knowledge.yaml", knowledge)
    return "SL-1A-B"


def _recovery_does_not_require_window(package: Path) -> str:
    routes = _read_yaml(package / "storylet-routes.yaml")
    recovery = next(item for item in routes["storylets"] if item["id"] == "SL-1A-B")
    recovery["activation"]["conditions"] = []
    _write_yaml(package / "storylet-routes.yaml", routes)
    return "tide_has_turned"


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
    ("unknown recovery storylet", _unknown_recovery_storylet, "SL-1A-C"),
    ("recovery storylet in another scene", _recovery_in_other_scene, "1B"),
    ("recovery reuses outcome storylet", _recovery_reuses_shared_storylet, "SL-1A-A"),
    ("recovery has no extra fact", _recovery_has_no_qualifying_realization, "SL-1A-B"),
    ("recovery awards both outcomes", _recovery_awards_both_outcomes, "SL-1A-B"),
    ("recovery misses window activation", _recovery_does_not_require_window, "tide_has_turned"),
]


def test_incident_fixture_loads_with_two_outcomes() -> None:
    package = load_story_package(FIXTURE)
    assert len(package.incidents) == 1
    assert [outcome.id for outcome in package.incidents[0].outcomes] == ["copy_chart", "learn_route"]


def test_neutral_zero_match_recovery_loads_with_two_outcomes(tmp_path: Path) -> None:
    package = _copy_fixture(tmp_path)
    _recovery_asserts_only_extra_fact(package)

    loaded = load_story_package(package)

    assert len(loaded.incidents[0].outcomes) == 2


def test_real_package_declares_the_continuity_incident() -> None:
    incidents = load_story_package(ROOT.parent.parent.parent / "data" / "stories" / "continuity-initiative").incidents
    assert [incident.id for incident in incidents] == [
        "i_1c_freight_transfer",
        "i_2a_real_leak",
        "i_2b_audit",
        "i_2c_rebecca_corridor",
    ]
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

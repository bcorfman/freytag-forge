"""Hermetic tests for the deterministic scene-affordance bench."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bench.affordance_map import _gate_metadata, build_affordance_map, check_affordance_map
from storygame.story_package.loader import load_story_package

CONTINUITY = Path("data/stories/continuity-initiative")
LIGHTHOUSE = Path("tests/fixtures/stories/lighthouse-keeper")


@pytest.fixture(scope="module")
def lighthouse():
    return load_story_package(LIGHTHOUSE)


def test_lighthouse_map_is_json_and_has_every_scene(lighthouse):
    amap = build_affordance_map(lighthouse)
    json.dumps(amap)
    assert [scene["scene_id"] for scene in amap["scenes"]] == [scene.metadata.scene_id for scene in lighthouse.scenes]


def test_action_evidence_without_object_group_does_not_use_entity_ids(lighthouse):
    amap = build_affordance_map(lighthouse)
    sources = [source for gate in amap["scenes"][0]["gates"] for source in gate["sources"]]
    key_sources = [source for source in sources if source["id"] == "k_find_key"]
    if key_sources:
        assert "brass_key" not in {item["entity_id"] for item in key_sources[0]["affordances"]}


def test_engine_source_and_empty_realization_are_checkable(lighthouse):
    amap = build_affordance_map(lighthouse)
    gate = {
        "transition_id": "synthetic",
        "fact_id": "clock",
        "sources": [
            {
                "id": "clock_event",
                "kind": "engine",
                "player_earned": False,
                "requires": [],
                "affordances": [],
                "realization_texts": [],
            }
        ],
    }
    amap["scenes"][0]["gates"].append(gate)
    assert any(finding["check"] == 4 for finding in check_affordance_map(lighthouse, amap))


@pytest.mark.parametrize(
    ("check", "broken"),
    [
        (
            1,
            lambda amap: amap["scenes"][0]["gates"].append(
                {"transition_id": "broken", "fact_id": "missing", "sources": []}
            ),
        ),
        (
            2,
            lambda amap: amap["scenes"][0]["gates"].append(
                {
                    "transition_id": "broken",
                    "fact_id": "hidden",
                    "sources": [
                        {
                            "id": "earned",
                            "kind": "knowledge",
                            "player_earned": True,
                            "requires": [],
                            "affordances": [
                                {
                                    "entity_id": "hidden",
                                    "name": "hidden",
                                    "visible_at_entry": False,
                                    "revealed_by": None,
                                }
                            ],
                        }
                    ],
                }
            ),
        ),
        (
            3,
            lambda amap: amap["scenes"][0]["gates"].append(
                {
                    "transition_id": "broken",
                    "fact_id": "unshown",
                    "sources": [
                        {
                            "id": "earned",
                            "kind": "knowledge",
                            "player_earned": True,
                            "requires": [],
                            "affordances": [
                                {
                                    "entity_id": "brass_key",
                                    "name": "not in entry",
                                    "visible_at_entry": True,
                                    "revealed_by": None,
                                }
                            ],
                        }
                    ],
                }
            ),
        ),
        (
            4,
            lambda amap: amap["scenes"][0]["gates"].append(
                {
                    "transition_id": "broken",
                    "fact_id": "engine",
                    "sources": [
                        {
                            "id": "engine",
                            "kind": "engine",
                            "player_earned": False,
                            "requires": [],
                            "affordances": [],
                            "realization_texts": [],
                        }
                    ],
                }
            ),
        ),
    ],
)
def test_each_check_reports_a_deliberately_broken_map(lighthouse, check, broken):
    amap = build_affordance_map(lighthouse)
    broken(amap)
    assert any(finding["check"] == check for finding in check_affordance_map(lighthouse, amap))


def test_whole_package_findings_match_recorded_gaps():
    package = load_story_package(CONTINUITY)
    amap = build_affordance_map(package)
    expected = json.loads((Path("bench") / "affordance_known_gaps.json").read_text(encoding="utf-8"))
    actual = [
        {key: finding[key] for key in ("check", "scene_id", "gate", "subject")}
        for finding in check_affordance_map(package, amap)
    ]
    assert sorted(actual, key=lambda item: (item["scene_id"], item["gate"], item["subject"], item["check"])) == expected


def test_continuity_1a_gate_affordances_include_drawer_and_memory_card():
    package = load_story_package(CONTINUITY)
    amap = build_affordance_map(package)
    scene = next(scene for scene in amap["scenes"] if scene["scene_id"] == "1A")
    affordances = [affordance for gate in scene["gates"] for affordance in gate["affordances"]]
    affordance_ids = {affordance["entity_id"] for affordance in affordances}
    assert {"michelle_drawer", "michelle_workstation", "kristin_laptop"} <= affordance_ids
    assert all(
        affordance["visible_at_entry"]
        for affordance in affordances
        if affordance["entity_id"]
        in {
            "michelle_drawer",
            "michelle_workstation",
            "kristin_laptop",
        }
    )
    assert any("memory_card" in source["reveals"] for gate in scene["gates"] for source in gate["sources"])


def test_protagonist_is_never_an_affordance():
    package = load_story_package(CONTINUITY)
    amap = build_affordance_map(package)
    assert all(
        affordance["entity_id"] != package.protagonist_id
        for scene in amap["scenes"]
        for gate in scene["gates"]
        for affordance in gate["affordances"]
    )


def test_source_reveal_is_separate_from_its_affordances():
    package = load_story_package(CONTINUITY)
    amap = build_affordance_map(package)
    sources = [source for scene in amap["scenes"] for gate in scene["gates"] for source in gate["sources"]]
    source = next(source for source in sources if source["id"] == "k_sl_1a_b_r0")
    assert source["reveals"] == ["memory_card"]
    assert "memory_card" not in {affordance["entity_id"] for affordance in source["affordances"]}


def test_affordances_and_scene_location_include_aliases():
    package = load_story_package(CONTINUITY)
    amap = build_affordance_map(package)
    scene = next(scene for scene in amap["scenes"] if scene["scene_id"] == "1A")
    assert amap["protagonist_id"] == package.protagonist_id
    assert scene["location"] == {
        "id": "mcgehee_home",
        "name": "Michelle's house",
        "aliases": ["Michelle's home", "the house"],
    }
    assert all("aliases" in affordance for gate in scene["gates"] for affordance in gate["affordances"])


@pytest.mark.parametrize("root", [CONTINUITY, LIGHTHOUSE])
def test_all_package_maps_have_scene_entries_and_json(root):
    package = load_story_package(root)
    amap = build_affordance_map(package)
    json.dumps(amap)
    assert len(amap["scenes"]) == len(package.scenes)


def test_lighthouse_has_no_findings(lighthouse):
    assert check_affordance_map(lighthouse, build_affordance_map(lighthouse)) == []


def test_gate_metadata_classifies_a_player_earned_chain(lighthouse):
    earned = {
        "id": "earned",
        "facts": {"lead"},
        "requires_predicates": [],
        "player_earned": True,
    }
    result = _gate_metadata(lighthouse, "lead", [earned], {"lead": [earned]})
    assert result[:3] == (
        "player_gated",
        "A transition gate depends on a source earned by a player action.",
        ["earned"],
    )


def test_gate_metadata_classifies_an_engine_only_chain(lighthouse):
    event = {
        "id": "clock",
        "facts": {"pressure"},
        "requires_predicates": [],
        "player_earned": False,
    }
    result = _gate_metadata(lighthouse, "pressure", [event], {"pressure": [event]})
    assert result[:3] == (
        "timer_by_design",
        "Every transition gate source is engine-driven, unconditional, or guaranteed by scene entry.",
        [],
    )


def test_bridge_activation_facts_are_requires(lighthouse):
    package = load_story_package(CONTINUITY)
    amap = build_affordance_map(package)
    source = next(
        source
        for scene in amap["scenes"]
        for gate in scene["gates"]
        for source in gate["sources"]
        if source["id"] == "storylet:bridge_1b_departure"
    )
    assert [requirement["fact_id"] for requirement in source["requires"]] == [
        "park_pursuit_resolved",
        "transport_route_identified",
        "brandon_identified",
        "missing_may_be_alive",
    ]


def test_continuity_core_scenes_are_player_gated():
    package = load_story_package(CONTINUITY)
    amap = build_affordance_map(package)
    classes = {scene["scene_id"]: scene["gate_class"] for scene in amap["scenes"]}
    assert {scene_id: classes[scene_id] for scene_id in ("1A", "2A", "2C")} == {
        "1A": "player_gated",
        "2A": "player_gated",
        "2C": "player_gated",
    }

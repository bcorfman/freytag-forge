from __future__ import annotations

from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)
NEW_SENTENCE = (
    "The observation shaft overlooks the processing line. "
    "Kristin can read the identification numbers on the uniforms below."
)


def _knowledge() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


def _scene_1c_state() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1C"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1C")
    state._assert_scene_entry_fact("1C")
    state.facts.assert_fact(Fact(predicate="facility_proof", subject="story", value="true"))
    return state


def test_1c_a_deliveries_have_the_reading_pointer() -> None:
    knowledge = _knowledge()
    assert knowledge["k_sl_1c_a_r1"]["delivery_text"] == (
        "Kristin finds electrical load, fresh air from the vents, and signs of recent work. "
        "The freight terminal is still running. " + NEW_SENTENCE
    )
    assert knowledge["k_sl_1c_a_r2"]["delivery_text"] == (
        "The transit token opens a service entrance to an active facility below. "
        "A service map shows a dry maintenance climb to the drainage spine. "
        "Kristin sees that route is too exposed to use now. " + NEW_SENTENCE
    )


def test_1c_reading_pointer_matches_real_matcher() -> None:
    knowledge = _knowledge()
    ids = ("k_sl_1c_a_r1", "k_sl_1c_a_r2", "k_sl_1c_b_r1", "k_sl_1c_b_r2", "k_sl_1c_c_r1", "k_sl_1c_c_r2")
    candidates = {item_id: tuple(tuple(group) for group in knowledge[item_id]["action_evidence"]) for item_id in ids}
    cases = {
        "k_sl_1c_b_r1": (
            "Read the identification numbers on the uniforms below.",
            "Copy the ID numbers.",
            "Compare the prisoners with missing-person records.",
            "Read the numbers on the uniforms.",
            "Check the uniforms for numbers.",
            "Record the numbers on the prisoners' uniforms.",
        ),
        "k_sl_1c_b_r2": ("Search the processing line for Michelle.", "Look for Michelle in the processing area."),
        "": (
            "Inspect the observation shaft and look for a way down into the processing area.",
            "Examine the locked stairs and the surrounding service level for a way to unlock or bypass them.",
            "Climb down the ladder from the observation shaft to the service level.",
            "Find an entrance to the processing line.",
            "Enter the biohazard containment zone.",
            "Use the transit token on the access panel.",
            "Inspect the uniforms.",
            "Read my notes about the missing people.",
            "Check the numbers on my phone.",
            "Read the prisoner numbers.",
        ),
        "k_sl_1c_b_r1,k_sl_1c_b_r2": ("Check the ID numbers and look for Michelle in the processing line.",),
    }
    for expected, commands in cases.items():
        expected_ids = set(expected.split(",")) if expected else set()
        for command in commands:
            actual = {item_id for item_id, evidence in candidates.items() if _matches_all(evidence, command)}
            assert actual == expected_ids, (command, actual)


def test_1c_b_r1_first_two_evidence_groups_are_unchanged() -> None:
    knowledge = _knowledge()
    assert knowledge["k_sl_1c_b_r1"]["action_evidence"][:2] == [
        [
            "compare",
            "match",
            "cross-check",
            "check",
            "read",
            "examine",
            "inspect",
            "observe",
            "look at",
            "record",
            "copy",
            "photograph",
            "capture",
            "write down",
            "log",
        ],
        [
            "prisoners",
            "captives",
            "people in the processing area",
            "uniforms",
            "uniform",
            "workers' uniforms",
            "identification numbers",
            "ID numbers",
        ],
    ]


def test_1c_a_delivery_is_accepted_after_facility_proof() -> None:
    text = PACKAGE.knowledge_indexes.by_id["k_sl_1c_a_r1"].delivery_text
    state = _scene_1c_state()
    result = RuntimeEngine(state, lambda _input: {"segments": [{"kind": "narration", "text": text}]}).turn(
        "Inspect the loading docks for signs of activity."
    )
    assert text in result.narration
    assert state.facts.matching("facility_proof", subject="story")
    assert not state.facts.matching("captives_confirmed_alive", subject="story")

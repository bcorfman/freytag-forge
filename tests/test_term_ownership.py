from __future__ import annotations

import shutil
from pathlib import Path

import yaml

from storygame.audit import audit_package
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeGuards
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

LIVE_PACKAGE = Path("data/stories/continuity-initiative")


def test_the_check_flags_a_later_owned_term_used_by_an_earlier_entry(tmp_path: Path) -> None:
    package = tmp_path / "continuity-initiative"
    shutil.copytree(LIVE_PACKAGE, package)
    knowledge_path = package / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    entry = next(item for item in knowledge["knowledge"] if item["id"] == "k_sl_1c_g_r1")
    group = next(group for group in entry["must_convey"] if "broadcast" in group)
    group[:] = ["emergency statement", "broadcast"]
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

    findings = [
        finding
        for finding in audit_package(package)["findings"]
        if finding["check"] == "earlier_scene_uses_later_owned_term"
    ]

    assert any(
        "emergency statement" in finding["detail"]
        and "k_sl_1b_g_r1" in finding["detail"]
        and "k_sl_1c_g_r1" in finding["detail"]
        for finding in findings
    )
    assert ("1A", "k_sl_1a_h_r1") in {
        (finding["scene_id"], entry_id)
        for finding in findings
        for entry_id in ("k_sl_1a_h_r1", "k_sl_1b_g_r1")
        if entry_id in finding["detail"]
    }


def test_the_live_story_has_no_term_ownership_findings() -> None:
    report = audit_package(LIVE_PACKAGE)

    assert not any(finding["check"] == "earlier_scene_uses_later_owned_term" for finding in report["findings"])
    checks = {finding["check"] for finding in report["findings"]}
    assert {"beat_overprojection", "prompt_hygiene"} <= checks


def test_the_park_statement_phrase_is_not_a_1c_only_leak_term() -> None:
    package = load_story_package(LIVE_PACKAGE)
    owners = set(package.knowledge_indexes.leak_term_to_knowledge.get("emergency statement", ()))
    owner_entries = package.knowledge_indexes.by_id

    assert not owners or any(
        scene_id in owner_entries[owner_id].available_in_scenes for owner_id in owners for scene_id in ("1A", "1B")
    ), f"emergency statement owners are later-scene-only: {owners}"


def test_an_earned_mouthing_may_be_echoed_in_1b() -> None:
    package = load_story_package(LIVE_PACKAGE)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1B").metadata
    entry = next(item for item in package.knowledge.knowledge if item.id == "k_sl_1b_g_r1")
    established_fact = next(operation.fact_id for operation in entry.establishes if operation.op == "assert")

    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "1B"
    state.phase = scene.freytag_phase
    state._assert_scene_entry_fact("1B")
    apply_scene_placements(package, state.facts, "1B")
    state.facts.assert_fact(Fact(predicate=established_fact, subject="story", value="true"))
    assert entry.id in KnowledgeGuards(state).earned_ids
    assert "k_sl_1c_g_r1" not in KnowledgeGuards(state).earned_ids

    narration = (
        "The stranger mouths the loudspeaker's emergency statement along with it, his eyes fixed on Kristin. "
        '"...all citizens are advised to remain calm..." The stranger\'s gaze lingers on Kristin as the moment passes. '
        "Kristin stays still and watches him."
    )
    result = RuntimeEngine(
        state,
        lambda _: {"segments": [{"kind": "narration", "text": narration}]},
    ).turn("Ask the man about Michelle.")

    assert isinstance(result.segments[0].text, str)
    assert "emergency statement" in result.segments[0].text

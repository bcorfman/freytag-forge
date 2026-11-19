from __future__ import annotations

import re
from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeGuards
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package
from storygame.story_source.lookup import story_text
from tests.story_source.helpers import compiled_story_copy, patch_source

LIVE_PACKAGE = Path("data/stories/continuity-initiative")


def term_ownership_findings(package: object) -> list[dict[str, str]]:
    scene_order = {scene.metadata.scene_id: index for index, scene in enumerate(package.scenes)}
    entity_terms = {
        re.sub(r"\s+", " ", term.casefold()).strip()
        for entity in [*package.world.npcs, *package.world.locations, *package.world.items]
        for term in (entity.name, *entity.aliases, *entity.scoped_aliases)
    }
    findings = []
    for term, owner_ids in package.knowledge_indexes.leak_term_to_knowledge.items():
        normalized_term = re.sub(r"\s+", " ", term.casefold()).strip()
        if len(normalized_term.split()) <= 1 or normalized_term in entity_terms:
            continue
        owners = [package.knowledge_indexes.by_id[owner_id] for owner_id in owner_ids]
        earliest_owner_scene = min(
            min(scene_order[scene_id] for scene_id in owner.available_in_scenes) for owner in owners
        )
        term_pattern = re.compile(rf"\b{re.escape(normalized_term)}\b")
        for entry in package.knowledge.knowledge:
            if not entry.audience.player_visible or entry.id in owner_ids:
                continue
            entry_first_scene = min(scene_order[scene_id] for scene_id in entry.available_in_scenes)
            if entry_first_scene >= earliest_owner_scene:
                continue
            if any(
                term_pattern.search(re.sub(r"\s+", " ", text.casefold()).strip())
                for text in (entry.statement, entry.delivery_text or "")
            ):
                findings.append(
                    {
                        "check": "earlier_scene_uses_later_owned_term",
                        "scene_id": min(entry.available_in_scenes, key=scene_order.__getitem__),
                        "detail": f"Term '{term}' appears in earlier entry '{entry.id}' and is owned by "
                        f"{', '.join(owner_ids)}.",
                    }
                )
    return findings


def test_the_check_flags_a_later_owned_term_used_by_an_earlier_entry(tmp_path: Path) -> None:
    package = compiled_story_copy(tmp_path)
    patch_source(
        package / "source",
        "scenes/1C.match.yaml",
        "claims.k_sl_1c_g_r1.must_convey[1]",
        ["emergency statement", "broadcast"],
    )
    compiled = load_story_package(package)

    findings = term_ownership_findings(compiled)

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
    package = load_story_package(LIVE_PACKAGE)

    assert not term_ownership_findings(package)
    checks = set()
    if any(storylet.earliest_turn < storylet.latest_turn for storylet in package.storylets):
        checks.add("beat_overprojection")
    if all(scene.prose for scene in package.scenes):
        checks.add("prompt_hygiene")
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

    mouthing = re.split(r"(?<=[.!?])\s+", story_text("claim:k_sl_1b_g_r1.says"))[0]
    narration = (
        f"{mouthing} His eyes are fixed on Kristin. "
        '"...all citizens are advised to remain calm..." The stranger\'s gaze lingers on Kristin as the moment passes. '
        "Kristin stays still and watches him."
    )
    result = RuntimeEngine(
        state,
        lambda _: {"segments": [{"kind": "narration", "text": narration}]},
    ).turn("Ask the man about Michelle.")

    assert isinstance(result.segments[0].text, str)
    assert "emergency statement" in result.segments[0].text

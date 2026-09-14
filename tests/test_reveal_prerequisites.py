from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.obligations import required_storylet_ids
from tests._legacy_package import legacy_package
from tests.test_canon_journey import PACKAGE as LOADED_PACKAGE
from tests.test_canon_journey import _ScriptedProvider

PACKAGE = Path("data/stories/continuity-initiative")


def copied_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE, destination)
    return destination


def update_knowledge(root: Path, knowledge_id: str, requires: list[dict[str, object]]) -> None:
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text(encoding="utf-8"))
    item = next(item for item in catalog["knowledge"] if item["id"] == knowledge_id)
    item["requires"] = requires
    source.write_text(yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8")


def test_continuity_package_loads() -> None:
    package = load_story_package(PACKAGE)

    assert package.story_id == "continuity_initiative"


def test_loader_rejects_required_reveal_with_unproducible_scene_prerequisite(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    source = root / "knowledge.yaml"
    catalog = yaml.safe_load(source.read_text(encoding="utf-8"))
    item = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_2c_c_r1")
    item["requires"].append({"fact_id": "michelle_resistance_known", "equals": True})
    source.write_text(yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(
        StoryPackageError,
        match=re.escape(
            "scene 2C reveal 'k_sl_2c_c_r1' requires 'michelle_resistance_known', which scene entry does not "
            "guarantee and the scene cannot produce"
        ),
    ):
        load_story_package(root)


def test_loader_accepts_required_reveal_with_scene_producer(tmp_path: Path) -> None:
    root = copied_package(tmp_path)
    update_knowledge(
        root,
        "k_sl_2c_c_r1",
        [
            {"fact_id": "purge_clock_started", "equals": True},
            {"fact_id": "janus_evidence", "equals": True},
            {"fact_id": "rebecca_offer_active", "equals": True},
        ],
    )

    package = load_story_package(root)

    assert package.knowledge_indexes.by_id["k_sl_2c_c_r1"].requires[-1].fact_id == "rebecca_offer_active"


def test_efficient_player_earns_2c_evidence_without_cue_or_deadline() -> None:
    package = legacy_package(LOADED_PACKAGE, {"k_sl_1a_a_r1"})
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)
    bridges = {event.scene_id: event for event in package.storylet_routes.bridge_events}
    by_id = package.knowledge_indexes.by_id
    required = required_storylet_ids(package)
    scene_picks: list[str | None] = []
    cues: list[str] = []
    deadline = False

    max_turns = sum(item.handoff_after_turns for item in package.pacing.scenes)
    for turn_index in range(1, max_turns + 1):
        scene = state.current_scene_id
        engine._activate_pacing()
        known = frozenset(f.predicate for f in state.facts.asserted if str(f.value).lower() == "true")
        bridge = bridges.get(scene)
        needed = set(bridge.activation.minimal_undelivered_facts(known)) if bridge else set()
        best: str | None = None
        best_score = (0, 0)
        for candidate in engine.projector.project(state, "player", "").candidates:
            knowledge = by_id.get(candidate.id)
            if knowledge is None:
                continue
            new_facts = [
                effect.fact_id
                for effect in knowledge.establishes
                if effect.op == "assert" and effect.fact_id not in known
            ]
            score = (
                sum(fact_id in needed for fact_id in new_facts),
                int(knowledge.source.storylet_id in required and bool(new_facts)),
            )
            if score > best_score:
                best, best_score = candidate.id, score

        provider.selected = [best] if best else []
        engine.turn("Act on the strongest available lead.")
        if scene == "2C":
            scene_picks.append(best)
            if state.last_turn_delivery.cue_fact_id:
                cues.append(state.last_turn_delivery.cue_fact_id)
            deadline |= state.last_turn_delivery.handoff_staged
            if state.current_scene_id != "2C":
                break
        if turn_index == max_turns:
            pytest.fail(f"efficient player never left 2C; in {state.current_scene_id}")

    assert not cues
    assert not deadline
    assert any(pick and pick.startswith("k_sl_2c_c_") for pick in scene_picks)

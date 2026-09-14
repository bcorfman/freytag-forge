from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package import StoryPackageError, load_story_package
from storygame.story_package.obligations import required_storylet_ids

PACKAGE_ROOT = Path("data/stories/continuity-initiative")
PACKAGE = load_story_package(PACKAGE_ROOT)
PREREQUISITES = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")


def _state_3c(*, turn_index: int = 0) -> RuntimeState:
    state = RuntimeState(package=PACKAGE, current_scene_id="3C", phase="resolution")
    state._assert_scene_entry_fact("3C")
    for fact_id in PREREQUISITES:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    state.turn_index = turn_index
    return state


class _Provider:
    def __init__(self, knowledge_id: str | None = None) -> None:
        self.knowledge_id = knowledge_id

    def __call__(self, _player_input: str) -> dict[str, object]:
        selected = [self.knowledge_id] if self.knowledge_id else []
        text = "The broadcast continues across the country."
        if self.knowledge_id:
            knowledge = PACKAGE.knowledge_indexes.by_id[self.knowledge_id]
            text = knowledge.delivery_text or knowledge.statement
        return {
            "segments": [{"kind": "narration", "text": text, "grounding_ids": selected}],
            "selected_knowledge_ids": selected,
        }


def test_resolution_prerequisites_alone_commit_nothing() -> None:
    state = _state_3c()
    RuntimeEngine(state, _Provider()).turn("Watch the broadcast spread.")

    assert not any(event.id in state.fired_event_ids for event in PACKAGE.storylet_routes.resolution_events)
    assert Fact(predicate="truth_no_longer_containable", subject="story", value="true") not in state.facts.asserted


def test_showing_exposure_does_not_commit_later_resolution_events() -> None:
    state = _state_3c()
    RuntimeEngine(state, _Provider("k_sl_3c_a_r1")).turn("Keep the broadcast running.")

    assert Fact(predicate="truth_no_longer_containable", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="rebecca_captured", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="captives_reaching_surface", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="resolution_complete", subject="story", value="true") not in state.facts.asserted


def test_resolution_deadline_shows_and_commits_remaining_chain() -> None:
    handoff = next(window for window in PACKAGE.pacing.scenes if window.scene_id == "3C").handoff_after_turns
    state = _state_3c(turn_index=handoff - 1)
    result = RuntimeEngine(state, _Provider()).turn("Get everyone to the surface.")
    narration = " ".join(segment.text for segment in result.segments)

    assert Fact(predicate="resolution_complete", subject="story", value="true") in state.facts.asserted
    positions = [narration.index(event.fallback_text or "") for event in PACKAGE.storylet_routes.resolution_events]
    assert positions == sorted(positions)
    assert all(event.fallback_text in narration for event in PACKAGE.storylet_routes.resolution_events)


def test_resolution_realization_storylets_are_required() -> None:
    assert {f"SL-3C-{letter}" for letter in "ABCDE"} <= required_storylet_ids(PACKAGE)


def test_portable_archive_starts_with_rebecca() -> None:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3C")
    placement = scene.metadata.item_placements["portable_archive"]

    assert "rebecca" in placement.placement.casefold()
    assert placement.while_fact_false == "portable_archive_secured"
    assert "portable_archive" in scene.metadata.item_ids


def _copied_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(PACKAGE_ROOT, destination)
    return destination


def _edit_routes(root: Path, edit) -> None:
    source = root / "storylet-routes.yaml"
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    edit(document)
    source.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")


def test_loader_rejects_resolution_event_without_fallback_text(tmp_path: Path) -> None:
    root = _copied_package(tmp_path)

    def remove_fallback(document: dict[str, object]) -> None:
        document["canonical_resolution_events"][0].pop("fallback_text")  # type: ignore[index]

    _edit_routes(root, remove_fallback)

    with pytest.raises(StoryPackageError, match="resolution event 'resolution_exposure_holds'.*fallback_text"):
        load_story_package(root)


def test_loader_rejects_unknown_resolution_realization_storylet(tmp_path: Path) -> None:
    root = _copied_package(tmp_path)

    def add_unknown(document: dict[str, object]) -> None:
        document["canonical_resolution_events"][0]["realization_storylets"].append("SL-3C-Z")  # type: ignore[index]

    _edit_routes(root, add_unknown)

    with pytest.raises(StoryPackageError, match="resolution_exposure_holds.*unknown realization storylet"):
        load_story_package(root)


def test_loader_rejects_resolution_fact_not_guaranteed_by_scene_entry(tmp_path: Path) -> None:
    root = _copied_package(tmp_path)

    def weaken_bridge(document: dict[str, object]) -> None:
        bridge = next(item for item in document["canonical_bridge_events"] if item["scene_id"] == "3B")  # type: ignore[index]
        bridge["activation"] = {  # type: ignore[index]
            "all_facts_true": ["relay_open"],
            "any_of": [
                "human_security_control",
                "charles_abandoned_rebecca",
                "detention_locations_secured",
                "brandon_confession_available",
            ],
            "at_least": 3,
        }

    _edit_routes(root, weaken_bridge)

    with pytest.raises(StoryPackageError, match="scene 3C.*brandon_confession_available"):
        load_story_package(root)


def test_loader_accepts_resolution_entry_guarantees() -> None:
    assert PACKAGE.storylet_routes.resolution_events

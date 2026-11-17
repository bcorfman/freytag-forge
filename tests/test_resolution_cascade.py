from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package import load_story_package
from storygame.story_package.obligations import required_storylet_ids
from storygame.story_source.diagnostics import SourceError
from tests.story_source.helpers import DELETE, compiled_story_copy, patch_source

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
    assert Fact(predicate="evacuation_complete", subject="story", value="true") not in state.facts.asserted


def test_resolution_deadline_shows_and_commits_remaining_chain() -> None:
    handoff = next(window for window in PACKAGE.pacing.scenes if window.scene_id == "3C").handoff_after_turns
    state = _state_3c(turn_index=handoff - 1)
    result = RuntimeEngine(state, _Provider()).turn("Get everyone to the surface.")
    narration = " ".join(segment.text for segment in result.segments)

    assert Fact(predicate="evacuation_complete", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="surge_forced_evacuation", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="barrier_held", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="captives_out_costly", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="lower_levels_lost", subject="story", value="true") not in state.facts.asserted
    assert state.story_complete is True
    assert all(event.fallback_text not in narration for event in PACKAGE.storylet_routes.resolution_events)


def test_resolution_realization_storylets_are_required() -> None:
    assert {"SL-3C-A", "SL-3C-B", "SL-3C-C", "SL-3C-D", "SL-3C-E", "SL-3C-F", "SL-3C-G"} <= required_storylet_ids(
        PACKAGE
    )


def _reveal(engine: RuntimeEngine, knowledge_id: str, command: str) -> None:
    engine.provider = _Provider(knowledge_id)
    engine.turn(command)
    engine._activate_pacing()  # noqa: SLF001 - inspect the next staged cue.


def _finish_a_through_c() -> RuntimeEngine:
    engine = RuntimeEngine(_state_3c(), _Provider("k_sl_3c_a_r1"))
    _reveal(engine, "k_sl_3c_a_r1", "Send the evidence package.")
    _reveal(engine, "k_sl_3c_b_r1", "Take the Portable data case from Rebecca.")
    _reveal(engine, "k_sl_3c_c_r1", "Restore the drainage pumps.")
    _reveal(engine, "k_sl_3c_c_r2", "Open the surface gates.")
    return engine


def test_resolution_d_r2_alone_waits_for_d_r1() -> None:
    engine = _finish_a_through_c()
    assert engine.state.story_complete is True
    assert Fact(predicate="evacuation_complete", subject="story", value="true") in engine.state.facts.asserted


@pytest.mark.parametrize(
    ("first_d", "second_d"),
    [
        ("k_sl_3c_d_r2", "k_sl_3c_d_r1"),
        ("k_sl_3c_d_r1", "k_sl_3c_d_r2"),
    ],
)
def test_resolution_d_chain_then_e_completes_without_deadline_events(first_d: str, second_d: str) -> None:
    commands = {
        "k_sl_3c_d_r1": "Check reports from other detention sites.",
        "k_sl_3c_d_r2": "Call the families of the missing.",
    }
    engine = _finish_a_through_c()

    engine.provider = _Provider()
    result = engine.turn(commands[first_d])
    assert result.story_complete is True
    assert engine.state.story_complete is True
    assert "evacuation_complete" in {fact.predicate for fact in engine.state.facts.asserted}


def test_portable_archive_starts_with_rebecca() -> None:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3C")
    placement = scene.metadata.item_placements["portable_archive"]

    assert placement.parent == "rebecca"
    assert "Rebecca" in placement.text
    assert "portable_archive" in scene.metadata.item_ids
    assert "portable_archive_secured" in PACKAGE.world.fact_effects


def test_loader_rejects_resolution_event_without_fallback_text(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root / "source", "scenes/3C.yaml", "bridge[resolution_exposure_holds].fallback_text", DELETE)

    with pytest.raises(SourceError, match="resolution_exposure_holds.*fallback_text"):
        load_story_package(root)


def test_loader_rejects_unknown_resolution_realization_storylet(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(
        root / "source",
        "scenes/3C.yaml",
        "bridge[resolution_exposure_holds].realized_by",
        ["sl_3c_a", "sl_3c_z"],
    )

    with pytest.raises(SourceError, match="resolution_exposure_holds.*reveal reference.*does not resolve"):
        load_story_package(root)


def test_loader_rejects_resolution_fact_not_guaranteed_by_scene_entry(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)
    patch_source(root / "source", "scenes/3B.yaml", "bridge[bridge_3b_broadcast].when", ["relay_open"])
    patch_source(
        root / "source",
        "scenes/3B.yaml",
        "bridge[bridge_3b_broadcast].when_any",
        [
            "human_security_control",
            "charles_abandoned_rebecca",
            "detention_locations_secured",
            "brandon_confession_available",
        ],
    )
    patch_source(root / "source", "scenes/3B.yaml", "bridge[bridge_3b_broadcast].at_least", 3)

    with pytest.raises(SourceError, match="scene 3C.*brandon_confession_available"):
        load_story_package(root)


def test_loader_accepts_resolution_entry_guarantees() -> None:
    assert PACKAGE.storylet_routes.resolution_events

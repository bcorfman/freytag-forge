from __future__ import annotations

from pathlib import Path

from storygame.runtime.contracts import GameBreakWarning, NarrationSegment, ResolvedTurnProposal
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
PROJECTOR = KnowledgeProjector()


def _state_3a() -> RuntimeState:
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "3A"
    state.phase = next(scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "3A")
    state._assert_scene_entry_fact("3A")
    for fact_id in ("michelle_reached", "uprising_prepared"):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return state


def _ids(items: object) -> set[str]:
    return {item.id for item in items}  # type: ignore[union-attr]


def _proposal(*knowledge_ids: str, game_break: GameBreakWarning | None = None) -> ResolvedTurnProposal:
    return ResolvedTurnProposal(
        segments=(NarrationSegment(kind="narration", text="The account is spoken aloud."),),
        selected_knowledge_ids=knowledge_ids,
        game_break=game_break,
    )


def test_realization_is_sayable_only_after_narration() -> None:
    state = _state_3a()

    before = PROJECTOR.project(state, "michelle", "Ask Michelle what happened.")
    assert "k_sl_3a_a_r1" not in _ids(before.sayable_knowledge)
    assert "k_sl_3a_a_r1" in _ids(before.committed_knowledge)

    state.apply_proposal(_proposal("k_sl_3a_a_r1"))

    after = PROJECTOR.project(state, "michelle", "Ask Michelle what happened.")
    assert "k_sl_3a_a_r1" in _ids(after.sayable_knowledge)


def test_committed_knowledge_still_includes_unnarrated_established_realization() -> None:
    state = _state_3a()

    projection = PROJECTOR.project(state, "michelle", "Ask Michelle what happened.")

    assert "k_sl_3a_a_r1" in _ids(projection.committed_knowledge)
    assert "k_sl_3a_a_r1" not in _ids(projection.sayable_knowledge)


def test_narrating_one_realization_does_not_make_its_sibling_sayable() -> None:
    state = _state_3a()
    state.apply_proposal(_proposal("k_sl_3a_a_r1"))

    projection = PROJECTOR.project(state, "michelle", "Ask Michelle what happened.")
    assert "k_sl_3a_a_r1" in _ids(projection.sayable_knowledge)
    assert "k_sl_3a_a_r2" not in _ids(projection.sayable_knowledge)


def test_non_realization_sources_remain_sayable_without_narration() -> None:
    state = _state_3a()
    state.facts.assert_fact(Fact(predicate="command_levels_assault_underway", subject="story", value="true"))
    canonical = PROJECTOR.project(state, "michelle", "Look around.")
    assert "k_bridge_3a_command_assault" in _ids(canonical.sayable_knowledge)

    scene_state = RuntimeState.bootstrap(PACKAGE)
    scene_state.current_scene_id = "1B"
    scene_state.phase = next(
        scene.metadata.freytag_phase for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B"
    )
    scene_state._assert_scene_entry_fact("1B")
    scene = PROJECTOR.project(scene_state, "brandon", "Search the park.")
    assert "k_1b_stranger_evasion" in _ids(scene.sayable_knowledge)


def test_narration_fact_is_unique_and_snapshot_restores_it() -> None:
    state = _state_3a()
    snapshot = state.snapshot()
    state.apply_proposal(_proposal("k_sl_3a_a_r1"))
    state.apply_proposal(_proposal("k_sl_3a_a_r1"))
    assert state.facts.matching("knowledge_narrated", "k_sl_3a_a_r1") == (
        Fact(predicate="knowledge_narrated", subject="k_sl_3a_a_r1", value="true"),
    )

    state.restore_snapshot(snapshot)
    assert state.facts.matching("knowledge_narrated", "k_sl_3a_a_r1") == ()


def test_game_break_does_not_commit_narration_fact() -> None:
    state = _state_3a()
    state.apply_proposal(
        _proposal(
            "k_sl_3a_a_r1",
            game_break=GameBreakWarning(
                warning_id="test_break",
                reason="test",
                snapshot_id="test_snapshot",
            ),
        )
    )
    assert state.facts.matching("knowledge_narrated", "k_sl_3a_a_r1") == ()


def test_narration_fact_survives_save_load_and_gate_holds(tmp_path: Path) -> None:
    state = _state_3a()
    state.apply_proposal(_proposal("k_sl_3a_a_r1"))
    store = RuntimeStateSqliteStore(tmp_path / "state.sqlite")
    store.save("session", state)

    restored = store.load("session", PACKAGE)
    assert restored.facts.matching("knowledge_narrated", "k_sl_3a_a_r1")
    projection = PROJECTOR.project(restored, "michelle", "Ask Michelle what happened.")
    assert "k_sl_3a_a_r1" in _ids(projection.sayable_knowledge)
    assert "k_sl_3a_a_r2" not in _ids(projection.sayable_knowledge)

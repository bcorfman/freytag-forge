from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
PHOTO_ID = "michelle_photograph"
SCENES = tuple(scene.metadata.scene_id for scene in PACKAGE.scenes)


def _state(scene_id: str) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    return state


def _provider(state: RuntimeState) -> ItemFactsProvider:
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )


def _verdict(scene_id: str, text: str) -> tuple[str, str]:
    state = _state(scene_id)
    try:
        RuntimeEngine(state, lambda _: {"segments": [{"kind": "narration", "text": text}]}).turn("Look around.")
    except ProposalValidationError as error:
        return "rejected", error.code or type(error).__name__
    return "accepted", ""


def test_photo_words_are_safe_in_1a_but_the_full_name_is_not() -> None:
    assert _verdict("1A", "The phone shows a photo of the two friends.") == ("accepted", "")
    assert _verdict("1A", "A photograph is not on the screen.") == ("accepted", "")
    assert _verdict("1A", "Michelle's photograph is not on the screen.") == (
        "rejected",
        "narration_known_term_leak",
    )


def test_photo_scoped_aliases_resolve_in_1b_when_placed() -> None:
    absent = _provider(_state("1A"))
    placed_state = _state("1B")

    apply_scene_placements(PACKAGE, placed_state.facts, "1B")
    placed = _provider(placed_state)

    assert absent._resolve_name(absent._world(), "photo") is None
    assert placed._resolve_name(placed._world(), "photo") == PHOTO_ID
    assert placed._resolve_name(placed._world(), "photograph") == PHOTO_ID


@pytest.mark.parametrize(
    ("player_input", "expected_id", "storylet_id"),
    (
        ("Examine Michelle's recovered photograph.", "k_sl_1b_a_r2", "SL-1B-A"),
        ("Show Michelle's photograph to the man.", "k_sl_1b_b_r1", "SL-1B-B"),
    ),
)
def test_photo_reveals_match_their_authored_commands(player_input: str, expected_id: str, storylet_id: str) -> None:
    state = _state("1B")

    apply_scene_placements(PACKAGE, state.facts, "1B")
    state.facts.assert_fact(Fact(predicate="bench_clues_recovered", subject="story", value="true"))
    apply_world_effects(PACKAGE, state.facts)
    state.active_event_ids.add(storylet_id)
    projection = KnowledgeProjector().project(state, "player", player_input)
    handoff = uniquely_matched_authored_handoff(player_input, projection.candidates)

    assert handoff is not None
    assert handoff.candidate.id == expected_id


def test_photo_sentence_sweep_matches_the_verified_scene_verdicts() -> None:
    expected = {scene_id: ("accepted", "") for scene_id in SCENES}

    assert {scene_id: _verdict(scene_id, "Kristin looks at a photo.") for scene_id in SCENES} == expected

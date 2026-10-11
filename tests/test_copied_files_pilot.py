from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.knowledge import _input_referenced_entity_ids
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
SENTENCES = (
    "Kristin opens the JANUS files in the records archive.",
    "Kristin studies the JANUS evidence on the terminal.",
    "Kristin copies the files onto her drive and tucks the copied files away.",
    "Kristin checks the copied JANUS files.",
)
BASE_VERDICTS = {
    "1A": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "1B": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "1C": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "2A": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "2B": (
        ("accept", ""),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "2C": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "3A": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "3B": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
    "3C": (
        ("reject", "narration_known_term_leak"),
        ("reject", "narration_known_term_leak"),
        ("accept", ""),
        ("accept", ""),
    ),
}


def _state(scene_id: str, *, janus_evidence: bool = True) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    if janus_evidence:
        state.facts.assert_fact(Fact(predicate="janus_evidence", subject="story", value="true"))
    apply_scene_placements(PACKAGE, state.facts, scene_id)
    return state


def _verdict(scene_id: str, sentence: str) -> tuple[str, str]:
    state = _state(scene_id)

    def provider(_player_input: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": sentence}]}

    try:
        RuntimeEngine(state, provider).turn("Look around.")
    except ProposalValidationError as error:
        return "reject", error.code or type(error).__name__
    return "accept", ""


def _resolver(scene_id: str) -> ItemFactsProvider:
    state = _state(scene_id)
    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )


def test_base_verdicts_are_unchanged_by_the_pilot() -> None:
    current = {scene: tuple(_verdict(scene, sentence) for sentence in SENTENCES) for scene in BASE_VERDICTS}
    assert current == BASE_VERDICTS


def test_copied_files_are_placed_under_kristin_in_2c() -> None:
    assert world_for(PACKAGE, _state("2C").facts).parent("copied_janus_files") == "kristin"


def test_scoped_aliases_resolve_only_in_2c() -> None:
    placed = _resolver("2C")
    absent = _resolver("1A")
    assert placed._resolve_name(placed._world(), "copied files") == "copied_janus_files"
    assert placed._resolve_name(placed._world(), "JANUS evidence") == "copied_janus_files"
    assert absent._resolve_name(absent._world(), "copied files") is None
    assert absent._resolve_name(absent._world(), "JANUS evidence") is None


def test_recall_references_copied_files_only_when_placed() -> None:
    # The projection's referenced_entity_ids only lists entities that knowledge records
    # establish, and no 2C reveal lists this item in entity_ids, so test the recall
    # surface directly.
    def referenced(scene_id: str) -> frozenset[str]:
        state = _state(scene_id)
        return _input_referenced_entity_ids(
            PACKAGE.world,
            "Check my copied files.",
            scope_world=world_for(PACKAGE, state.facts),
            scene=next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id),
            protagonist_id=PACKAGE.world.protagonist_id,
        )

    assert "copied_janus_files" in referenced("2C")
    assert "copied_janus_files" not in referenced("1A")


@pytest.mark.parametrize(
    ("scene_id", "text", "expected"),
    [
        ("1A", "The JANUS system is active.", "protected_narration_leak"),
        ("1A", "Rebecca is in the room.", "narration_known_term_leak"),
    ],
)
def test_early_secret_terms_remain_rejected(scene_id: str, text: str, expected: str) -> None:
    state = _state(scene_id, janus_evidence=False)
    with pytest.raises(ProposalValidationError) as caught:
        RuntimeEngine(
            state,
            lambda _input: {"segments": [{"kind": "narration", "text": text}]},
        ).turn("Look around.")
    assert caught.value.code == expected


@pytest.mark.parametrize(
    "player_input",
    [
        "Check my copied JANUS files.",
        "Open the JANUS files.",
        "Review the copied files.",
        "Inspect the JANUS evidence.",
        "Read my copied JANUS files.",
    ],
)
def test_2c_copied_file_commands_match_only_the_original_reveal(player_input: str) -> None:
    candidates = tuple(
        item for item in PACKAGE.knowledge.knowledge if "2C" in item.available_in_scenes and item.action_evidence
    )
    result = uniquely_matched_authored_handoff(player_input, candidates)
    assert result is not None
    assert result.candidate.id == "k_sl_2c_c_r1"

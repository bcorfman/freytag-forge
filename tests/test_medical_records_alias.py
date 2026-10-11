from __future__ import annotations

from pathlib import Path

from storygame.runtime.facts import Fact
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.knowledge import _input_referenced_entity_ids
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_world_effects, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
SCENES = tuple(f"{phase}{letter}" for phase in range(1, 4) for letter in "ABC")
RECORDS_ID = "detention_medical_records"
SENTENCES = (
    "Kristin reads the medical records on the terminal.",
    "Kristin reviews the survivor records.",
    "Kristin studies the warning on the medical terminal and the medical records it lists.",
    "Kristin opens the detention medical records.",
    "Kristin checks the medical level.",
    "Kristin reads the experiment records.",
)
BASE = {
    "1A": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
    "1B": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
    "1C": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
    "2A": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
    "2B": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
    "2C": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
    "3A": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
        ("accepted", ""),
    ),
    "3B": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
    "3C": (
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("rejected", "narration_known_term_leak"),
        ("accepted", ""),
    ),
}


def _state(scene_id: str, *, records_placed: bool = False) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    state.facts.assert_fact(Fact(predicate="janus_evidence", subject="story", value="true"))
    if records_placed:
        state.facts.assert_fact(Fact(predicate="behavioral_experiments_known", subject="story", value="true"))
        apply_world_effects(PACKAGE, state.facts)
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


def _verdicts() -> dict[str, tuple[tuple[str, str], ...]]:
    import copy

    from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
    from storygame.runtime.knowledge import KnowledgeProjector
    from storygame.runtime.narration_safety import NarrationSafetyValidator
    from storygame.runtime.validation import ProposalValidationError

    result = {}
    for scene_id in SCENES:
        state = _state(scene_id)
        cells = []
        for sentence in SENTENCES:
            proposal = ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=sentence),))
            try:
                NarrationSafetyValidator().validate(
                    state,
                    copy.deepcopy(state),
                    proposal,
                    KnowledgeProjector(),
                    "Look around.",
                )
            except ProposalValidationError as error:
                cells.append(("rejected", error.code or type(error).__name__))
            else:
                cells.append(("accepted", ""))
        result[scene_id] = tuple(cells)
    return result


def test_scoped_alias_only_changes_the_three_alias_cells() -> None:
    actual = _verdicts()
    expected = {
        scene: tuple(
            ("accepted", "") if index in {0, 1} or (index == 2 and scene == "2B") else cell
            for index, cell in enumerate(BASE[scene])
        )
        for scene in SCENES
    }
    assert actual == expected


def test_alias_is_available_in_2b_and_2c_but_full_name_stays_guarded_in_1a() -> None:
    actual = _verdicts()
    assert actual["2B"][0] == ("accepted", "")
    assert actual["2C"][0] == ("accepted", "")
    assert actual["1A"][3] == BASE["1A"][3]


def test_resolver_only_resolves_records_after_the_revealing_fact() -> None:
    placed = _provider(_state("3A", records_placed=True))
    absent = _provider(_state("2B"))

    assert placed._resolve_name(placed._world(), "medical records") == RECORDS_ID
    assert placed._resolve_name(placed._world(), "survivor records") == RECORDS_ID
    assert absent._resolve_name(absent._world(), "medical records") is None
    assert absent._resolve_name(absent._world(), "survivor records") is None


def test_recall_only_includes_records_when_they_are_in_scope() -> None:
    placed_state = _state("3A", records_placed=True)
    placed_scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "3A")
    placed = _input_referenced_entity_ids(
        PACKAGE.world,
        "Inspect the medical records.",
        scope_world=world_for(PACKAGE, placed_state.facts),
        scene=placed_scene,
        protagonist_id=PACKAGE.world.protagonist_id,
    )
    absent_state = _state("2B")
    absent_scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2B")
    absent = _input_referenced_entity_ids(
        PACKAGE.world,
        "Inspect the medical records.",
        scope_world=world_for(PACKAGE, absent_state.facts),
        scene=absent_scene,
        protagonist_id=PACKAGE.world.protagonist_id,
    )

    assert RECORDS_ID in placed
    assert RECORDS_ID not in absent

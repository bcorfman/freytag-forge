"""Scene-scoped item vocabulary does not leak across scene boundaries."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.knowledge import KnowledgeProjector, scoped_alias_entity_ids
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


def _state(scene_id: str) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == scene_id)
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = scene_id
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact(scene_id)
    return state


def _proposal(text: str) -> ResolvedTurnProposal:
    return ResolvedTurnProposal(segments=(NarrationSegment(kind="narration", text=text),))


def test_bare_later_scene_words_do_not_reject_earlier_narration() -> None:
    state = _state("1A")

    NarrationSafetyValidator().validate(
        state,
        deepcopy(state),
        _proposal("She searches under the bench. A drain runs along the wall. The tunnel is dark."),
        KnowledgeProjector(),
        "Search underneath.",
    )


@pytest.mark.parametrize("text", ("The park bench is empty.", "The storm drain is dark."))
def test_specific_later_scene_names_are_still_guarded_earlier(text: str) -> None:
    state = _state("1A")

    with pytest.raises(ProposalValidationError) as caught:
        NarrationSafetyValidator().validate(
            state,
            deepcopy(state),
            _proposal(text),
            KnowledgeProjector(),
            "Look around.",
        )

    assert caught.value.code == "narration_known_term_leak"


def test_scene_words_still_resolve_in_their_own_scene() -> None:
    absent_state = _state("1A")
    absent_scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1A")
    absent_world = world_for(PACKAGE, absent_state.facts)

    placed_state = _state("1B")
    apply_scene_placements(PACKAGE, placed_state.facts, "1B")
    placed_scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    placed_world = world_for(PACKAGE, placed_state.facts)

    assert scoped_alias_entity_ids(
        PACKAGE.world,
        "bench",
        scene=placed_scene,
        protagonist_id=PACKAGE.world.protagonist_id,
        scope_world=placed_world,
    ) == ("park_bench",)
    assert (
        scoped_alias_entity_ids(
            PACKAGE.world,
            "bench",
            scene=absent_scene,
            protagonist_id=PACKAGE.world.protagonist_id,
            scope_world=absent_world,
        )
        == ()
    )


def test_guarded_items_have_no_bare_common_word_aliases() -> None:
    offenders: list[str] = []
    for story_root in sorted(path for path in (ROOT / "data/stories").iterdir() if path.is_dir()):
        package = load_story_package(story_root)
        offenders.extend(
            f"{item.id}: {alias}"
            for item in package.world.items
            if item.disclosure != "public"
            for alias in item.aliases
            if len(alias.split()) == 1 and alias.isalpha() and alias.islower()
        )

    assert not offenders, "non-public items have bare common-word aliases: " + ", ".join(sorted(offenders))

"""Phase 2 shadow E2E contract for progressive Scene 1A knowledge."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.contracts import FactOperation, NarrationSegment, ResolvedTurnProposal, StoryEventProposal
from storygame.runtime.engine import SCENE_ENTRY_REQUEST, RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import Audience
from tests._legacy_package import legacy_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _ids(items: object) -> set[str]:
    return {item.id for item in items}  # type: ignore[union-attr]


def test_michelles_encrypted_message_terms_no_longer_collide_with_ordinary_phone_talk() -> None:
    term_to_knowledge = PACKAGE.knowledge_indexes.term_to_knowledge

    assert (
        not {
            "michelle's message",
            "her message",
            "message from michelle",
            "michelle's note",
        }
        & term_to_knowledge.keys()
    )
    assert set(term_to_knowledge.get("michelle's encrypted message", ())) == {"k_sl_2c_d_r1"}
    assert set(term_to_knowledge.get("her encrypted message", ())) == set()
    assert set(term_to_knowledge.get("encrypted message from michelle", ())) == {"k_sl_2c_d_r1"}
    assert set(term_to_knowledge.get("michelle's encrypted note", ())) == set()
    assert set(term_to_knowledge.get("coded message", ())) == {"k_sl_2c_d_r1", "k_sl_2c_d_r2"}


@pytest.mark.parametrize(
    ("audience", "kind", "player_visible", "expected"),
    [
        ("player", "public", True, True),
        ("michelle", "characters", False, True),
        ("player", "characters", False, False),
        ("player", "world_only", False, False),
    ],
)
def test_audience_visibility_matrix(audience: str, kind: str, player_visible: bool, expected: bool) -> None:
    scoped_audience = Audience(
        kind=kind,
        character_ids=("michelle",) if kind == "characters" else (),
        player_visible=player_visible,
    )
    item = PACKAGE.knowledge.knowledge[0].model_copy(update={"audience": scoped_audience})

    assert KnowledgeProjector._visible_to(item, audience) is expected


def test_scene_1a_shadow_timeline_is_fact_backed_and_causal() -> None:
    """Temporary deterministic E2E fixture retained through every redesign phase."""

    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    projector = KnowledgeProjector(max_candidates=8)

    opening = projector.project(state, "player", "Inspect Michelle's phone.")
    assert "k_sl_1a_b_r2" not in _ids(opening.committed_knowledge)
    assert "k_sl_1a_b_r2" not in _ids(opening.candidates)
    assert all("patrol" not in item.id for item in opening.committed_knowledge)

    # Shadow eligibility starts only after the package's route has activated;
    # the warning is still a candidate, never a committed discovery.
    state.active_event_ids.update({"SL-1A-A", "SL-1A-B"})
    recording = projector.project(state, "player", "Play the damaged recording on Michelle's memory card.")
    assert "k_sl_1a_b_r2" in _ids(recording.candidates)
    assert "k_sl_1a_b_r2" not in _ids(recording.committed_knowledge)
    assert recording.payload_size() < 8_192

    warning = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r2"]
    state.apply_proposal(
        ResolvedTurnProposal(
            segments=(
                NarrationSegment(
                    kind="narration", text="The damaged recording begins with Michelle's breath catching."
                ),
            ),
            events=(
                StoryEventProposal(
                    event_id="SL-1A-B",
                    realization_id="SL-1A-B-R2",
                    operations=tuple(
                        FactOperation(
                            operation=effect.op,
                            fact=Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower()),
                        )
                        for effect in warning.establishes
                    ),
                ),
            ),
        )
    )
    after_recording = projector.project(state, "player", "Replay the recording.")
    assert "k_sl_1a_b_r2" in _ids(after_recording.committed_knowledge)
    assert not {"k_sl_1a_b_r1", "k_sl_1a_b_r2"} & _ids(after_recording.candidates)

    # A patrol route cannot supply its tape/pressure knowledge until the patrol
    # route itself is active and its exact effects have been committed.
    assert not {"k_sl_1a_c_r1", "k_sl_1a_c_r2"} & _ids(recording.candidates)
    state.active_event_ids.add("SL-1A-C")
    patrol = projector.project(state, "player", "Check the gate after the patrol searched the house.")
    assert {"k_sl_1a_c_r1", "k_sl_1a_c_r2"} <= _ids(patrol.candidates)


def test_scene_1a_route_windows_preserve_the_recording_timeline() -> None:
    package = legacy_package(PACKAGE, {"k_sl_1a_a_r1", "k_sl_1a_c_r1"}, strip_must_convey=True)
    state = RuntimeState.bootstrap(package)
    responses = iter(
        (
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": "Forced entry leaves a concrete contradiction.",
                        "grounding_ids": ["k_sl_1a_a_r1"],
                    }
                ],
                "selected_knowledge_ids": ["k_sl_1a_a_r1"],
            },
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": "A memory card is taped beneath the KMS drawer. Michelle left it there.",
                        "grounding_ids": ["k_sl_1a_b_r0"],
                    }
                ],
                "selected_knowledge_ids": ["k_sl_1a_b_r0"],
            },
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": (
                            "The card holds Michelle's saved files and a damaged recording. The recording warns, "
                            '"Do not trust the emergency broadcasts." The files name the Continuity Initiative and '
                            "point to a dead drop at a bench in the park."
                        ),
                        "grounding_ids": ["k_sl_1a_b_r1"],
                    }
                ],
                "selected_knowledge_ids": ["k_sl_1a_b_r1"],
            },
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": "The patrol approaches the gate.",
                    }
                ],
            },
        )
    )
    engine = RuntimeEngine(state, lambda _: next(responses))

    expected_candidates = (
        {"k_sl_1a_a_r1"},
        {"k_sl_1a_b_r0"},
        {"k_sl_1a_b_r1", "k_sl_1a_b_r2"},
        {"k_sl_1a_c_r1", "k_sl_1a_c_r2"},
    )
    for player_input, expected in zip(
        (
            "Inspect the back door.",
            "Look beneath the KMS drawer.",
            "Read the files on Michelle's memory card.",
            "Check the gate.",
        ),
        expected_candidates,
        strict=True,
    ):
        engine._activate_pacing()
        assert _ids(engine.projector.project(state, "player", player_input).candidates) == expected
        engine.turn(player_input)


def test_turn_rejection_has_a_stable_registered_code() -> None:
    payload = {
        "segments": [{"kind": "narration", "text": "A quiet detail.", "grounding_ids": ["k_invented_source"]}],
        "selected_knowledge_ids": [],
    }

    def provider(text: str) -> dict[str, object]:
        return (
            {"segments": [{"kind": "narration", "text": "A quiet house."}]} if text == SCENE_ENTRY_REQUEST else payload
        )

    def reject() -> ProposalValidationError:
        state = RuntimeState.bootstrap(PACKAGE)
        engine = RuntimeEngine(state, provider)
        engine.opening()
        with pytest.raises(ProposalValidationError) as caught:
            engine.turn("Search the drawer.")
        return caught.value

    first = reject()
    second = reject()
    assert str(first) == "segment grounding is not committed or selected knowledge"
    assert first.code == "invalid_grounding_reference"
    assert second.code == first.code


def test_projection_is_stable_across_turn_recording_and_save_load(tmp_path: Path) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(
        state,
        lambda _: {"segments": [{"kind": "narration", "text": "Dust shifts beneath the desk as she searches."}]},
    )

    engine.turn("Search the desk.")
    assert state.turn_records[0].id == "turn_1"
    assert engine.last_projection is not None

    store = RuntimeStateSqliteStore(tmp_path / "shadow.sqlite")
    store.save("shadow", state)
    restored = store.load("shadow", PACKAGE)
    projector = KnowledgeProjector()
    assert projector.project(restored, "player", "Search the desk.") == projector.project(
        state, "player", "Search the desk."
    )


def test_future_or_ambiguous_input_does_not_expand_shadow_context() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    projector = KnowledgeProjector()

    ordinary = projector.project(state, "player", "Search the desk.")
    future_named = projector.project(state, "player", "Call Brandon about JANUS and the facility.")

    assert future_named.referenced_entity_ids == ()
    assert _ids(future_named.candidates) == _ids(ordinary.candidates)
    assert "JANUS" not in future_named.model_dump_json()


def test_committed_projection_stays_bounded_as_the_story_accumulates() -> None:
    """A whole playthrough of committed knowledge must still fit one narration turn.

    Unbounded growth made every later turn slower than the last until the Worker
    call timed out and the player lost the turn in Act 3.
    """

    package = load_story_package(Path("data/stories/continuity-initiative"))
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3C"
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "3C")
    for fact_id in sorted(package.world.facts):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    projector = KnowledgeProjector()
    projection = projector.project(state, "player", "Act.")

    scene_local = [item for item in package.knowledge.knowledge if "3C" in item.available_in_scenes]
    assert len(projection.committed_knowledge) == min(projector.max_committed_knowledge, len(scene_local))
    assert projection.payload_size() < 8000, "a late-game turn must not approach the narration timeout"

    # The current scene keeps its grounding; distant history is what gives way.
    by_id = {item.id: item for item in package.knowledge.knowledge}
    kept_scene_local = [
        item.id for item in projection.committed_knowledge if "3C" in by_id[item.id].available_in_scenes
    ]
    all_scene_local = [
        item.id
        for item in package.knowledge.knowledge
        if "3C" in item.available_in_scenes and item.id in {k.id for k in projection.committed_knowledge}
    ]
    assert kept_scene_local == all_scene_local, "every established Scene 3C unit must survive the bound"

    # Bounding must stay deterministic so a reloaded session projects identically.
    assert projector.project(state, "player", "Act.").committed_knowledge == projection.committed_knowledge


def _establish(state: RuntimeState, knowledge_id: str) -> None:
    for effect in PACKAGE.knowledge_indexes.by_id[knowledge_id].establishes:
        value = str(effect.value).lower() if isinstance(effect.value, bool) else str(effect.value)
        state.facts.assert_fact(Fact(predicate=effect.fact_id, subject="story", value=value))


def test_knowledge_outside_the_scene_arrives_only_when_the_player_reaches_for_it() -> None:
    """World knowledge stays in scope, but silence about it costs nothing.

    Everything the current scene's beats describe is always projected. Anything
    else is retrieved only when the player's own words name it, so an earlier
    scene nobody mentions never reaches the narrator, and a player who does
    remember it gets continuity instead of a blank.
    """

    recalled_id = "k_bridge_1b_departure"
    state = RuntimeState.bootstrap(PACKAGE)
    _establish(state, recalled_id)
    projector = KnowledgeProjector()

    assert "1A" not in PACKAGE.knowledge_indexes.by_id[recalled_id].available_in_scenes

    unmentioned = projector.project(state, "player", "Search the kitchen for signs of a struggle.")
    assert recalled_id not in _ids(unmentioned.committed_knowledge)

    mentioned = projector.project(state, "player", "Examine Brandon's transit token.")
    assert recalled_id in _ids(mentioned.committed_knowledge)

    # The scene's own material is unconditional either way.
    scene_local = {
        item.id
        for item in PACKAGE.knowledge.knowledge
        if "1A" in item.available_in_scenes and item.id in _ids(unmentioned.committed_knowledge)
    }
    assert scene_local <= _ids(mentioned.committed_knowledge)


def test_incidental_words_do_not_recall_knowledge_aliases() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    _establish(state, "k_scene_1b_entry")
    _establish(state, "k_scene_2b_entry")
    projector = KnowledgeProjector()

    for player_input in (
        "Park beside the curb.",
        "Photograph the evidence.",
        "Record the pursuit.",
    ):
        projection = projector.project(state, "player", player_input)
        assert "k_scene_1b_entry" not in _ids(projection.committed_knowledge)
        assert "k_scene_2b_entry" not in _ids(projection.committed_knowledge)


def test_entity_references_use_whole_words_and_authored_aliases() -> None:
    from storygame.runtime.knowledge import _input_referenced_entity_ids

    world = PACKAGE.world
    assert "michelle" in _input_referenced_entity_ids(world, "Call Shelly again.")
    assert "memory_card" in _input_referenced_entity_ids(world, "Turn the memory card over in my hand.")
    assert "memory_card" in _input_referenced_entity_ids(world, "Check Shelly's memory card.")
    assert "mcgehee_home" not in _input_referenced_entity_ids(world, "Inspect Shelly's housework.")
    assert _input_referenced_entity_ids(world, "Inspect the blank wall.") == frozenset()

"""Phase 2 shadow E2E contract for progressive Scene 1A knowledge."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.contracts import FactOperation, StoryEventProposal, TurnProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import Audience

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _ids(items: object) -> set[str]:
    return {item.id for item in items}  # type: ignore[union-attr]


@pytest.mark.parametrize(
    ("audience", "kind", "player_visible", "expected"),
    [
        ("player", "public", True, True),
        ("sarah", "characters", False, True),
        ("player", "characters", False, False),
        ("player", "world_only", False, False),
    ],
)
def test_audience_visibility_matrix(audience: str, kind: str, player_visible: bool, expected: bool) -> None:
    scoped_audience = Audience(
        kind=kind,
        character_ids=("sarah",) if kind == "characters" else (),
        player_visible=player_visible,
    )
    item = PACKAGE.knowledge.knowledge[0].model_copy(update={"audience": scoped_audience})

    assert KnowledgeProjector._visible_to(item, audience) is expected


def test_scene_1a_shadow_timeline_is_fact_backed_and_causal() -> None:
    """Temporary deterministic E2E fixture retained through every redesign phase."""

    state = RuntimeState.bootstrap(PACKAGE)
    projector = KnowledgeProjector(max_candidates=8)

    opening = projector.project(state, "player", "I inspect Sarah's phone.")
    assert "k_sl_1a_b_r2" not in _ids(opening.committed_knowledge)
    assert "k_sl_1a_b_r2" not in _ids(opening.candidates)
    assert all("patrol" not in item.id for item in opening.committed_knowledge)

    # Shadow eligibility starts only after the package's route has activated;
    # the warning is still a candidate, never a committed discovery.
    state.active_event_ids.update({"SL-1A-A", "SL-1A-B"})
    recording = projector.project(state, "player", "I search the desk drawer for Sarah's damaged recording.")
    assert "k_sl_1a_b_r2" in _ids(recording.candidates)
    assert "k_sl_1a_b_r2" not in _ids(recording.committed_knowledge)
    assert recording.payload_size() < 8_192
    assert "Sarah" not in str(recording.observability())

    warning = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r2"]
    state.apply_proposal(
        TurnProposal(
            narration="The damaged recording begins with Sarah's breath catching.",
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
    assert "k_sl_1a_b_r2" in _ids(projector.project(state, "player", "I replay the recording.").committed_knowledge)

    # A patrol route cannot supply its tape/pressure knowledge until the patrol
    # route itself is active and its exact effects have been committed.
    assert not {"k_sl_1a_c_r1", "k_sl_1a_c_r2"} & _ids(recording.candidates)
    state.active_event_ids.add("SL-1A-C")
    patrol = projector.project(state, "player", "I check the gate after the patrol searched the house.")
    assert {"k_sl_1a_c_r1", "k_sl_1a_c_r2"} <= _ids(patrol.candidates)


def test_shadow_projection_is_stable_across_turn_recording_and_save_load(tmp_path: Path) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _: {"narration": "Dust shifts beneath the desk as I search."})

    engine.turn("I search the desk.")
    assert state.narrative_history == []
    assert state.turn_records[0].id == "turn_1"
    assert engine.last_shadow_projection is not None

    store = RuntimeStateSqliteStore(tmp_path / "shadow.sqlite")
    store.save("shadow", state)
    restored = store.load("shadow", PACKAGE)
    projector = KnowledgeProjector()
    assert projector.project(restored, "player", "I wait.") == projector.project(state, "player", "I wait.")


def test_future_or_ambiguous_input_and_raw_history_do_not_expand_shadow_context() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.narrative_history.append("JANUS and Gabriel were already revealed in an old transcript.")
    state.active_event_ids.add("SL-1A-B")
    projector = KnowledgeProjector()

    ordinary = projector.project(state, "player", "I search the desk.")
    future_named = projector.project(state, "player", "I call Gabriel about JANUS and the facility.")

    assert future_named.referenced_entity_ids == ()
    assert _ids(future_named.candidates) == _ids(ordinary.candidates)
    assert "JANUS" not in future_named.model_dump_json()

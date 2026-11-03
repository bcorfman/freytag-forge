"""The four offered candidates: a candidate whose action evidence matches the command ranks first.

Optional ambient reveals rank below story-critical ones (priority -1), so without this rule a crowded scene could
starve the very reveal the player just asked for.
"""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
GENERIC = "Act on the strongest available lead."


def _state_1b(*true_facts: str) -> RuntimeState:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "1B")
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1B"
    state.phase = scene.metadata.freytag_phase
    state._assert_scene_entry_fact("1B")
    apply_scene_placements(PACKAGE, state.facts, "1B")
    for fact_id in true_facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return state


def _engine(state: RuntimeState) -> RuntimeEngine:
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Kristin looks."}]})
    engine._activate_pacing()
    return engine


def _ids(state: RuntimeState, command: str) -> list[str]:
    engine = _engine(state)
    return [candidate.id for candidate in engine.projector.project(state, "player", command).candidates]


def test_the_reveal_the_command_earns_is_offered_first():
    state = _state_1b("missing_may_be_alive")
    assert _ids(state, "Examine the thermos.")[0] == "k_sl_1b_h_r1"
    assert _ids(_state_1b(), "Watch the stranger.")[0] == "k_sl_1b_g_r1"
    assert _ids(_state_1b(), "Look at the picnic blanket.")[0] == "k_sl_1b_f_r1"


def test_a_command_that_earns_nothing_keeps_the_old_order():
    state = _state_1b()
    _engine(state)
    eligible = [
        item
        for knowledge_id in PACKAGE.knowledge_indexes.scene_to_candidates["1B"]
        if explain_reveal(state, "player", (item := PACKAGE.knowledge_indexes.by_id[knowledge_id])).eligible
    ]
    expected = [item.id for item in sorted(eligible, key=lambda item: (-item.relevance.priority, item.id))][:4]
    assert expected and _ids(state, GENERIC) == expected


def test_the_offer_stays_four_long_and_keeps_the_bench_reveal_for_a_bench_command():
    ids = _ids(_state_1b(), "Look under the park bench.")
    assert len(ids) <= 4 and ids[0] == "k_sl_1b_d_r1"

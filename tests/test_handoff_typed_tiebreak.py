from __future__ import annotations

from pathlib import Path

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import RevealCandidate
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
TYPED = "Ask the senior official about the gate codes."
# The engine appends the display names the player's nouns resolved to ("gate codes" becomes "emergency override
# codes"). Those words belong to the world, not to the player's sentence.
WITH_NAMES = f"{TYPED} emergency surface gates emergency override codes"


def _candidate(candidate_id: str, *groups: tuple[str, ...]) -> RevealCandidate:
    return RevealCandidate(
        id=candidate_id,
        statement=f"{candidate_id} statement",
        must_convey=(),
        action_evidence=groups,
        delivery_text=f"{candidate_id} text",
    )


ASK = _candidate("ask", ("ask", "talk"), ("senior official", "gate codes"))
USE = _candidate("use", ("use", "override"), ("emergency override codes",))


def test_a_match_that_needs_appended_names_for_its_verb_yields_to_one_the_player_typed():
    assert uniquely_matched_authored_handoff(WITH_NAMES, (ASK, USE)) is None
    handoff = uniquely_matched_authored_handoff(WITH_NAMES, (ASK, USE), typed_input=TYPED)
    assert handoff is not None and handoff.candidate.id == "ask" and handoff.source == "exact"


def test_without_a_typed_input_the_old_behavior_is_unchanged():
    assert uniquely_matched_authored_handoff(WITH_NAMES, (ASK, USE), typed_input=None) is None
    handoff = uniquely_matched_authored_handoff(TYPED, (ASK,), typed_input=TYPED)
    assert handoff is not None and handoff.candidate.id == "ask"


def test_a_genuine_tie_on_the_typed_words_still_delivers_nothing():
    twin = _candidate("twin", ("ask",), ("gate codes",))
    assert uniquely_matched_authored_handoff(TYPED, (ASK, twin), typed_input=TYPED) is None
    assert uniquely_matched_authored_handoff(WITH_NAMES, (ASK, twin), typed_input=TYPED) is None


def test_when_no_tied_match_fits_the_typed_words_the_tie_stands():
    only_names_a = _candidate("names_a", ("use", "override"), ("emergency override codes",))
    only_names_b = _candidate("names_b", ("activate", "override"), ("emergency surface gates",))
    assert uniquely_matched_authored_handoff(WITH_NAMES, (only_names_a, only_names_b), typed_input=TYPED) is None


def test_the_framed_official_hands_off_with_the_names_the_engine_appends():
    package = load_story_package(ROOT)
    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "3A"
    state.phase = next(s for s in package.scenes if s.metadata.scene_id == "3A").metadata.freytag_phase
    state._assert_scene_entry_fact("3A")
    state.turn_index = 5
    apply_scene_placements(package, state.facts, "3A")
    for fact_id in ("michelle_reached", "uprising_prepared", "behavioral_experiments_known"):
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    RuntimeEngine(state, lambda _command: {"segments": []})._activate_pacing()
    provider = CloudflareTurnProvider(worker_url="", token="", state=state)
    provider.assemble_turn_prompt(TYPED)
    assert provider.authored_handoff is not None
    assert provider.authored_handoff.candidate.id == "k_sl_3a_d_r1"

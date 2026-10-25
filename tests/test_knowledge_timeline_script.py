"""Check the scripted Scene 1A knowledge timeline without network or model calls.

The committed prefix and deliberate rejection are replayed through the real
engine and ``ScriptedTurnProvider``.  The provider indexes entries by the
persisted turn, and rejected turns restore that index, so the script ends at
the deliberate rejection.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.scripted_provider import ScriptedTurnProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_PATH = ROOT / "deployment/knowledge-timeline-script.json"
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"

# Keep these in sync with the @knowledge-timeline test in scene-runtime.spec.js.
PLAYER_INPUTS = (
    "Search the back door and room for signs of Michelle's disappearance.",
    "Examine Michelle's phone for useful evidence.",
    "Search under the drawer in her workstation.",
    "Check the front gate for an arriving patrol.",
    "Reassess the house evidence for a concrete local consequence.",
    "Probe the future lead for a response.",
)


def test_knowledge_timeline_script_replays_eligible_prefix_and_rejects_future_selection() -> None:
    """Replay the reachable prefix, then prove the rejected script contract."""

    script = json.loads(SCRIPT_PATH.read_text())
    package = load_story_package(PACKAGE_ROOT)
    state = RuntimeState.bootstrap(package)
    provider = ScriptedTurnProvider(state, str(SCRIPT_PATH))
    engine = RuntimeEngine(state, provider)
    engine.opening()

    committed_turns = script["turns"][:5]
    assert len(committed_turns) == len(PLAYER_INPUTS) - 1
    for player_input in PLAYER_INPUTS[:5]:
        engine.turn(player_input)

    before_rejection = state.snapshot()
    with pytest.raises(ProposalValidationError) as raised:
        engine.turn(PLAYER_INPUTS[5])

    assert raised.value.code == "ineligible_selection"
    assert state.turn_index == before_rejection.turn_index
    assert state.facts == before_rejection.facts
    assert state.current_scene_id == before_rejection.current_scene_id

    selected_ids = [item_id for turn in script["turns"] for item_id in turn.get("selected_knowledge_ids", [])]
    assert selected_ids == ["k_sl_1a_b_r0", "k_future_invalid"]
    assert "k_future_invalid" not in package.knowledge_indexes.by_id
    established: set[str] = set()
    for item_id in selected_ids:
        if item_id == "k_future_invalid":
            continue
        item = package.knowledge_indexes.by_id[item_id]
        for predicate in item.requires:
            if predicate.equals is True:
                assert predicate.fact_id in established
            else:
                assert predicate.fact_id not in established
        established.update(effect.fact_id for effect in item.establishes if effect.op == "assert")

"""Deadline handoffs license the authored fallback narration they insert."""

from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import NarrationSegment, ResolvedTurnProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import FactDelivery

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = json.dumps(payload).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.payload


def test_scene_1a_deadline_fallback_is_accepted_and_exits_scene(monkeypatch) -> None:
    monkeypatch.setattr(
        "storygame.runtime.cloudflare.urlopen",
        lambda *_args, **_kwargs: _Response(
            {"narration": json.dumps({"segments": [{"kind": "narration", "text": "The house is quiet."}]})}
        ),
    )
    state = RuntimeState.bootstrap(PACKAGE)
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)
    engine = RuntimeEngine(state, provider)
    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "1A")

    for player_input in (
        "Search the kitchen.",
        "Check the back door.",
        "Look at the overturned chair.",
        "Look around the living room.",
        "Check the front window.",
    ):
        engine.turn(player_input)
    for _ in range(window.handoff_after_turns - 5):
        engine.turn("Search the room for a way forward.")

    assert state.current_scene_id == "1B"
    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="memory_card_recovered", subject="story", value="true") in state.facts.asserted


def test_card_is_still_unavailable_before_a_staged_handoff() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(
        state,
        lambda _input: {"segments": [{"kind": "narration", "text": "Kristin picks up the card."}]},
    )

    with pytest.raises(ProposalValidationError) as caught:
        engine.turn("Search the kitchen.")

    assert caught.value.code == "narration_known_term_leak"
    assert "unavailable knowledge" in str(caught.value)


def test_staged_fallback_text_licenses_only_terms_it_contains() -> None:
    delivery = FactDelivery(
        fact_id="synthetic_handoff",
        scene_id="1A",
        source_kind="observation",
        must_convey=(("the card",), ("Continuity Initiative",)),
        fallback_text="The card arrives in Kristin's hands.",
    )
    package = PACKAGE.model_copy(update={"deliveries": (*PACKAGE.deliveries, delivery)})
    state = RuntimeState.bootstrap(package)
    state.staged_handoff_fact_ids = ("synthetic_handoff",)
    candidate_state = deepcopy(state)
    proposal = ResolvedTurnProposal(
        segments=(
            NarrationSegment(
                kind="narration",
                text="The card arrives in Kristin's hands. The emergency broadcasts continue.",
            ),
        )
    )

    with pytest.raises(ProposalValidationError) as caught:
        NarrationSafetyValidator().validate(
            state, candidate_state, proposal, KnowledgeProjector(), "Search the kitchen."
        )

    assert caught.value.code == "narration_known_term_leak"
    assert "emergency broadcasts" in str(caught.value)

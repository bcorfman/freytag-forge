"""Narrator embellishments: typed reply field, pre-commit check, post-capture commit, opening (richer-narration 2c)."""

from __future__ import annotations

import copy
import tempfile
from pathlib import Path

import pytest
from worldkeeper import EmbellishResult, World

from storygame.runtime.capture import WorldCapture
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import OPENING_ATTEMPTS, TURN_NARRATION_ATTEMPTS, RuntimeEngine
from storygame.runtime.item_facts import _MATCH_SYSTEM, ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProposalValidationError
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package
from tests.test_incidental_package import LIGHTHOUSE, lighthouse

CUP = {
    "props": [{"template": "tea cup", "parent": "bench"}],
    "traits": [{"target": "tea cup", "facet": "color", "value": "blue"}],
}
NARRATION = "Ada studies the bench."


def turn(embellishments=None, text=NARRATION):
    reply = {"segments": [{"kind": "narration", "text": text}]}
    if embellishments is not None:
        reply["embellishments"] = embellishments
    return reply


@pytest.fixture
def rig(monkeypatch, tmp_path):
    """Return a builder for (state, engine, calls) with scripted narration replies; match calls answer 'nothing'."""

    def build(*replies, policy=True):
        package = load_story_package(lighthouse(Path(tempfile.mkdtemp(dir=tmp_path))) if policy else LIGHTHOUSE)
        state = RuntimeState.bootstrap(package)
        provider = ItemFactsProvider(
            worker_url="",
            token="",
            state=state,
            item_facts={},
            mode="single_call",
            seed_from_package=True,
            held_by=True,
        )
        queue, calls = list(replies), []

        def request(_provider, payload):
            if payload.get("system") == _MATCH_SYSTEM:
                return {"refers": [], "same_as": {}, "kind": {}}
            calls.append(payload)
            return copy.deepcopy(queue.pop(0))

        monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
        capture = WorldCapture(provider, lambda _state, questions: {next(iter(questions)): True})
        return state, RuntimeEngine(state, provider, capture=capture), calls

    return build


def counts(state):
    return world_for(state.package, state.facts).incidental_counts("1A")


def facts_of(state):
    return frozenset(state.facts.asserted)


def test_an_accepted_proposal_commits_a_prop_and_its_trait_with_the_turn(rig):
    state, engine, _ = rig(turn(CUP))
    result = engine.turn("Look at the bench.")
    world = world_for(state.package, state.facts)
    cup = world.resolve("tea cup")
    assert result.narration == NARRATION and cup is not None
    assert world.parent(cup) == "keeper_bench" and world.facets(cup) == {"color": "blue"}
    assert counts(state) == (1, 1)


@pytest.mark.parametrize("embellishments", [None, {}, {"props": [], "traits": []}])
def test_no_embellishments_changes_nothing(rig, embellishments):
    state, engine, _ = rig(turn(embellishments))
    assert engine.turn("Look at the bench.").narration == NARRATION
    assert counts(state) == (0, 0)


def test_a_refused_proposal_is_retried_and_the_clean_retry_commits(rig):
    bad = turn({"props": [{"template": "gold crown", "parent": "bench"}]}, text="Ada finds a gold crown.")
    state, engine, calls = rig(bad, turn(None, text="Ada studies the bench closely."))
    result = engine.turn("Look at the bench.")
    assert result.narration == "Ada studies the bench closely." and len(calls) == 2
    assert counts(state) == (0, 0) and world_for(state.package, state.facts).resolve("gold crown") is None


def test_a_proposal_refused_on_every_attempt_fails_closed_and_changes_nothing(rig):
    bad = turn({"props": [{"template": "gold crown", "parent": "bench"}]}, text="Ada finds a gold crown.")
    state, engine, _ = rig(*[bad] * TURN_NARRATION_ATTEMPTS)
    before, turn_index = facts_of(state), state.turn_index
    with pytest.raises(ProposalValidationError):
        engine.turn("Look at the bench.")
    assert facts_of(state) == before and state.turn_index == turn_index


@pytest.mark.parametrize(
    "malformed",
    [
        {"props": "tea cup"},
        {"props": [{"template": "tea cup"}]},
        {"props": [{"template": "tea cup", "parent": "bench", "extra": 1}]},
        {"traits": [{"target": "tea cup", "facet": "color"}]},
        {"traits": [{"target": "Tom's logbook", "facet": "color", "value": 7}]},
        {"mystery": []},
        "tea cup",
        ["tea cup"],
    ],
)
def test_malformed_embellishments_are_rejected_and_retried_not_dropped(rig, malformed):
    state, engine, calls = rig(turn(malformed), turn(None, text="Ada studies the bench closely."))
    assert engine.turn("Look at the bench.").narration == "Ada studies the bench closely."
    assert len(calls) == 2 and counts(state) == (0, 0)


def test_a_package_without_a_policy_rejects_any_embellishment(rig):
    state, engine, _ = rig(*[turn(CUP)] * TURN_NARRATION_ATTEMPTS, policy=False)
    before = facts_of(state)
    with pytest.raises(ProposalValidationError):
        engine.turn("Look at the bench.")
    assert facts_of(state) == before


def test_allowances_accumulate_across_turns_and_a_refusal_spends_nothing(rig):
    napkin = {"props": [{"template": "tea cup", "parent": "bench"}]}
    again = {"props": [{"template": "tea cup", "parent": "parlour"}]}
    state, engine, _ = rig(turn(napkin), *[turn(again)] * TURN_NARRATION_ATTEMPTS)
    engine.turn("Look at the bench.")
    assert counts(state) == (1, 1)
    before = facts_of(state)
    with pytest.raises(ProposalValidationError):
        engine.turn("Look at the bench again.")
    assert counts(state) == (1, 1) and facts_of(state) == before


def test_a_trait_on_an_authored_object_commits_from_its_palette(rig):
    reply = turn({"traits": [{"target": "Tom's logbook", "facet": "color", "value": "brown"}]})
    state, engine, _ = rig(reply)
    engine.turn("Look at the bench.")
    assert world_for(state.package, state.facts).facets("logbook") == {"color": "brown"}


def test_drift_between_check_and_commit_rolls_the_whole_turn_back(rig, monkeypatch):
    state, engine, _ = rig(turn(CUP))
    before, turn_index = facts_of(state), state.turn_index
    monkeypatch.setattr(World, "apply_embellishments", lambda self, *a, **k: EmbellishResult(False, "drifted"))
    with pytest.raises(ProposalValidationError) as caught:
        engine.turn("Look at the bench.")
    assert caught.value.code == "embellishment_diverged"
    assert facts_of(state) == before and state.turn_index == turn_index


def test_the_opening_commits_its_embellishments_as_one_turn(rig):
    state, engine, _ = rig(turn(CUP, text="Morning light fills the parlour."))
    opening = engine.opening()
    world = world_for(state.package, state.facts)
    assert any("Morning light" in segment.text for segment in opening.segments)
    assert world.facets(world.resolve("tea cup")) == {"color": "blue"}
    assert counts(state) == (1, 1)


def test_a_refused_opening_proposal_is_retried(rig):
    bad = turn({"props": [{"template": "gold crown", "parent": "bench"}]}, text="A gold crown gleams.")
    state, engine, calls = rig(bad, turn(CUP, text="Morning light fills the parlour."))
    engine.opening()
    assert len(calls) == 2 and counts(state) == (1, 1)
    assert world_for(state.package, state.facts).resolve("gold crown") is None


def test_a_refused_opening_on_every_attempt_fails_closed_and_commits_nothing(rig):
    bad = turn({"props": [{"template": "gold crown", "parent": "bench"}]}, text="A gold crown gleams.")
    state, engine, _ = rig(*[bad] * OPENING_ATTEMPTS)
    before = facts_of(state)
    with pytest.raises(ProposalValidationError):
        engine.opening()
    assert facts_of(state) == before

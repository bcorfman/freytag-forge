from copy import deepcopy
from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")


def _engine(mode: str, facts: dict[str, dict[str, str]], replies=None):
    state = RuntimeState.bootstrap(PACKAGE)
    provider_state = ItemFactsProvider(
        worker_url="", token="", state=state, item_facts={}, mode="single_call", seed_from_package=True
    )
    replies = iter(replies or [{"segments": [{"kind": "narration", "text": "The move is complete."}]}])
    calls = []

    def narrator(command):
        calls.append(command)
        provider_state._pending_item_facts = facts
        provider_state._pending_item_facts_present = True
        return next(replies)

    capture = WorldCapture(provider_state, lambda _state, questions: {next(iter(questions)): True})
    return RuntimeEngine(state, narrator, capture=capture, refusal_mode=mode), calls, state


@pytest.mark.parametrize("mode", ["off", "clause", "repair", "renarrate"])
def test_no_refusal_makes_one_provider_call(mode):
    engine, calls, _state = _engine(mode, {"Kristin's laptop": {"place": "workstation"}})

    engine.turn("Move the laptop to the workstation.")

    assert len(calls) == 1
    assert engine.refusal_extra_calls == 0


def test_off_leaves_refused_reply_unchanged():
    engine, calls, _state = _engine("off", {"drawer": {"place": "Kristin's truck"}})

    result = engine.turn("Move the drawer to the truck.")

    assert result.narration == "The move is complete."
    assert len(calls) == 1


def test_clause_appends_refusal_clause():
    engine, _calls, _state = _engine("clause", {"drawer": {"place": "Kristin's truck"}})

    result = engine.turn("Move the drawer to the truck.")

    assert result.narration.endswith("Drawer has not moved.")


@pytest.mark.parametrize("mode, expected", [("renarrate", "It stays by the wall."), ("repair", "It stays put.")])
def test_rewrite_arms_make_one_extra_call_and_keep_facts(mode, expected):
    engine, calls, state = _engine(
        mode,
        {"drawer": {"place": "Kristin's truck"}},
        [
            {"segments": [{"kind": "narration", "text": "The drawer leaves the room."}]},
            {"segments": [{"kind": "narration", "text": expected}]},
        ],
    )
    before = deepcopy({fact for fact in state.facts.asserted if fact.predicate != "story_elapsed_seconds"})

    result = engine.turn("Move the drawer to the truck.")

    assert result.narration == expected
    assert len(calls) == 2
    assert engine.refusal_extra_calls == 1
    assert {fact for fact in state.facts.asserted if fact.predicate != "story_elapsed_seconds"} == before


@pytest.mark.parametrize("mode", ["repair", "renarrate"])
def test_rewrite_arms_fall_back_to_clause_on_invalid_reply(mode):
    engine, calls, _state = _engine(
        mode,
        {"drawer": {"place": "Kristin's truck"}},
        [
            {"segments": [{"kind": "narration", "text": "The drawer leaves the room."}]},
            {"invalid": True},
        ],
    )

    result = engine.turn("Move the drawer to the truck.")

    assert result.narration.endswith("Drawer has not moved.")
    assert len(calls) == 2
    assert any("refusal re-narration failed:" in issue for issue in engine.state.last_turn_delivery.capture_issues)


def test_rewrite_falls_back_when_replacement_fails_validation():
    engine, calls, _state = _engine(
        "renarrate",
        {"drawer": {"place": "Kristin's truck"}},
        [
            {"segments": [{"kind": "narration", "text": "The drawer leaves the room."}]},
            {"segments": [{"kind": "narration", "text": "It stays put."}]},
        ],
    )
    original_validate = engine.narration_validator.validate
    calls_to_validate = 0

    def fail_second(*args, **kwargs):
        nonlocal calls_to_validate
        calls_to_validate += 1
        if calls_to_validate == 2:
            raise ValueError("test validation failure")
        return original_validate(*args, **kwargs)

    engine.narration_validator.validate = fail_second
    result = engine.turn("Move the drawer to the truck.")

    assert result.narration.endswith("Drawer has not moved.")
    assert len(calls) == 2


@pytest.mark.parametrize("mode", ["renarrate", "repair"])
def test_rewrite_splices_only_provider_segments(mode):
    engine, _calls, _state = _engine(mode, {})
    proposal = parse_turn_proposal(
        {
            "segments": [
                {"kind": "narration", "text": "The drawer leaves the room."},
                {"kind": "narration", "text": "The engine-authored complication survives."},
            ]
        }
    )
    provider_proposal = parse_turn_proposal(
        {"segments": [{"kind": "narration", "text": "The drawer leaves the room."}]}
    )
    replacement = parse_turn_proposal({"segments": [{"kind": "narration", "text": "It stays put."}]})

    result = engine._splice_refusal_segments(proposal, provider_proposal, replacement.segments)

    assert [segment.text for segment in result] == [
        "It stays put.",
        "The engine-authored complication survives.",
    ]


def test_extra_refusal_call_discards_pending_item_facts_and_restores_prompt():
    state = RuntimeState.bootstrap(PACKAGE)

    class Provider:
        last_prompt = "original prompt"
        _pending_item_facts = {"drawer": {"place": "truck"}}
        _pending_item_facts_present = True

        def discard_pending_item_facts(self):
            self._pending_item_facts = None
            self._pending_item_facts_present = False

        def __call__(self, _command):
            self.last_prompt = "refusal prompt"
            return {"segments": [{"kind": "narration", "text": "It stays put."}]}

    provider = Provider()
    engine = RuntimeEngine(state, provider, refusal_mode="renarrate")

    engine._call_refusal_provider({"user": "rewrite this"})

    assert provider._pending_item_facts is None
    assert provider._pending_item_facts_present is False
    assert provider.last_prompt == "original prompt"


def test_invalid_refusal_mode_raises():
    state = RuntimeState.bootstrap(PACKAGE)

    with pytest.raises(ValueError):
        RuntimeEngine(state, lambda _command: {}, refusal_mode="unknown")

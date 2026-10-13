from pathlib import Path

import pytest

from storygame.runtime.capture import WorldCapture
from storygame.runtime.contracts import NarrationSegment
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(ROOT / "data" / "stories" / "continuity-initiative")


def _engine(item_facts: dict[str, dict[str, str]]) -> tuple[RuntimeEngine, WorldCapture, RuntimeState]:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
    )

    def narrator(_command: str) -> dict[str, object]:
        provider._pending_item_facts = item_facts
        provider._pending_item_facts_present = True
        return {"segments": [{"kind": "narration", "text": "The move is complete."}]}

    capture = WorldCapture(provider, lambda _state, questions: {next(iter(questions)): True})
    return RuntimeEngine(state, narrator, capture=capture), capture, state


def test_refused_move_appends_deterministic_final_clause() -> None:
    engine, _capture, _state = _engine({"drawer": {"place": "Kristin's truck"}})

    result = engine.turn("Move the drawer to the truck.")

    assert result.segments[-1] == NarrationSegment(kind="narration", text="Drawer has not moved.")
    assert result.narration.endswith("Drawer has not moved.")
    assert "refusal clause added for Drawer" in engine.state.last_turn_delivery.capture_issues


def test_accepted_move_adds_no_refusal_clause() -> None:
    engine, _capture, _state = _engine({"Kristin's laptop": {"place": "workstation"}})

    result = engine.turn("Move the laptop to the workstation.")

    assert result.narration == "The move is complete."
    assert not any("has not moved" in segment.text for segment in result.segments)


def test_left_unplaced_result_adds_no_refusal_clause() -> None:
    engine, capture, _state = _engine({"Kristin's laptop": {"place": "a sealed box"}})

    result = engine.turn("Put the laptop in a sealed box.")

    assert result.narration == "The move is complete."
    assert capture.last_after["unplaced"]
    assert capture.last_after["refused"] == []


def test_multiple_refused_moves_use_have() -> None:
    engine, _capture, _state = _engine(
        {
            "drawer": {"place": "Kristin's truck"},
            "back door": {"place": "Kristin's truck"},
        }
    )

    result = engine.turn("Move the drawer and back door to the truck.")

    assert result.narration.endswith("Drawer and Back door have not moved.")


def test_refusal_clause_survives_save_load_before_follow_up() -> None:
    first, _capture, state = _engine({"Kristin's laptop": {"place": "workstation"}})
    first.turn("Move the laptop to the workstation.")

    restored = RuntimeState.bootstrap(PACKAGE)
    restored.restore_snapshot(state.snapshot())
    second, _capture, _state = _engine({"drawer": {"place": "Kristin's truck"}})
    second.state = restored
    second.validator = first.validator
    second.reveal_resolver = first.reveal_resolver
    second.capture.provider.state = restored

    result = second.turn("Move the drawer to the truck.")

    assert result.narration.endswith("Drawer has not moved.")


def test_refusal_clause_is_composed_when_a_saved_turn_resumes(monkeypatch: pytest.MonkeyPatch) -> None:
    engine, _capture, _state = _engine({"drawer": {"place": "Kristin's truck"}})
    monkeypatch.setattr(engine.validator, "validate", lambda *_args: ("brandon",))

    blocked = engine.turn("Move the drawer to the truck.")
    assert blocked.game_break is not None
    assert "has not moved" not in blocked.narration

    resumed = engine.resolve_break("proceed")

    assert resumed is not None
    assert resumed.narration.endswith("Drawer has not moved.")

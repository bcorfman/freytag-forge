from __future__ import annotations

from random import Random

from storygame.cli import run_turn
from storygame.engine.freeform import LlmFreeformProposalAdapter
from storygame.engine.world import build_default_state


class _CountingNarrator:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls = 0

    def generate(self, _context) -> str:  # noqa: ANN001
        self.calls += 1
        return self.text


def test_deterministic_affordance_uses_one_story_model_render_call(monkeypatch) -> None:
    planner_calls = 0

    def _unexpected_planner_call(*_args, **_kwargs):  # noqa: ANN002, ANN003
        nonlocal planner_calls
        planner_calls += 1
        raise AssertionError("deterministic look must not invoke the planner")

    monkeypatch.setattr("storygame.engine.freeform._story_agent_chat_complete", _unexpected_planner_call)
    narrator = _CountingNarrator("You study the committed room facts before choosing your next move.")

    state, _lines, _raw, _beat, _continued = run_turn(
        build_default_state(seed=701),
        "look",
        Random(701),
        narrator,
        freeform_adapter=LlmFreeformProposalAdapter(mode="openai"),
    )

    assert state.turn_index == 1
    assert planner_calls == 0
    assert narrator.calls == 1


def test_post_commit_narration_cannot_create_custody_or_narration_facts() -> None:
    state = build_default_state(seed=702)
    narrator = _CountingNarrator("You take the case file and carry an impossible relic.")

    next_state, _lines, _raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(702),
        narrator,
    )

    assert next_state.turn_index == 1
    assert not next_state.world_facts.holds("holding", "player", "case_file")
    assert all(event.type != "narration_commit" for event in next_state.event_log.events)


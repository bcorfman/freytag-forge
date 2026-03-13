from __future__ import annotations

import json

from storygame.engine.world import build_default_state
from storygame.llm.story_agents import DefaultNarratorOpeningAgent
from storygame.llm.story_agents import agents as agent_module


def test_narrator_opening_merges_protagonist_name_and_background_in_intro() -> None:
    state = build_default_state(seed=12, genre="mystery", tone="neutral")
    narrator = DefaultNarratorOpeningAgent("openai")
    architect = {
        "protagonist_name": "Noah Kade",
        "protagonist_background": (
            "A detective, embittered by a past failure and now living the life of a recluse "
            "in a secluded mansion, is tasked with solving one last case"
        ),
    }
    cast = {"contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}]}
    plan = {
        "assistant_name": "Daria Stone",
        "actionable_objective": "Review the case file and field kit, then choose your first lead.",
    }

    def _fake_chat_complete(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        payload = json.loads(user)
        draft = payload["opening_draft"]
        paragraphs = [segment.strip() for segment in draft.split("\n\n") if segment.strip()]
        return json.dumps({"paragraphs": paragraphs[:4]})

    original_chat_complete = agent_module._chat_complete
    agent_module._chat_complete = _fake_chat_complete
    try:
        opening = narrator.run(state, architect, cast, plan)
    finally:
        agent_module._chat_complete = original_chat_complete
    intro = opening[1].lower()

    assert "you are noah kade" in intro
    assert "detective" in intro
    assert "one last case." in intro
    assert "daria stone stays close as your assistant" in intro
    assert "their tone observant while they wait for your first instruction." in intro

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
    intro = opening[0].lower()
    relationship = opening[1].lower()

    assert "you are noah kade" in opening[0].lower()
    assert "detective" in intro
    assert "one last case." in intro
    assert "daria stone is beside you as your assistant" in relationship
    assert "daria stone's observant manner" in relationship
    assert "shared decision" in relationship
    assert "waits for your first instruction" not in relationship


def test_narrator_opening_draft_leans_on_character_pressure_over_scenery() -> None:
    state = build_default_state(seed=13, genre="mystery", tone="neutral")
    narrator = DefaultNarratorOpeningAgent("openai")
    architect = {
        "protagonist_name": "Noah Kade",
        "protagonist_background": "A detective dragged back by an old failure.",
    }
    cast = {"contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}]}
    plan = {
        "assistant_name": "Daria Stone",
        "actionable_objective": "Review the case file before anyone can control the briefing.",
    }
    observed_user: dict[str, object] = {}

    def _fake_chat_complete(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        observed_user.update(json.loads(user))
        return json.dumps({"paragraphs": ["p1", "p2", "p3"]})

    original_chat_complete = agent_module._chat_complete
    agent_module._chat_complete = _fake_chat_complete
    try:
        narrator.run(state, architect, cast, plan)
    finally:
        agent_module._chat_complete = original_chat_complete

    opening_draft = str(observed_user["opening_draft"]).lower()
    assert "can you still trust the judgment it cost you" in opening_draft
    assert "shared decision, not an order to await" in opening_draft
    assert "asks what part of the case you want to understand" in opening_draft
    assert "daria stone is beside you as your assistant" in opening_draft


def test_narrator_opening_draft_avoids_scenery_led_opening() -> None:
    state = build_default_state(seed=14, genre="mystery", tone="neutral")
    narrator = DefaultNarratorOpeningAgent("openai")
    architect = {
        "protagonist_name": "Noah Kade",
        "protagonist_background": "A detective dragged back by an old failure.",
    }
    cast = {"contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}]}
    plan = {
        "assistant_name": "Daria Stone",
        "actionable_objective": "Review the case file before anyone can control the briefing.",
    }
    observed_user: dict[str, object] = {}

    def _fake_chat_complete(mode: str, system: str, user: str) -> str:  # noqa: ARG001
        observed_user.update(json.loads(user))
        return json.dumps({"paragraphs": ["p1", "p2", "p3"]})

    original_chat_complete = agent_module._chat_complete
    agent_module._chat_complete = _fake_chat_complete
    try:
        narrator.run(state, architect, cast, plan)
    finally:
        agent_module._chat_complete = original_chat_complete

    draft_paragraphs = [part.strip().lower() for part in str(observed_user["opening_draft"]).split("\n\n") if part.strip()]
    assert draft_paragraphs
    assert draft_paragraphs[0].startswith("you are noah kade")

from __future__ import annotations

import io
import json
import logging
import urllib.error

import pytest

from storygame.engine.world import build_default_state
from storygame.llm.story_agents import agents as agent_module
from storygame.llm.story_agents.agents import (
    DefaultStoryBootstrapAgent,
    DefaultStoryBootstrapCriticAgent,
    DefaultCharacterDesignerAgent,
    DefaultNarratorOpeningAgent,
    DefaultPlotDesignerAgent,
    DefaultRoomPresentationAgent,
    DefaultStoryArchitectAgent,
    DefaultStoryReplanAgent,
    _build_identity_intro_sentence,
    _json_from_text,
    _normalize_actionable_objective_language,
    _normalize_background_clause,
    _summary_premise,
)
from storygame.llm.story_agents.contracts import StoryAgentContractError


class _FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def test_json_from_text_handles_direct_and_embedded_json() -> None:
    assert _json_from_text('{"a":1}') == {"a": 1}
    assert _json_from_text("noise\n{\"a\":1}\nnoise") == {"a": 1}
    assert _json_from_text("not json") is None


def test_summary_and_background_normalizers_cover_variants() -> None:
    state = build_default_state(seed=501)
    state.world_package["outline"] = {
        "source_text": "Situation: A detective is tasked with one last case that leads to danger.\nLine2"
    }
    assert _summary_premise(state) == "A detective is tasked with one last case"
    assert _normalize_background_clause("He is A detective, is tasked with one last case.") == (
        "a detective, tasked with one last case"
    )
    assert _build_identity_intro_sentence("Noah Kade", "") == "You are Noah Kade."
    assert _build_identity_intro_sentence("Noah Kade", "A detective.") == "You are Noah Kade, a detective."


def test_actionable_objective_normalizer_keeps_assistant_out_of_suspect_language() -> None:
    normalized = _normalize_actionable_objective_language(
        "Review the case file, then ask targeted questions about Daria Stone's involvement and question your witness.",
        "Daria Stone",
        "Victor Hale",
    )
    assert "first witness" not in normalized.lower()
    assert "question your contact" in normalized.lower()
    assert "daria stone's involvement" not in normalized.lower()
    assert "victor hale's involvement" in normalized.lower()

    fallback = _normalize_actionable_objective_language(
        "Ask direct questions about Daria Stone's involvement.",
        "Daria Stone",
        "",
    )
    assert "daria stone's involvement" not in fallback.lower()
    assert "the suspect's involvement" in fallback.lower()


def test_chat_complete_openai_and_ollama_branches(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "fake")
    captured_requests: list[dict[str, object]] = []

    def _openai_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured_requests.append(json.loads(request.data.decode("utf-8")))
        return _FakeResponse('{"choices":[{"message":{"content":"ok-openai"}}]}')

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _openai_urlopen)
    assert agent_module._chat_complete("openai", "s", "u") == "ok-openai"
    assert int(captured_requests[-1]["max_tokens"]) >= 1400

    def _ollama_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse('{"message":{"content":"ok-ollama"}}')

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _ollama_urlopen)
    assert agent_module._chat_complete("ollama", "s", "u") == "ok-ollama"

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://demo.example.workers.dev/api/narrate")

    def _cloudflare_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        return _FakeResponse('{"narration":"ok-cloudflare"}')

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _cloudflare_urlopen)
    assert agent_module._chat_complete("cloudflare", "s", "u") == "ok-cloudflare"


def test_chat_complete_ollama_normalizes_root_base_url_to_api_chat(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434")

    def _ollama_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        assert request.get_method() == "POST"
        assert request.full_url == "http://localhost:11434/api/chat"
        return _FakeResponse('{"message":{"content":"ok-ollama"}}')

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _ollama_urlopen)
    assert agent_module._chat_complete("ollama", "s", "u") == "ok-ollama"


def test_chat_complete_ollama_falls_back_to_generate_on_404(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat")
    called_urls: list[str] = []

    def _ollama_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        called_urls.append(request.full_url)
        if request.full_url.endswith("/api/chat"):
            raise urllib.error.HTTPError(
                request.full_url,
                404,
                "Not Found",
                None,
                io.BytesIO(b'{"error":"not found"}'),
            )
        return _FakeResponse('{"response":"ok-generate"}')

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _ollama_urlopen)
    assert agent_module._chat_complete("ollama", "s", "u") == "ok-generate"
    assert called_urls[:2] == ["http://localhost:11434/api/chat", "http://localhost:11434/api/generate"]


def test_chat_complete_error_paths(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        agent_module._chat_complete("openai", "s", "u")

    monkeypatch.setenv("OPENAI_API_KEY", "fake")

    def _raise_http(*args, **kwargs):  # noqa: ANN002, ANN003
        raise urllib.error.HTTPError("https://api.openai.com", 500, "boom", None, io.BytesIO(b"err"))

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _raise_http)
    with pytest.raises(RuntimeError, match="OpenAI story-agent request failed"):
        agent_module._chat_complete("openai", "s", "u")

    def _bad_ollama(*args, **kwargs):  # noqa: ANN002, ANN003
        return _FakeResponse('{"unexpected": true}')

    monkeypatch.setattr("storygame.llm.story_agents.agents.urllib.request.urlopen", _bad_ollama)
    with pytest.raises(RuntimeError, match="Ollama story-agent request failed"):
        agent_module._chat_complete("ollama", "s", "u")

    monkeypatch.delenv("CLOUDFLARE_WORKER_URL", raising=False)
    with pytest.raises(RuntimeError, match="CLOUDFLARE_WORKER_URL"):
        agent_module._chat_complete("cloudflare", "s", "u")

    with pytest.raises(ValueError, match="require mode"):
        agent_module._chat_complete("invalid", "s", "u")


def test_story_architect_agent_success_and_failures(monkeypatch) -> None:
    state = build_default_state(seed=502)
    agent = DefaultStoryArchitectAgent("openai")

    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {
                "protagonist_name": "Noah Kade",
                "protagonist_background": "A detective on one final case.",
                "secrets_to_hide": ["secret"],
                "tone": "dark",
            }
        ),
    )
    result = agent.run(state)
    assert result["protagonist_name"] == "Noah Kade"

    monkeypatch.setattr("storygame.llm.story_agents.agents._chat_complete", lambda mode, system, user: "not-json")
    with pytest.raises(RuntimeError, match="non-JSON"):
        agent.run(state)

    def _raise_contract(payload):  # noqa: ANN001
        raise StoryAgentContractError("X", "bad")

    monkeypatch.setattr("storygame.llm.story_agents.agents._chat_complete", lambda mode, system, user: "{}")
    monkeypatch.setattr("storygame.llm.story_agents.agents.parse_story_architect_output", _raise_contract)
    with pytest.raises(RuntimeError, match="contract validation failed"):
        agent.run(state)


def test_story_bootstrap_agent_success_and_failures(monkeypatch) -> None:
    state = build_default_state(seed=550)
    agent = DefaultStoryBootstrapAgent("openai")

    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {
                "protagonist_name": "Noah Kade",
                "protagonist_background": "A detective on one final case.",
                "assistant_name": "Daria Stone",
                "actionable_objective": "Review the case file and press the strongest lead.",
                "primary_goal": "Expose the conspiracy behind the murders.",
                "secondary_goals": ["Find the missing witness."],
                "expanded_outline": "Investigate the murders, expose the conspiracy, and survive retaliation.",
                "story_beats": [
                    {"beat_id": "hook", "summary": "Survey the estate.", "min_progress": 0.0},
                    {"beat_id": "midpoint", "summary": "Expose the conspiracy.", "min_progress": 0.5},
                    {"beat_id": "climax", "summary": "Confront the killer.", "min_progress": 0.85},
                ],
                "villains": [
                    {
                        "name": "Magistrate Voss",
                        "motive": "Protect the conspiracy.",
                        "means": "Paid enforcers.",
                        "opportunity": "Access to the estate.",
                    }
                ],
                "timed_events": [
                    {
                        "event_id": "warning",
                        "summary": "A servant warns that records are burning.",
                        "min_turn": 2,
                        "location": "foyer",
                        "participants": ["Daria Stone"],
                    }
                ],
                "clue_placements": [
                    {
                        "item_id": "route_key",
                        "room_id": "watch_tower",
                        "clue_text": "The route key marks the killer's exit path.",
                        "hidden_reason": "It was hidden inside a cracked stone cap.",
                    }
                ],
                "hidden_threads": ["The route key links the assistant to the mansion."],
                "reveal_schedule": [{"thread_index": 0, "min_progress": 0.55}],
                "contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}],
                "opening_paragraphs": ["p1", "p2", "p3"],
            }
        ),
    )
    result = agent.run(state)
    assert result["assistant_name"] == "Daria Stone"
    assert result["villains"][0]["name"] == "Magistrate Voss"
    assert len(result["opening_paragraphs"]) == 3

    monkeypatch.setattr("storygame.llm.story_agents.agents._chat_complete", lambda mode, system, user: "not-json")
    with pytest.raises(RuntimeError, match="non-JSON"):
        agent.run(state)


def test_story_bootstrap_critic_rejects_role_and_clue_opening_conflicts(monkeypatch) -> None:
    state = build_default_state(seed=551)
    agent = DefaultStoryBootstrapCriticAgent("openai")
    bundle = {
        "protagonist_name": "Detective Elias Wren",
        "protagonist_background": "A detective on one final case.",
        "assistant_name": "Daria Stone",
        "actionable_objective": "Question Daria Stone about her involvement and inspect the front steps.",
        "primary_goal": "Expose the conspiracy behind the murders.",
        "secondary_goals": ["Find the missing witness."],
        "expanded_outline": "Investigate the murders, expose the conspiracy, and survive retaliation.",
        "story_beats": [
            {"beat_id": "hook", "summary": "Survey the estate.", "min_progress": 0.0},
            {"beat_id": "midpoint", "summary": "Expose the conspiracy.", "min_progress": 0.5},
            {"beat_id": "climax", "summary": "Confront the killer.", "min_progress": 0.85},
        ],
        "villains": [
            {
                "name": "Magistrate Voss",
                "motive": "Protect the conspiracy.",
                "means": "Paid enforcers.",
                "opportunity": "Access to the estate.",
            }
        ],
        "timed_events": [],
        "clue_placements": [
            {
                "item_id": "ledger_page",
                "room_id": "front_steps",
                "clue_text": "The ledger page marks a missing payment.",
                "hidden_reason": "Someone tried to keep it out of the official file.",
            }
        ],
        "hidden_threads": ["The ledger page links the assistant to the mansion."],
        "reveal_schedule": [{"thread_index": 0, "min_progress": 0.55}],
        "contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}],
        "opening_paragraphs": [
            "Rain needles the stone as you reach the front steps.",
            "Daria Stone, your assistant, keeps the ledger page in hand.",
            "The ledger page is wedged into the stones in front of the mansion.",
            "You are here to question Daria Stone about her involvement before you go inside.",
        ],
    }

    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {"verdict": "accepted", "continuity_summary": "Looks fine.", "issues": []}
        ),
    )

    result = agent.run(state, bundle)

    assert result["verdict"] == "revise"
    assert any("assistant" in issue.lower() for issue in result["issues"])
    assert any("ledger page" in issue.lower() for issue in result["issues"])


def test_story_bootstrap_critic_rejects_ledger_page_left_on_front_steps(monkeypatch) -> None:
    state = build_default_state(seed=552)
    agent = DefaultStoryBootstrapCriticAgent("openai")
    bundle = {
        "assistant_name": "Daria Stone",
        "actionable_objective": "Review the grounds and decide which lead to press first.",
        "contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}],
        "clue_placements": [
            {
                "item_id": "ledger_page",
                "room_id": "front_steps",
                "clue_text": "The ledger page marks a missing payment.",
                "hidden_reason": "Wind left it half-caught in the stonework.",
            }
        ],
        "opening_paragraphs": [
            "Rain needles the stone as you approach the mansion.",
            "Daria Stone watches the drive while the ledger page lies in plain sight on the front steps.",
            "The work begins before you even cross the threshold.",
        ],
    }
    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {"verdict": "accepted", "continuity_summary": "Looks fine.", "issues": []}
        ),
    )

    result = agent.run(state, bundle)

    assert result["verdict"] == "revise"
    assert any("front steps" in issue.lower() for issue in result["issues"])


def test_character_plot_narrator_agents_success_and_error_paths(monkeypatch) -> None:
    state = build_default_state(seed=503)
    architect = {"protagonist_name": "Noah Kade", "protagonist_background": "A detective."}
    cast = {"contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}]}
    plan = {"assistant_name": "Daria Stone", "actionable_objective": "Start with the case file."}

    char_agent = DefaultCharacterDesignerAgent("openai")
    plot_agent = DefaultPlotDesignerAgent("openai")
    narr_agent = DefaultNarratorOpeningAgent("openai")
    room_agent = DefaultRoomPresentationAgent("openai")

    # Character success
    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {"contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}]}
        ),
    )
    contacts = char_agent.run(state, architect)
    seeded_name = state.world.npcs[state.world.rooms[state.player.location].npc_ids[0]].name
    assert contacts["contacts"][0]["name"] == seeded_name

    # Plot success
    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {"assistant_name": "Daria Stone", "actionable_objective": "Review the case file first."}
        ),
    )
    plot = plot_agent.run(state, architect, contacts)
    assert "case file" in plot["actionable_objective"].lower()
    assert "first witness" not in plot["actionable_objective"].lower()

    # Narrator success
    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps({"paragraphs": ["p1", "p2", "p3"]}),
    )
    opening = narr_agent.run(state, architect, cast, plan)
    assert len(opening) == 3

    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {
                "paragraphs": [
                    "Daria Stone stands close, their posture steady.",
                    "You keep the file ready.",
                    "The case begins.",
                ]
            }
        ),
    )
    opening_with_named_contact = narr_agent.run(state, architect, cast, plan)
    assert "their posture" not in opening_with_named_contact[0].lower()
    assert "daria stone's posture" in opening_with_named_contact[0].lower()

    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: "p1.\n\np2.\n\np3.",
    )
    prose_opening = narr_agent.run(state, architect, cast, plan)
    assert prose_opening == ["p1.", "p2.", "p3."]

    # Room presentation success
    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {
                "rooms": [
                    {"room_id": room_id, "long": "Detailed room copy.", "short": "Brief room copy."}
                    for room_id in state.world.rooms
                ]
            }
        ),
    )
    room_copy = room_agent.run(state, architect, cast, plan)
    assert set(room_copy.keys()) == set(state.world.rooms.keys())
    assert all("long" in entry and "short" in entry for entry in room_copy.values())

    # Narrator non-JSON failure
    monkeypatch.setattr("storygame.llm.story_agents.agents._chat_complete", lambda mode, system, user: "bad")
    with pytest.raises(RuntimeError, match="non-JSON"):
        narr_agent.run(state, architect, cast, plan)
    with pytest.raises(RuntimeError, match="non-JSON"):
        room_agent.run(state, architect, cast, plan)

    # Plot contract failure
    def _raise_plot_contract(payload):  # noqa: ANN001
        raise StoryAgentContractError("X", "bad")

    monkeypatch.setattr("storygame.llm.story_agents.agents._chat_complete", lambda mode, system, user: "{}")
    monkeypatch.setattr("storygame.llm.story_agents.agents.parse_plot_designer_output", _raise_plot_contract)
    with pytest.raises(RuntimeError, match="contract validation failed"):
        plot_agent.run(state, architect, cast)

    # Character no-contact failure
    empty_state = build_default_state(seed=504)
    for room in empty_state.world.rooms.values():
        room.npc_ids = ()
    with pytest.raises(RuntimeError, match="requires at least one NPC"):
        DefaultCharacterDesignerAgent("openai").run(empty_state, architect)


def test_narrator_opening_logs_raw_response_when_contract_validation_fails(monkeypatch, caplog) -> None:
    state = build_default_state(seed=503)
    architect = {"protagonist_name": "Noah Kade", "protagonist_background": "A detective."}
    cast = {"contacts": [{"name": "Daria Stone", "role": "assistant", "trait": "observant"}]}
    plan = {"assistant_name": "Daria Stone", "actionable_objective": "Start with the case file."}
    narr_agent = DefaultNarratorOpeningAgent("openai")

    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps({"paragraphs": ["only one"]}),
    )

    with caplog.at_level(logging.WARNING):
        with pytest.raises(RuntimeError, match="contract validation failed"):
            narr_agent.run(state, architect, cast, plan)

    assert "NarratorOpening contract validation failed with raw response" in caplog.text
    assert '{"paragraphs": ["only one"]}' in caplog.text


def test_character_designer_pins_seeded_opening_contact_as_assistant(monkeypatch) -> None:
    state = build_default_state(seed=512)
    architect = {"protagonist_name": "Noah Kade"}
    seeded_npc_id = state.world.rooms[state.player.location].npc_ids[0]
    seeded_name = state.world.npcs[seeded_npc_id].name
    alternate_name = next(npc.name for npc_id, npc in state.world.npcs.items() if npc_id != seeded_npc_id)

    monkeypatch.setattr(
        "storygame.llm.story_agents.agents._chat_complete",
        lambda mode, system, user: json.dumps(
            {
                "contacts": [
                    {"name": alternate_name, "role": "assistant", "trait": "sharp"},
                    {"name": seeded_name, "role": "contact", "trait": "observant"},
                ]
            }
        ),
    )

    contacts = DefaultCharacterDesignerAgent("openai").run(state, architect)

    assert contacts["contacts"][0]["name"] == seeded_name
    assert contacts["contacts"][0]["role"] == "assistant"


def test_story_replan_agent_branches() -> None:
    state = build_default_state(seed=505)
    agent = DefaultStoryReplanAgent("openai")

    critical = agent.run(
        state,
        {"impact_class": "critical", "reasons": ["violent_action"], "command": "punch police officer"},
    )
    assert "fallout" in critical["new_active_goal"].lower()
    assert critical["impact_class"] == "critical"

    moderate = agent.run(state, {"impact_class": "moderate", "reasons": ["noise"], "command": "break sign"})
    assert "adapt" in moderate["new_active_goal"].lower()

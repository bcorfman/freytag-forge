from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Any, Protocol

from storygame.engine.state import GameState
from storygame.llm.story_agents.contracts import (
    StoryAgentContractError,
    parse_character_designer_output,
    parse_narrator_opening_output,
    parse_plot_designer_output,
    parse_story_architect_output,
)
from storygame.llm.story_agents.prompts import (
    build_character_designer_prompt,
    build_narrator_opening_prompt,
    build_plot_designer_prompt,
    build_story_architect_prompt,
)


def _json_from_text(text: str) -> dict[str, Any] | None:
    try:
        return json.loads(text)
    except Exception:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except Exception:
        return None


def _chat_complete(mode: str, system: str, user: str) -> str:
    if mode == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            return ""
        base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        timeout = float(os.getenv("OPENAI_TIMEOUT", "10.0"))
        request = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": 0.2,
            "max_tokens": 900,
        }
        http_request = urllib.request.Request(
            base_url,
            data=json.dumps(request).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(http_request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            return str(payload["choices"][0]["message"]["content"]).strip()
        except Exception:
            return ""

    if mode == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "180.0"))
        request = {
            "model": model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 900},
        }
        http_request = urllib.request.Request(
            base_url,
            data=json.dumps(request).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(http_request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if "message" in payload and "content" in payload["message"]:
                return str(payload["message"]["content"]).strip()
            if "response" in payload:
                return str(payload["response"]).strip()
            return ""
        except Exception:
            return ""
    return ""


def _summary_premise(state: GameState) -> str:
    source_text = str(state.world_package.get("outline", {}).get("source_text", "")).strip()
    premise = source_text.splitlines()[0].strip() if source_text else ""
    if premise.lower().startswith("premise:"):
        premise = premise[len("premise:") :].strip()
    if premise.lower().startswith("situation:"):
        premise = premise[len("situation:") :].strip()
    premise = re.sub(
        r"\b(that leads|which leads|leading to|and a choice between|and must choose).*$",
        "",
        premise,
        flags=re.IGNORECASE,
    ).strip(" ,;.")
    return premise


class StoryArchitectAgent(Protocol):
    def run(self, state: GameState) -> dict[str, Any]: ...


class CharacterDesignerAgent(Protocol):
    def run(self, state: GameState, architect: dict[str, Any]) -> dict[str, Any]: ...


class PlotDesignerAgent(Protocol):
    def run(self, state: GameState, architect: dict[str, Any], cast: dict[str, Any]) -> dict[str, Any]: ...


class NarratorOpeningAgent(Protocol):
    def run(self, state: GameState, architect: dict[str, Any], cast: dict[str, Any], plan: dict[str, Any]) -> list[str]: ...


class DefaultStoryArchitectAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState) -> dict[str, Any]:
        premise = _summary_premise(state)
        protagonist = str(state.world_package.get("story_plan", {}).get("protagonist_name", "")).strip() or "The Detective"
        fallback = {
            "protagonist_name": protagonist,
            "protagonist_background": premise or "A detective with a bruised record has taken one more case.",
            "secrets_to_hide": list(state.world_package.get("story_plan", {}).get("hidden_threads", ())),
            "tone": state.story_tone,
        }
        if self._mode not in {"openai", "ollama"}:
            return fallback
        system, user = build_story_architect_prompt(premise, protagonist, state.story_genre, state.story_tone)
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            return fallback
        try:
            parsed = parse_story_architect_output(payload)
        except StoryAgentContractError:
            return fallback
        return dict(parsed)


class DefaultCharacterDesignerAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState, architect: dict[str, Any]) -> dict[str, Any]:
        contacts: list[dict[str, str]] = []
        for room in state.world.rooms.values():
            for npc_id in room.npc_ids:
                npc = state.world.npcs.get(npc_id)
                if not npc:
                    continue
                contacts.append({"name": npc.name, "role": "assistant" if not contacts else "contact", "trait": "observant"})
        if not contacts:
            contacts = [{"name": "Mina Cole", "role": "assistant", "trait": "steady"}]
        fallback = {"contacts": contacts[:3]}
        if self._mode not in {"openai", "ollama"}:
            return fallback
        system, user = build_character_designer_prompt(str(architect.get("protagonist_name", "")), contacts)
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            return fallback
        try:
            parsed = parse_character_designer_output(payload)
        except StoryAgentContractError:
            return fallback
        return {"contacts": parsed["contacts"][:3] or contacts[:3]}


class DefaultPlotDesignerAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState, architect: dict[str, Any], cast: dict[str, Any]) -> dict[str, Any]:
        goal = state.active_goal
        contacts = cast.get("contacts", [])
        assistant = contacts[0]["name"] if contacts else ""
        actionable = goal
        if goal.lower().startswith("get oriented and secure your first reliable lead"):
            actionable = "Review the case file and field kit, then choose the first person or place to investigate."
        fallback = {"assistant_name": assistant or "Assistant", "actionable_objective": actionable}
        if self._mode not in {"openai", "ollama"}:
            return fallback
        system, user = build_plot_designer_prompt(goal, fallback["assistant_name"])
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            return fallback
        try:
            parsed = parse_plot_designer_output(payload)
        except StoryAgentContractError:
            return fallback
        return dict(parsed)


class DefaultNarratorOpeningAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState, architect: dict[str, Any], cast: dict[str, Any], plan: dict[str, Any]) -> list[str]:
        room = state.world.rooms[state.player.location]
        protagonist = str(architect.get("protagonist_name", "")).strip() or "the detective"
        background = str(architect.get("protagonist_background", "")).strip()
        contacts = cast.get("contacts", [])
        assistant_name = str(plan.get("assistant_name", "")).strip()
        assistant_trait = str(contacts[0].get("trait", "")).strip() if contacts else ""
        assistant_role = str(contacts[0].get("role", "")).strip() if contacts else ""

        inventory = [item.replace("_", " ") for item in state.player.inventory]
        carry_line = "At your side you carry " + ", ".join(f"a {item}" for item in inventory[:2]) + "." if inventory else "Your hands are empty for now."
        paragraph_1 = (
            f"The air around the {room.name.lower()} bites with evening cold as damp stone keeps the day's last heat "
            "and distant traffic thins into rumor."
        )
        paragraph_2 = (
            f"You are {protagonist}. {carry_line} "
            f"{assistant_name} stays close as your {assistant_role or 'assistant'}, "
            f"their tone {assistant_trait or 'measured'} while they wait for your first instruction."
        )
        paragraph_3 = (
            f"Your history sits just behind your eyes: {background}"
            if background
            else "Your history sits just behind your eyes, unresolved but sharp enough to focus your judgment."
        )
        objective = str(plan.get("actionable_objective", state.active_goal)).strip()
        if assistant_name:
            paragraph_4 = (
                f"{assistant_name} breaks the silence. \"Your immediate objective is practical: start with the case file "
                f"and field kit. {objective}\""
            )
        else:
            paragraph_4 = f"Your immediate objective is practical and immediate: {objective}"

        opening = [paragraph_1, paragraph_2, paragraph_3, paragraph_4]
        if self._mode in {"openai", "ollama"}:
            system, user = build_narrator_opening_prompt("\n\n".join(opening))
            payload = _json_from_text(_chat_complete(self._mode, system, user))
            if payload is not None:
                try:
                    parsed = parse_narrator_opening_output(payload)
                    opening = parsed["paragraphs"][:4]
                except StoryAgentContractError:
                    pass
        return opening

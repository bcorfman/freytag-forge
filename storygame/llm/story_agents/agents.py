from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from urllib.parse import urlparse, urlunparse
from typing import Any, Protocol

from storygame.engine.state import GameState
from storygame.llm.story_agents.contracts import (
    RoomPresentationOutput,
    StoryAgentContractError,
    parse_character_designer_output,
    parse_narrator_opening_output,
    parse_plot_designer_output,
    parse_room_presentation_output,
    parse_story_architect_output,
)
from storygame.llm.story_agents.prompts import (
    build_character_designer_prompt,
    build_narrator_opening_prompt,
    build_plot_designer_prompt,
    build_room_presentation_prompt,
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
            raise RuntimeError("OPENAI_API_KEY is required for story-agent execution.")
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
        except Exception as exc:
            raise RuntimeError(f"OpenAI story-agent request failed: {exc}") from exc

    if mode == "ollama":
        base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat")
        model = os.getenv("OLLAMA_MODEL", "llama3.2")
        timeout = float(os.getenv("OLLAMA_TIMEOUT", "180.0"))
        endpoints = _resolve_ollama_endpoints(base_url)
        errors: list[str] = []

        for endpoint in endpoints:
            request = _build_ollama_request(endpoint, model, system, user)
            http_request = urllib.request.Request(
                endpoint,
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
                raise RuntimeError("Ollama story-agent response missing expected content.")
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                errors.append(f"{endpoint} -> HTTP {exc.code}: {detail}")
                if exc.code in {404, 405, 500} and endpoint != endpoints[-1]:
                    continue
                raise RuntimeError(
                    f"Ollama story-agent request failed: endpoint={endpoint} model={model} "
                    f"status={exc.code} detail={detail}"
                ) from exc
            except Exception as exc:
                errors.append(f"{endpoint} -> {type(exc).__name__}: {exc}")
                if endpoint != endpoints[-1]:
                    continue
                raise RuntimeError(f"Ollama story-agent request failed: {exc}") from exc
        raise RuntimeError(
            "Ollama story-agent request failed across endpoints. "
            f"model={model}. attempts={' | '.join(errors)}"
        )
    raise ValueError("Story agents require mode 'openai' or 'ollama'.")


def _resolve_ollama_endpoints(raw_url: str) -> tuple[str, ...]:
    parsed = urlparse(raw_url)
    if not parsed.scheme or not parsed.netloc:
        return (raw_url,)
    if parsed.path in ("", "/"):
        base = urlunparse(parsed._replace(path="", params="", query="", fragment="")).rstrip("/")
        return (f"{base}/api/chat", f"{base}/api/generate")
    if parsed.path.endswith("/api/chat"):
        base = urlunparse(parsed._replace(path=parsed.path[: -len("/api/chat")], params="", query="", fragment=""))
        return (raw_url, f"{base.rstrip('/')}/api/generate")
    if parsed.path.endswith("/api/generate"):
        base = urlunparse(
            parsed._replace(path=parsed.path[: -len("/api/generate")], params="", query="", fragment="")
        )
        return (raw_url, f"{base.rstrip('/')}/api/chat")
    return (raw_url,)


def _build_ollama_request(endpoint: str, model: str, system: str, user: str) -> dict[str, Any]:
    if endpoint.endswith("/api/generate"):
        return {
            "model": model,
            "prompt": f"{system}\n\n{user}",
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 900},
        }
    return {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 900},
    }


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


def _normalize_background_clause(background: str) -> str:
    cleaned = " ".join(background.split()).strip(" ,")
    if not cleaned:
        return ""
    cleaned = cleaned.rstrip(".!?")
    cleaned = re.sub(r"^(he|she|they)\s+(is|are)\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^you\s+are\s+", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bis tasked with\b", "tasked with", cleaned, flags=re.IGNORECASE)
    if cleaned.startswith("A "):
        cleaned = f"a{cleaned[1:]}"
    elif cleaned.startswith("An "):
        cleaned = f"an{cleaned[2:]}"
    return cleaned.strip(" ,")


def _build_identity_intro_sentence(protagonist: str, background: str) -> str:
    identity_clause = _normalize_background_clause(background)
    if not identity_clause:
        return f"You are {protagonist}."
    return f"You are {protagonist}, {identity_clause}."


def _normalize_assistant_references(paragraphs: list[str], assistant_name: str) -> list[str]:
    if not assistant_name:
        return paragraphs
    normalized: list[str] = []
    for paragraph in paragraphs:
        if assistant_name.lower() not in paragraph.lower():
            normalized.append(paragraph)
            continue
        updated = re.sub(r"\bthey are\b", f"{assistant_name} is", paragraph, flags=re.IGNORECASE)
        updated = re.sub(r"\bthey're\b", f"{assistant_name} is", updated, flags=re.IGNORECASE)
        updated = re.sub(r"\bthey have\b", f"{assistant_name} has", updated, flags=re.IGNORECASE)
        updated = re.sub(r"\bthey've\b", f"{assistant_name} has", updated, flags=re.IGNORECASE)
        updated = re.sub(r"\btheirs\b", f"{assistant_name}'s", updated, flags=re.IGNORECASE)
        updated = re.sub(r"\btheir\b", f"{assistant_name}'s", updated, flags=re.IGNORECASE)
        updated = re.sub(r"\bthem\b", assistant_name, updated, flags=re.IGNORECASE)
        updated = re.sub(r"\bthey\b", assistant_name, updated, flags=re.IGNORECASE)
        normalized.append(updated)
    return normalized


def _pick_suspect_name(contacts: list[dict[str, str]], assistant_name: str) -> str:
    for contact in contacts:
        name = str(contact.get("name", "")).strip()
        if not name:
            continue
        if assistant_name and name.lower() == assistant_name.lower():
            continue
        return name
    return ""


def _same_contact_name(left: str, right: str) -> bool:
    return " ".join(left.split()).strip().lower() == " ".join(right.split()).strip().lower()


def _pin_seeded_assistant(contacts: list[dict[str, str]], seeded_contact: dict[str, str]) -> list[dict[str, str]]:
    seeded_name = str(seeded_contact.get("name", "")).strip()
    seeded_trait = str(seeded_contact.get("trait", "")).strip() or "observant"
    if not seeded_name:
        return contacts

    matched = next((contact for contact in contacts if _same_contact_name(str(contact.get("name", "")), seeded_name)), None)
    pinned = [
        {
            "name": seeded_name,
            "role": "assistant",
            "trait": (
                str(matched.get("trait", "")).strip()
                if matched is not None and str(matched.get("trait", "")).strip()
                else seeded_trait
            ),
        }
    ]
    for contact in contacts:
        name = str(contact.get("name", "")).strip()
        if not name or _same_contact_name(name, seeded_name):
            continue
        pinned.append(
            {
                "name": name,
                "role": "contact",
                "trait": str(contact.get("trait", "")).strip() or "observant",
            }
        )
    return pinned


def _normalize_actionable_objective_language(objective: str, assistant_name: str, suspect_name: str) -> str:
    normalized = " ".join(objective.split())
    if not normalized:
        return normalized
    if assistant_name:
        normalized = re.sub(r"\bfirst witness\b", "first contact", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\bquestion your witness\b", "question your contact", normalized, flags=re.IGNORECASE)
        suspect_label = suspect_name or "the suspect"
        assistant_pattern = re.escape(assistant_name)
        normalized = re.sub(
            rf"\b{assistant_pattern}'s involvement\b",
            f"{suspect_label}'s involvement",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\binvolvement of {assistant_pattern}\b",
            f"involvement of {suspect_label}",
            normalized,
            flags=re.IGNORECASE,
        )
        normalized = re.sub(
            rf"\babout {assistant_pattern} involvement\b",
            f"about {suspect_label}'s involvement",
            normalized,
            flags=re.IGNORECASE,
        )
    return normalized


class StoryArchitectAgent(Protocol):
    def run(self, state: GameState) -> dict[str, Any]: ...


class CharacterDesignerAgent(Protocol):
    def run(self, state: GameState, architect: dict[str, Any]) -> dict[str, Any]: ...


class PlotDesignerAgent(Protocol):
    def run(self, state: GameState, architect: dict[str, Any], cast: dict[str, Any]) -> dict[str, Any]: ...


class NarratorOpeningAgent(Protocol):
    def run(
        self,
        state: GameState,
        architect: dict[str, Any],
        cast: dict[str, Any],
        plan: dict[str, Any],
    ) -> list[str]: ...


class StoryReplanAgent(Protocol):
    def run(self, state: GameState, disruption: dict[str, Any]) -> dict[str, Any]: ...


class RoomPresentationAgent(Protocol):
    def run(
        self,
        state: GameState,
        architect: dict[str, Any],
        cast: dict[str, Any],
        plan: dict[str, Any],
    ) -> dict[str, dict[str, str]]: ...


class DefaultStoryArchitectAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState) -> dict[str, Any]:
        premise = _summary_premise(state)
        protagonist = (
            str(state.world_package.get("story_plan", {}).get("protagonist_name", "")).strip() or "The Detective"
        )
        system, user = build_story_architect_prompt(premise, protagonist, state.story_genre, state.story_tone)
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            raise RuntimeError("StoryArchitect agent returned non-JSON content.")
        try:
            parsed = parse_story_architect_output(payload)
        except StoryAgentContractError as exc:
            raise RuntimeError(f"StoryArchitect contract validation failed: {exc}") from exc
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
                contacts.append(
                    {
                        "name": npc.name,
                        "role": "assistant" if not contacts else "contact",
                        "trait": "observant",
                    }
                )
        if not contacts:
            raise RuntimeError("CharacterDesigner requires at least one NPC contact in world state.")
        system, user = build_character_designer_prompt(str(architect.get("protagonist_name", "")), contacts)
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            raise RuntimeError("CharacterDesigner agent returned non-JSON content.")
        try:
            parsed = parse_character_designer_output(payload)
        except StoryAgentContractError as exc:
            raise RuntimeError(f"CharacterDesigner contract validation failed: {exc}") from exc
        return {"contacts": _pin_seeded_assistant(list(parsed["contacts"]), contacts[0])[:3]}


class DefaultPlotDesignerAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState, architect: dict[str, Any], cast: dict[str, Any]) -> dict[str, Any]:
        goal = state.active_goal
        contacts = cast.get("contacts", [])
        assistant = contacts[0]["name"] if contacts else ""
        suspect = _pick_suspect_name(contacts, assistant)
        system, user = build_plot_designer_prompt(goal, assistant or "Assistant")
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            raise RuntimeError("PlotDesigner agent returned non-JSON content.")
        try:
            parsed = parse_plot_designer_output(payload)
        except StoryAgentContractError as exc:
            raise RuntimeError(f"PlotDesigner contract validation failed: {exc}") from exc
        normalized = dict(parsed)
        normalized["actionable_objective"] = _normalize_actionable_objective_language(
            str(normalized.get("actionable_objective", "")),
            str(normalized.get("assistant_name", "")),
            suspect,
        )
        return normalized


class DefaultNarratorOpeningAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState, architect: dict[str, Any], cast: dict[str, Any], plan: dict[str, Any]) -> list[str]:
        room = state.world.rooms[state.player.location]
        protagonist = str(architect.get("protagonist_name", "")).strip() or "the detective"
        background = str(architect.get("protagonist_background", "")).strip()
        contacts = cast.get("contacts", [])
        assistant_name = str(plan.get("assistant_name", "")).strip()
        suspect_name = _pick_suspect_name(contacts, assistant_name)
        assistant_trait = str(contacts[0].get("trait", "")).strip() if contacts else ""
        assistant_role = str(contacts[0].get("role", "")).strip() if contacts else ""

        inventory = [item.replace("_", " ") for item in state.player.inventory]
        carry_line = (
            "At your side you carry " + ", ".join(f"a {item}" for item in inventory[:2]) + "."
            if inventory
            else "Your hands are empty for now."
        )
        identity_intro = _build_identity_intro_sentence(protagonist, background)
        paragraph_1 = (
            f"The air around the {room.name.lower()} bites with evening cold as damp stone keeps the day's last heat "
            "and distant traffic thins into rumor."
        )
        paragraph_2 = (
            f"{identity_intro} {carry_line} "
            f"{assistant_name} stays close as your {assistant_role or 'assistant'}, "
            f"{assistant_name}'s tone {assistant_trait or 'measured'} while {assistant_name} waits for your first instruction."
        )
        paragraph_3 = "Your history sits just behind your eyes, unresolved but sharp enough to focus your judgment."
        objective = _normalize_actionable_objective_language(
            str(plan.get("actionable_objective", state.active_goal)).strip(),
            assistant_name,
            suspect_name,
        )
        if assistant_name:
            paragraph_4 = (
                f"{assistant_name} breaks the silence. "
                "\"Your immediate objective is practical: start with the case file "
                f"and field kit. {objective}\""
            )
        else:
            paragraph_4 = f"Your immediate objective is practical and immediate: {objective}"

        opening = [paragraph_1, paragraph_2, paragraph_3, paragraph_4]
        system, user = build_narrator_opening_prompt("\n\n".join(opening))
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            raise RuntimeError("NarratorOpening agent returned non-JSON content.")
        try:
            parsed = parse_narrator_opening_output(payload)
        except StoryAgentContractError as exc:
            raise RuntimeError(f"NarratorOpening contract validation failed: {exc}") from exc
        return _normalize_assistant_references(parsed["paragraphs"][:4], assistant_name)


class DefaultStoryReplanAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(self, state: GameState, disruption: dict[str, Any]) -> dict[str, Any]:
        impact_class = str(disruption.get("impact_class", "high")).strip().lower()
        reasons = tuple(str(reason).strip().lower() for reason in disruption.get("reasons", ()) if str(reason).strip())
        command = str(disruption.get("command", "")).strip()

        high_violence = "violent_action" in reasons or "criminal_behavior" in reasons or "authority_target" in reasons
        if impact_class == "critical" or high_violence:
            new_goal = "Manage the fallout from your last choice while evading immediate institutional consequences."
            note = "The story shifts hard: consequences are now active, and former allies may no longer be reliable."
        else:
            new_goal = "Adapt to the consequences of your last choice and rebuild a viable lead."
            note = "The story shifts: your last choice changes what progress now requires."

        return {
            "new_active_goal": new_goal,
            "note": note,
            "impact_class": impact_class,
            "trigger_command": command,
            "mode": self._mode,
        }


class DefaultRoomPresentationAgent:
    def __init__(self, mode: str) -> None:
        self._mode = mode

    def run(
        self,
        state: GameState,
        architect: dict[str, Any],  # noqa: ARG002
        cast: dict[str, Any],  # noqa: ARG002
        plan: dict[str, Any],  # noqa: ARG002
    ) -> dict[str, dict[str, str]]:
        room_ids = tuple(state.world.rooms.keys())
        room_seed: list[dict[str, object]] = []
        for room_id in room_ids:
            room = state.world.rooms[room_id]
            room_seed.append(
                {
                    "room_id": room_id,
                    "name": room.name,
                    "description_seed": room.description,
                    "exits": sorted(room.exits.keys()),
                    "items": [item.replace("_", " ") for item in room.item_ids],
                    "npcs": [state.world.npcs[npc_id].name for npc_id in room.npc_ids if npc_id in state.world.npcs],
                }
            )
        system, user = build_room_presentation_prompt(state.story_genre, state.story_tone, room_seed)
        payload = _json_from_text(_chat_complete(self._mode, system, user))
        if payload is None:
            raise RuntimeError("RoomPresentation agent returned non-JSON content.")
        try:
            parsed: RoomPresentationOutput = parse_room_presentation_output(payload, room_ids)
        except StoryAgentContractError as exc:
            raise RuntimeError(f"RoomPresentation contract validation failed: {exc}") from exc
        return {
            room["room_id"]: {
                "long": room["long"],
                "short": room["short"],
            }
            for room in parsed["rooms"]
        }

from __future__ import annotations

from dataclasses import dataclass

from storygame.engine.facts import (
    active_story_goal,
    assistant_name,
    assistant_role,
    npc_stance_toward_player,
    npc_trust_toward_player,
    planned_story_events,
    protagonist_profile,
    story_goals,
)
from storygame.engine.mystery import filtered_inventory, room_item_groups
from storygame.engine.parser import Action
from storygame.engine.scene_state import scene_snapshot
from storygame.engine.state import EventLog, GameState, Npc
from storygame.story_canon import canonical_detective_name

MAX_RECENT_EVENTS = 5
MAX_VISIBLE_ITEMS = 6
MAX_INVENTORY_ITEMS = 8
MAX_EVENT_MESSAGE_LEN = 120
MAX_NPC_FACTS = 12
MAX_NPC_DESCRIPTION_LEN = 100
MAX_MEMORY_FRAGMENTS = 3
MAX_MEMORY_FRAGMENT_LEN = 220

HARD_CONSTRAINTS = (
    "state_changes_must_be_explicit_and_fact_backed",
    "do_not_invent_facts",
    "must_match_engine_context",
)


@dataclass(frozen=True)
class NarrationContext:
    room_name: str
    room_description: str
    visible_items: tuple[str, ...]
    visible_npcs: tuple[str, ...]
    npc_facts: tuple[dict, ...]
    exits: tuple[str, ...]
    inventory: tuple[str, ...]
    recent_events: tuple[dict, ...]
    phase: str
    tension: float
    beat: str
    goal: str
    goal_stack: dict = None
    scene: dict = None
    planned_events: tuple[dict, ...] = ()
    action: str = ""
    protagonist_name: str = ""
    protagonist_background: str = ""
    assistant_name: str = ""
    assistant_role: str = ""
    memory_fragments: tuple[str, ...] = ()
    conversation_intent: str = ""
    conversation_topic: str = ""
    addressed_npc_id: str = ""
    addressed_npc_name: str = ""
    prefer_npc_reply: bool = False

    def as_dict(self) -> dict:
        return {
            "room_name": self.room_name,
            "room_description": self.room_description,
            "protagonist_name": self.protagonist_name,
            "assistant_name": self.assistant_name,
            "visible_items": list(self.visible_items),
            "visible_npcs": list(self.visible_npcs),
            "npc_facts": list(self.npc_facts),
            "exits": list(self.exits),
            "inventory": list(self.inventory),
            "recent_events": list(self.recent_events),
            "phase": self.phase,
            "tension": self.tension,
            "beat": self.beat,
            "goal": self.goal,
            "goal_stack": dict(self.goal_stack or {}),
            "scene": dict(self.scene or {}),
            "planned_events": list(self.planned_events),
            "action": self.action,
            "memory_fragments": list(self.memory_fragments),
            "protagonist_background": self.protagonist_background,
            "assistant_role": self.assistant_role,
            "conversation_intent": self.conversation_intent,
            "conversation_topic": self.conversation_topic,
            "addressed_npc_id": self.addressed_npc_id,
            "addressed_npc_name": self.addressed_npc_name,
            "prefer_npc_reply": self.prefer_npc_reply,
            "constraints": list(HARD_CONSTRAINTS),
        }


def _short_message(value: str) -> str:
    if len(value) <= MAX_EVENT_MESSAGE_LEN:
        return value
    return value[: MAX_EVENT_MESSAGE_LEN - 3] + "..."


def _short_text(value: str, max_len: int) -> str:
    if len(value) <= max_len:
        return value
    return value[: max_len - 3] + "..."


def _npc_fact(npc: Npc, location: str) -> dict[str, str]:
    return {
        "id": npc.id,
        "name": npc.name,
        "pronouns": npc.pronouns,
        "identity": _short_text(npc.identity, MAX_NPC_DESCRIPTION_LEN),
        "description": _short_text(npc.description, MAX_NPC_DESCRIPTION_LEN),
        "appearance": _short_text(npc.appearance, MAX_NPC_DESCRIPTION_LEN),
        "location": location,
        "stance_to_player": "",
        "trust_to_player": "",
    }


def _summarize_recent_events(events: EventLog) -> tuple[dict, ...]:
    trimmed = events.tail(MAX_RECENT_EVENTS)
    return tuple(
        {
            "type": event.type,
            "message_key": _short_message(event.message_key),
            "entities": list(event.entities),
            "tags": list(event.tags),
            "turn_index": event.turn_index,
        }
        for event in trimmed
    )


def _npc_locations(state: GameState) -> dict[str, str]:
    locations: dict[str, str] = {}
    for room_id, room in state.world.rooms.items():
        for npc_id in room.npc_ids:
            locations[npc_id] = room_id
    return locations


def _summarize_npc_facts(state: GameState) -> tuple[dict, ...]:
    locations = _npc_locations(state)
    npc_ids = sorted(state.world.npcs.keys())
    facts: list[dict[str, str]] = []
    for npc_id in npc_ids[:MAX_NPC_FACTS]:
        fact = _npc_fact(state.world.npcs[npc_id], locations.get(npc_id, ""))
        fact["stance_to_player"] = npc_stance_toward_player(state, npc_id)
        fact["trust_to_player"] = npc_trust_toward_player(state, npc_id)
        facts.append(fact)
    return tuple(facts)


def _latest_freeform_focus(state: GameState) -> dict[str, object]:
    events = tuple(reversed(state.event_log.events))
    for event in events:
        if event.type != "freeform_roleplay":
            continue
        metadata = event.metadata
        action_proposal = metadata.get("action_proposal", {})
        if not isinstance(action_proposal, dict):
            return {}
        intent = str(action_proposal.get("intent", "")).strip()
        targets = action_proposal.get("targets", ())
        if not isinstance(targets, (list, tuple)) or not targets:
            return {"conversation_intent": intent, "conversation_topic": "", "prefer_npc_reply": False}
        target_id = str(targets[0]).strip()
        npc = state.world.npcs.get(target_id)
        arguments = action_proposal.get("arguments", {})
        topic = ""
        if isinstance(arguments, dict):
            topic = str(arguments.get("topic", "")).strip()
        return {
            "conversation_intent": intent,
            "conversation_topic": topic,
            "addressed_npc_id": target_id,
            "addressed_npc_name": npc.name if npc is not None else "",
            "prefer_npc_reply": bool(target_id and intent in {"ask_about", "greet", "apologize", "threaten"}),
        }
    return {}


def _protagonist_name(state: GameState) -> str:
    profile = protagonist_profile(state)
    protagonist = profile["name"].strip()
    if protagonist:
        return canonical_detective_name(state.story_genre, protagonist)
    bundle = dict(state.world_package.get("llm_story_bundle", {}))
    protagonist = str(bundle.get("protagonist_name", "")).strip()
    if protagonist:
        return canonical_detective_name(state.story_genre, protagonist)
    story_plan = dict(state.world_package.get("story_plan", {}))
    protagonist = str(story_plan.get("protagonist_name", "")).strip()
    if protagonist:
        return canonical_detective_name(state.story_genre, protagonist)
    return canonical_detective_name(state.story_genre, "")


def _assistant_name(state: GameState) -> str:
    resolved = assistant_name(state).strip()
    if resolved:
        return resolved
    bundle = dict(state.world_package.get("llm_story_bundle", {}))
    bundle_assistant_name = str(bundle.get("assistant_name", "")).strip()
    if bundle_assistant_name:
        return bundle_assistant_name
    room = state.world.rooms[state.player.location]
    if room.npc_ids:
        npc = state.world.npcs.get(room.npc_ids[0])
        if npc is not None and npc.name.strip():
            return npc.name.strip()
    for npc_id in sorted(state.world.npcs):
        npc = state.world.npcs[npc_id]
        if npc.name.strip():
            return npc.name.strip()
    return ""


def _protagonist_background(state: GameState) -> str:
    profile = protagonist_profile(state)
    if profile["background"].strip():
        return profile["background"].strip()
    bundle = dict(state.world_package.get("llm_story_bundle", {}))
    background = str(bundle.get("protagonist_background", "")).strip()
    if background:
        return background
    story_plan = dict(state.world_package.get("story_plan", {}))
    return str(story_plan.get("protagonist_background", "")).strip()


def _assistant_role(state: GameState) -> str:
    resolved_assistant = _assistant_name(state)
    role = assistant_role(state, resolved_assistant)
    if role:
        return role
    bundle = dict(state.world_package.get("llm_story_bundle", {}))
    assistant_name = str(bundle.get("assistant_name", "")).strip().lower()
    contacts = bundle.get("contacts", ())
    for contact in contacts:
        if not isinstance(contact, dict):
            continue
        if str(contact.get("name", "")).strip().lower() == assistant_name:
            return str(contact.get("role", "")).strip()
    story_cast = dict(state.world_package.get("story_cast", {}))
    for contact in story_cast.get("contacts", ()):
        if not isinstance(contact, dict):
            continue
        if str(contact.get("name", "")).strip().lower() == _assistant_name(state).strip().lower():
            return str(contact.get("role", "")).strip()
    return ""


def build_narration_context(
    state: GameState,
    action: Action,
    beat: str,
    memory_fragments: tuple[str, ...] = (),
) -> NarrationContext:
    room = state.world.rooms[state.player.location]
    visible_items, _junk_count = room_item_groups(state, room)
    freeform_focus = _latest_freeform_focus(state)
    scene = scene_snapshot(state)
    scene_payload = {
        "id": str(scene["scene_id"]),
        "location_id": str(scene["location_id"]),
        "objective": str(scene["scene_objective"]),
        "dramatic_question": str(scene["dramatic_question"]),
        "pressure": str(scene["pressure"]),
        "beat_phase": str(scene["beat_phase"]),
        "beat_role": str(scene["beat_role"]),
        "player_approach": str(scene["player_approach"]),
        "participants": list(scene["participants"]),
    }

    return NarrationContext(
        room_name=room.name,
        room_description=room.description,
        protagonist_name=_protagonist_name(state),
        protagonist_background=_protagonist_background(state),
        assistant_name=_assistant_name(state),
        assistant_role=_assistant_role(state),
        visible_items=visible_items[:MAX_VISIBLE_ITEMS],
        visible_npcs=room.npc_ids,
        npc_facts=_summarize_npc_facts(state),
        exits=tuple(sorted(room.exits.keys())),
        inventory=filtered_inventory(state)[:MAX_INVENTORY_ITEMS],
        memory_fragments=tuple(
            _short_text(frag, MAX_MEMORY_FRAGMENT_LEN) for frag in memory_fragments[:MAX_MEMORY_FRAGMENTS]
        ),
        recent_events=_summarize_recent_events(state.event_log),
        phase=str(scene["beat_phase"]),
        tension=state.tension,
        beat=beat,
        goal=active_story_goal(state),
        goal_stack=story_goals(state),
        scene=scene_payload,
        planned_events=planned_story_events(state),
        action=action.raw,
        conversation_intent=str(freeform_focus.get("conversation_intent", "")),
        conversation_topic=str(freeform_focus.get("conversation_topic", "")),
        addressed_npc_id=str(freeform_focus.get("addressed_npc_id", "")),
        addressed_npc_name=str(freeform_focus.get("addressed_npc_name", "")),
        prefer_npc_reply=bool(freeform_focus.get("prefer_npc_reply", False)),
    )

from __future__ import annotations

from storygame.llm.context import HARD_CONSTRAINTS, NarrationContext

SYSTEM_CONSTRAINTS = (
    "Narrate only and do not invent facts.",
    "Never mention details not present in the context slice.",
    "Any state change you narrate must be explicit, limited to engine context, and fact-representable.",
    "Never use memory fragments to override engine facts.",
    "Opening scene (turn 0 only): write 3-4 paragraphs.",
    "Opening scene must establish who the player is, where they are, and the immediate objective.",
    "Opening scene should use concrete sensory details and atmosphere grounded in known context.",
    "Opening scene must stay materially consistent with the room description, exits, visible items, visible NPCs, and inventory.",
    "Do not invent extra furniture, desks, tables, papers, or document staging that are not present in the context slice.",
    "Turn format after opening: room name, room description, items naturally in prose, exits, then NPC interactions or background events.",
    "For conversational freeform turns with an addressed NPC, prefer a direct in-world reply from that NPC and do not restate the room block first.",
    "Spoiler discipline: do not reveal later twists early.",
)


def build_prompt(context: NarrationContext) -> dict[str, str]:
    system = "\n".join(SYSTEM_CONSTRAINTS)
    payload = context.as_dict()
    npc_facts_line = ", ".join(
        f"{fact['name']} [{fact['pronouns']}] ({fact['identity']}) @ {fact['location']}"
        + (f" appearance={fact['appearance']}" if str(fact.get("appearance", "")).strip() else "")
        + (f" relation={fact['relationship_to_player']}" if str(fact.get("relationship_to_player", "")).strip() else "")
        + (f" purpose={fact['scene_purpose']}" if str(fact.get("scene_purpose", "")).strip() else "")
        for fact in payload["npc_facts"]
    )
    item_facts_line = "; ".join(
        (
            f"{fact['name']} [{fact['kind']}; portable={fact['portable']}"
            + (f"; owner={fact['owner']}" if str(fact.get("owner", "")).strip() else "")
            + (f"; driver={fact['driver']}" if str(fact.get("driver", "")).strip() else "")
            + (f"; state={fact['state']}" if str(fact.get("state", "")).strip() else "")
            + f"]: {fact['description']}"
        )
        for fact in payload["item_facts"]
    )
    user = (
        f"Action: {payload['action']}\n"
        f"Beat: {payload['beat']}\n"
        f"Phase: {payload['phase']}\n"
        f"Tension: {payload['tension']:.2f}\n"
        f"Scene ID: {payload['scene'].get('id', '')}\n"
        f"Scene objective: {payload['scene'].get('objective', '')}\n"
        f"Dramatic question: {payload['scene'].get('dramatic_question', '')}\n"
        f"Scene pressure: {payload['scene'].get('pressure', '')}\n"
        f"Player approach: {payload['scene'].get('player_approach', '')}\n"
        f"Location: {payload['room_name']}\n"
        f"Room description: {payload['room_description']}\n"
        f"Scene facts: {' | '.join(payload['scene_facts'])}\n"
        f"Protagonist: {payload['protagonist_name']}\n"
        f"Protagonist background: {payload['protagonist_background']}\n"
        f"Assistant anchor: {payload['assistant_name']}\n"
        f"Assistant role: {payload['assistant_role']}\n"
        f"Addressed NPC: {payload['addressed_npc_name']}\n"
        f"Conversation intent: {payload['conversation_intent']}\n"
        f"Conversation topic: {payload['conversation_topic']}\n"
        f"Prefer NPC reply: {payload['prefer_npc_reply']}\n"
        f"Visible items: {', '.join(payload['visible_items'])}\n"
        f"Visible item facts: {item_facts_line}\n"
        f"Visible NPCs: {', '.join(payload['visible_npcs'])}\n"
        f"Soft memory hints (non-authoritative): {', '.join(payload['memory_fragments'])}\n"
        f"Canonical NPC facts: {npc_facts_line}\n"
        f"Inventory: {', '.join(payload['inventory'])}\n"
        f"Exits: {', '.join(payload['exits'])}\n"
        f"Recent events: {[e['message_key'] for e in payload['recent_events']]}\n"
        f"Active goal: {payload['goal']}\n"
        f"Hard constraints: {', '.join(HARD_CONSTRAINTS)}\n"
        "Rule: use only engine context for truth; memory hints are suggestions for continuity."
    )
    return {"system": system, "user": user}


def build_prompt_text(context: NarrationContext) -> str:
    payload = build_prompt(context)
    return f"SYSTEM:\n{payload['system']}\n\nUSER:\n{payload['user']}"

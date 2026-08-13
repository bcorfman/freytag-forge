from __future__ import annotations

from storygame.llm.context import HARD_CONSTRAINTS, NarrationContext

SYSTEM_CONSTRAINTS = (
    "Narrate only and do not invent facts.",
    "Never mention details not present in the context slice.",
    "Any state change you narrate must be explicit, limited to engine context, and fact-representable.",
    "Never use memory fragments to override engine facts.",
    "Opening scene (turn 0 only): write 3-4 paragraphs.",
    "Opening scene must establish who the player is, where they are, and the immediate objective.",
    "Opening scene: introduce the protagonist by name and background in the first paragraph, before or alongside the setting.",
    "Opening scene: summarize the permitted public situation facts that explain why the player is here, including the case setup when those facts are present.",
    "Opening scene: use present tense.",
    "Opening scene should focus primarily on protagonist background, motivation, communication, and relationships.",
    "Opening scene may use atmospheric detail only in support of character pressure or the immediate objective; remove scenery-first filler unless it is needed for flow or story cohesion.",
    "Opening scene must stay materially consistent with the room description, exits, visible items, visible NPCs, and inventory.",
    "Opening scene: on first mention of a visible NPC, introduce them by full name, not only first name.",
    "After that introduction, use that character's given name and a brief presence or action; repeat the full name only when two characters share the given name and clarity requires it.",
    "After turn 0, do not reintroduce the protagonist, assistant, or other already-established characters as if the player has just met them; continue the scene from their existing relationship and knowledge.",
    "After turn 0, do not repeat already-established stakes, atmosphere, or investigation pressure from the opening or recent events. Advance the immediate situation instead.",
    "Do not invent extra furniture, desks, tables, papers, or document staging that are not present in the context slice.",
    "Turn format after opening: use the room name and room description as prose anchors; weave visible items naturally in prose, then ground named routes and NPC interactions or background events. Never use compass directions.",
    "Never output prompt field labels, a context checklist, JSON, markdown headings, or the player's statement echoed back; respond to its meaning in new prose instead.",
    "For conversational freeform turns with an addressed NPC, prefer a direct in-world reply from that NPC and do not restate the room block first.",
    "Write grounded roleplay, not a status report: characters act from their supplied motives, relationships, knowledge, emotional pressure, and limits, with believable initiative, subtext, disagreement, and hesitation.",
    "Treat performance as presentation only: voice, attention, body language, pacing, and expression may vary, but never introduce a fact, protected knowledge, event, or visible state change without an accepted commit.",
    "For ordinary turns, start from the meaningful human or situational response to the player's move. Mention room, inventory, exits, or visible items only when they affect what someone perceives, risks, does, or can reasonably attempt.",
    "Spoiler discipline: do not reveal later twists early.",
)


def build_prompt(context: NarrationContext) -> dict[str, str]:
    system = "\n".join(SYSTEM_CONSTRAINTS)
    payload = context.as_dict()
    visible_item_labels = [str(fact.get("name", "")).strip() for fact in payload["item_facts"] if str(fact.get("name", "")).strip()]
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
    case_facts_line = "; ".join(f"{fact['key']}={fact['value']}" for fact in payload["case_facts"])
    user = (
        f"Turn index: {payload['turn_index']}\n"
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
        f"Canonical case facts: {case_facts_line}\n"
        f"Protagonist: {payload['protagonist_name']}\n"
        f"Protagonist background: {payload['protagonist_background']}\n"
        f"Assistant anchor: {payload['assistant_name']}\n"
        f"Assistant role: {payload['assistant_role']}\n"
        f"Addressed NPC: {payload['addressed_npc_name']}\n"
        f"Conversation intent: {payload['conversation_intent']}\n"
        f"Conversation topic: {payload['conversation_topic']}\n"
        f"Prefer NPC reply: {payload['prefer_npc_reply']}\n"
        f"Visible items: {', '.join(visible_item_labels)}\n"
        f"Visible item facts: {item_facts_line}\n"
        f"Visible NPCs: {', '.join(payload['visible_npcs'])}\n"
        f"Soft memory hints (non-authoritative): {', '.join(payload['memory_fragments'])}\n"
        f"Canonical NPC facts: {npc_facts_line}\n"
        f"Inventory: {', '.join(payload['inventory'])}\n"
        f"Exits: {', '.join(payload['exits'])}\n"
        f"Recent events: {[e['message_key'] for e in payload['recent_events']]}\n"
        f"Active goal: {payload['goal']}\n"
        f"Hard constraints: {', '.join(HARD_CONSTRAINTS)}\n"
        f"Completion instruction: {payload['completion_instruction']}\n"
        "Rule: use only engine context for truth; memory hints are suggestions for continuity."
    )
    return {"system": system, "user": user}


def build_prompt_text(context: NarrationContext) -> str:
    payload = build_prompt(context)
    return f"SYSTEM:\n{payload['system']}\n\nUSER:\n{payload['user']}"

from __future__ import annotations

from storygame.llm.context import HARD_CONSTRAINTS, NarrationContext

SYSTEM_CONSTRAINTS = (
    "Narrate only and do not invent facts.",
    "Never mention details not present in the context slice.",
    "Do not change world state or output commands.",
    "Never use memory fragments to override engine facts.",
)


def build_prompt(context: NarrationContext) -> dict[str, str]:
    system = "\n".join(SYSTEM_CONSTRAINTS)
    payload = context.as_dict()
    npc_facts_line = ", ".join(
        f"{fact['name']} [{fact['pronouns']}] ({fact['identity']}) @ {fact['location']}"
        for fact in payload["npc_facts"]
    )
    user = (
        f"Action: {payload['action']}\n"
        f"Beat: {payload['beat']}\n"
        f"Phase: {payload['phase']}\n"
        f"Tension: {payload['tension']:.2f}\n"
        f"Location: {payload['room_name']}\n"
        f"Visible items: {', '.join(payload['visible_items'])}\n"
        f"Visible NPCs: {', '.join(payload['visible_npcs'])}\n"
        f"Soft memory hints (non-authoritative): {', '.join(payload['memory_fragments'])}\n"
        f"Canonical NPC facts: {npc_facts_line}\n"
        f"Inventory: {', '.join(payload['inventory'])}\n"
        f"Recent events: {[e['message_key'] for e in payload['recent_events']]}\n"
        f"Active goal: {payload['goal']}\n"
        f"Hard constraints: {', '.join(HARD_CONSTRAINTS)}\n"
        "Rule: use only engine context for truth; memory hints are suggestions for continuity."
    )
    return {"system": system, "user": user}


def build_prompt_text(context: NarrationContext) -> str:
    payload = build_prompt(context)
    return f"SYSTEM:\n{payload['system']}\n\nUSER:\n{payload['user']}"

from __future__ import annotations

import re

from storygame.engine.state import GameState

_FIRST_PERSON_WEARING_PATTERN = re.compile(
    r"\b(?:i['’]?m|i\s+am)\s+wearing\s+(?:the\s+)?[\"']?(.+?)[\"']?[.!?]*$",
    re.IGNORECASE,
)


def _normalized_appearance_phrase(text: str) -> str:
    match = _FIRST_PERSON_WEARING_PATTERN.search(" ".join(text.split()).strip())
    if match is None:
        return ""
    phrase = match.group(1).strip(" \"'.,;:!?").lower()
    if not phrase:
        return ""
    return phrase if phrase.startswith(("a ", "an ", "the ")) else f"a {phrase}"


def dialogue_fact_conflict(state: GameState, speaker_id: str, text: str, topic: str = "") -> str:
    """Return a player-safe error when dialogue contradicts committed appearance facts."""
    normalized_speaker = speaker_id.strip().lower()
    if not normalized_speaker or normalized_speaker not in state.world.npcs:
        return ""
    if topic.strip().lower() not in {"appearance", "clothing", "clothes", "wearing"}:
        return ""
    mentioned = _normalized_appearance_phrase(text)
    if not mentioned:
        return ""
    existing = state.world_facts.query("npc_appearance", normalized_speaker, None)
    if not existing:
        return ""
    committed = existing[0][2].strip().lower()
    if committed == mentioned or committed in mentioned or mentioned in committed:
        return ""
    return f"{state.world.npcs[normalized_speaker].name}'s reply conflicts with committed appearance facts."

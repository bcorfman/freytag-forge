from __future__ import annotations

import re

from storygame.engine.state import GameState

_CLAUSE_SPLIT_PATTERN = re.compile(r"[\n.!?;]+")
_SPACE_PATTERN = re.compile(r"\s+")
_TAKE_VERB_PATTERN = re.compile(r"\b(takes?|pick(?:s)? up|grabs?|collects?|pockets?|holds?)\b")
_MOVE_VERB_PATTERN = re.compile(r"\b(moves?|goes?|heads?|walks?|steps?)\b")
_FIRST_PERSON_WEARING_PATTERN = re.compile(
    r"\b(?:i am|i'm|im)\s+wearing\s+(.+?)(?:[.!?]|$)",
    re.IGNORECASE,
)


def _normalize_phrase(value: str) -> str:
    lowered = value.lower().replace("_", " ")
    lowered = re.sub(r"[^a-z0-9\s'-]", " ", lowered)
    return _SPACE_PATTERN.sub(" ", lowered).strip()


def _sorted_aliases(alias_map: dict[str, str]) -> tuple[str, ...]:
    return tuple(sorted(alias_map.keys(), key=len, reverse=True))


def _actor_aliases(state: GameState) -> dict[str, str]:
    aliases: dict[str, str] = {"you": "player"}
    first_name_counts: dict[str, int] = {}
    for npc in state.world.npcs.values():
        full_name = _normalize_phrase(npc.name)
        if full_name:
            aliases[full_name] = npc.id
            first_name = full_name.split(" ", 1)[0]
            first_name_counts[first_name] = first_name_counts.get(first_name, 0) + 1
    for npc in state.world.npcs.values():
        full_name = _normalize_phrase(npc.name)
        if not full_name:
            continue
        first_name = full_name.split(" ", 1)[0]
        if first_name_counts.get(first_name, 0) == 1:
            aliases[first_name] = npc.id
    return aliases


def _item_aliases(state: GameState) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for item_id, item in state.world.items.items():
        for alias in (_normalize_phrase(item_id), _normalize_phrase(item.name)):
            if alias:
                aliases[alias] = item_id
                if alias.startswith("a "):
                    aliases[alias[2:]] = item_id
                if alias.startswith("an "):
                    aliases[alias[3:]] = item_id
                if alias.startswith("the "):
                    aliases[alias[4:]] = item_id
    return aliases


def _room_aliases(state: GameState) -> dict[str, str]:
    aliases: dict[str, str] = {}
    for room_id, room in state.world.rooms.items():
        for alias in (_normalize_phrase(room_id), _normalize_phrase(room.name)):
            if alias:
                aliases[alias] = room_id
    return aliases


def _resolve_actor(clause: str, aliases: dict[str, str]) -> str:
    for alias in _sorted_aliases(aliases):
        if clause.startswith(alias + " ") or clause == alias:
            return aliases[alias]
    return ""


def _resolve_suffix_entity(fragment: str, aliases: dict[str, str]) -> str:
    for alias in _sorted_aliases(aliases):
        if re.search(rf"\b(?:the |a |an )?{re.escape(alias)}\b", fragment):
            return aliases[alias]
    return ""


def _take_fact_ops(actor_id: str, item_id: str) -> list[dict[str, object]]:
    return [{"op": "assert", "fact": ("holding", actor_id, item_id)}]


def _movement_fact_ops(actor_id: str, room_id: str) -> list[dict[str, object]]:
    predicate = "at" if actor_id == "player" else "npc_at"
    return [{"op": "assert", "fact": (predicate, actor_id, room_id)}]


def _normalized_appearance_phrase(text: str) -> str:
    match = _FIRST_PERSON_WEARING_PATTERN.search(text.strip())
    if match is None:
        return ""
    phrase = " ".join(match.group(1).strip().split()).strip(" \"'")
    phrase = re.sub(r"^(?:a|an|the)\s+", "", phrase, flags=re.IGNORECASE)
    if not phrase:
        return ""
    return f"a {phrase.lower()}"


def extract_dialogue_fact_ops(state: GameState, speaker_id: str, text: str, topic: str = "") -> list[dict[str, object]]:
    normalized_speaker = speaker_id.strip().lower()
    if not normalized_speaker or normalized_speaker not in state.world.npcs:
        return []
    if topic.strip().lower() not in {"appearance", "clothing", "clothes", "wearing"}:
        return []
    appearance = _normalized_appearance_phrase(text)
    if not appearance:
        return []
    existing = state.world_facts.query("npc_appearance", normalized_speaker, None)
    if existing and existing[0][2].strip().lower() == appearance:
        return []
    return [{"op": "assert", "fact": ("npc_appearance", normalized_speaker, appearance)}]


def dialogue_fact_conflict(state: GameState, speaker_id: str, text: str, topic: str = "") -> str:
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
    if committed == mentioned:
        return ""
    if committed in mentioned or mentioned in committed:
        return ""
    npc = state.world.npcs[normalized_speaker]
    return f"{npc.name}'s reply conflicts with committed appearance facts."


def extract_narration_fact_ops(state: GameState, narration: str) -> list[dict[str, object]]:
    if not narration.strip():
        return []

    actor_aliases = _actor_aliases(state)
    item_alias_map = _item_aliases(state)
    room_alias_map = _room_aliases(state)
    ops: list[dict[str, object]] = []
    seen: set[tuple[str, ...]] = set()

    for raw_clause in _CLAUSE_SPLIT_PATTERN.split(narration):
        clause = _normalize_phrase(raw_clause)
        if not clause:
            continue
        actor_id = _resolve_actor(clause, actor_aliases)
        if not actor_id:
            continue
        if _TAKE_VERB_PATTERN.search(clause):
            item_id = _resolve_suffix_entity(clause, item_alias_map)
            if item_id:
                fact = ("holding", actor_id, item_id)
                if fact not in seen:
                    ops.extend(_take_fact_ops(actor_id, item_id))
                    seen.add(fact)
                continue
        if _MOVE_VERB_PATTERN.search(clause):
            room_id = _resolve_suffix_entity(clause, room_alias_map)
            if room_id:
                predicate = "at" if actor_id == "player" else "npc_at"
                fact = (predicate, actor_id, room_id)
                if fact not in seen:
                    ops.extend(_movement_fact_ops(actor_id, room_id))
                    seen.add(fact)
    return ops

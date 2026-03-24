from __future__ import annotations

import json


def build_story_bootstrap_prompt(
    premise: str,
    genre: str,
    tone: str,
    session_length: str,
    beat_candidates: list[str],
    contacts_seed: list[dict],
    opening_room: dict[str, object],
    rooms_seed: list[dict[str, object]],
    items_seed: list[dict[str, object]],
    inventory_seed: list[str],
    opening_facts: dict[str, object],
) -> tuple[str, str]:
    system = (
        "You are Story Bootstrap Agent. Return JSON only with keys: "
        "protagonist_name, protagonist_background, assistant_name, actionable_objective, primary_goal, "
        "secondary_goals, expanded_outline, story_beats, villains, timed_events, clue_placements, "
        "hidden_threads, reveal_schedule, contacts, opening_paragraphs. "
        "For mystery stories, use a named male detective protagonist and keep that identity stable in opening_paragraphs. "
        "story_beats must map the whole story arc for the requested session length. "
        "villains must explain motive, means, and opportunity. "
        "clue_placements must use exact provided item_id and room_id values and should keep meaningful clues hidden in plausible places. "
        "timed_events must use exact provided room_id values when referencing locations. "
        "opening_paragraphs must contain 3 to 4 paragraphs of direct player-facing opening prose. "
        "opening_paragraphs must stay materially consistent with opening_room description, exits, visible NPCs, visible items, and inventory_seed. "
        "Prioritize character setup over scenic repetition: establish protagonist background, motivation, communication, and relationships first. "
        "Remove scenery-first filler unless it is needed for flow or story cohesion, and only keep scenic detail when it directly changes character intent, conflict, or stakes. "
        "On first mention of a visible NPC in opening_paragraphs, use that NPC's full name. "
        "Treat opening_facts as canonical opening state for role, custody, scene-purpose, and pending-knowledge continuity; do not contradict opening_facts. "
        "Use only provided context. Keep spoilers out of opening_paragraphs and protagonist_background."
    )
    user = json.dumps(
        {
            "premise": premise,
            "genre": genre,
            "tone": tone,
            "session_length": session_length,
            "beat_candidates": beat_candidates,
            "contacts_seed": contacts_seed,
            "opening_room": opening_room,
            "rooms_seed": rooms_seed,
            "items_seed": items_seed,
            "inventory_seed": inventory_seed,
            "opening_facts": opening_facts,
        },
        ensure_ascii=True,
    )
    return system, user


def build_story_architect_prompt(premise: str, protagonist_hint: str, genre: str, tone: str) -> tuple[str, str]:
    system = (
        "You are Story Architect Agent. Return JSON only with keys: "
        "protagonist_name, protagonist_background, secrets_to_hide, tone. "
        "Keep spoilers out of protagonist_background. "
        "For mystery stories, make the protagonist a named male detective."
    )
    user = json.dumps(
        {
            "premise": premise,
            "protagonist_hint": protagonist_hint,
            "genre": genre,
            "tone": tone,
        },
        ensure_ascii=True,
    )
    return system, user


def build_character_designer_prompt(protagonist_name: str, contacts_seed: list[dict]) -> tuple[str, str]:
    system = (
        "You are Character Designer Agent. Return JSON only with key contacts, where contacts is a list of "
        "objects with fields: name, role, trait. Do not use placeholders like Premise/Scene."
    )
    user = json.dumps(
        {
            "protagonist_name": protagonist_name,
            "contacts_seed": contacts_seed,
        },
        ensure_ascii=True,
    )
    return system, user


def build_plot_designer_prompt(active_goal: str, assistant_name: str, assistant_facts: dict[str, object]) -> tuple[str, str]:
    system = (
        "You are Plot Designer Agent. Return JSON only with keys assistant_name and actionable_objective. "
        "actionable_objective must be concrete and immediately playable. "
        "Treat assistant_facts as canonical role and scene-purpose context when shaping the objective."
    )
    user = json.dumps(
        {
            "active_goal": active_goal,
            "assistant_name": assistant_name,
            "assistant_facts": assistant_facts,
        },
        ensure_ascii=True,
    )
    return system, user


def build_narrator_opening_prompt(opening_draft: str, opening_facts: dict[str, object]) -> tuple[str, str]:
    system = (
        "You are Narrator Agent. Return JSON only with key paragraphs (3 to 4 paragraphs). "
        "Second person voice, present tense, no spoilers, no meta-game phrasing. "
        "When referring to named NPCs in the draft, prefer explicit names over ambiguous pronouns. "
        "Stay materially consistent with the room description, exits, visible items, visible NPCs, and inventory from the draft. "
        "Favor character background, motivation, communication, and relationship tension over repeated atmospheric room description. "
        "Remove scenery-first filler unless it is needed for flow or story cohesion, and only keep environmental detail when it changes how the characters read the moment or what they do next. "
        "On first mention of a visible NPC, use their full name. "
        "Treat opening_facts as canonical state for role, custody, scene-purpose, and pending-knowledge continuity; do not contradict opening_facts. "
        "Do not invent extra furniture, desks, tables, papers, or document staging that the draft does not support."
    )
    user = json.dumps({"opening_draft": opening_draft, "opening_facts": opening_facts}, ensure_ascii=True)
    return system, user


def build_room_presentation_prompt(
    genre: str,
    tone: str,
    rooms: list[dict[str, object]],
) -> tuple[str, str]:
    system = (
        "You are Room Presentation Agent. Return JSON only with key rooms, where rooms is a list of "
        "objects with keys room_id, long, short. Use only provided world facts. "
        "long must be a concrete 2-3 sentence location description. short must be a single concise sentence. "
        "Avoid vague filler and avoid unexplained mystery wording."
    )
    user = json.dumps({"genre": genre, "tone": tone, "rooms": rooms}, ensure_ascii=True)
    return system, user


def build_story_bootstrap_critique_prompt(
    premise: str,
    bootstrap_bundle: dict[str, object],
    rooms_seed: list[dict[str, object]],
    items_seed: list[dict[str, object]],
    opening_facts: dict[str, object],
) -> tuple[str, str]:
    system = (
        "You are Story Bootstrap Critic. Return JSON only with keys verdict, continuity_summary, issues. "
        "Be harsh. Reject plans where clue placement is implausible, villains lack motive/means/opportunity, "
        "timed events do not fit the map or cast, or canonical opening_facts are contradicted. "
        "Reject physically impossible opening staging, role contradictions, and custody/location contradictions. "
        "Use verdict='accepted' only when the story plan is coherent."
    )
    user = json.dumps(
        {
            "premise": premise,
            "bootstrap_bundle": bootstrap_bundle,
            "rooms_seed": rooms_seed,
            "items_seed": items_seed,
            "opening_facts": opening_facts,
        },
        ensure_ascii=True,
    )
    return system, user

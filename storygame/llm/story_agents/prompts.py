from __future__ import annotations

import json


def build_story_architect_prompt(premise: str, protagonist_hint: str, genre: str, tone: str) -> tuple[str, str]:
    system = (
        "You are Story Architect Agent. Return JSON only with keys: "
        "protagonist_name, protagonist_background, secrets_to_hide, tone. "
        "Keep spoilers out of protagonist_background."
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


def build_plot_designer_prompt(active_goal: str, assistant_name: str) -> tuple[str, str]:
    system = (
        "You are Plot Designer Agent. Return JSON only with keys assistant_name and actionable_objective. "
        "actionable_objective must be concrete and immediately playable."
    )
    user = json.dumps(
        {
            "active_goal": active_goal,
            "assistant_name": assistant_name,
        },
        ensure_ascii=True,
    )
    return system, user


def build_narrator_opening_prompt(opening_draft: str) -> tuple[str, str]:
    system = (
        "You are Narrator Agent. Return JSON only with key paragraphs (3 to 4 paragraphs). "
        "Second person voice, no spoilers, no meta-game phrasing. "
        "When referring to named NPCs in the draft, prefer explicit names over ambiguous pronouns."
    )
    user = json.dumps({"opening_draft": opening_draft}, ensure_ascii=True)
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

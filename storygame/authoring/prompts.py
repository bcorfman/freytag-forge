"""Prompts for the offline compiled-story authoring boundary."""

from __future__ import annotations

import json
from collections.abc import Mapping


def build_compiler_prompt(outline: str, genre_profile: Mapping[str, object]) -> str:
    """Request the portable V2 authoring contract, not runtime facts or proposals."""

    profile = json.dumps(dict(genre_profile), sort_keys=True, separators=(",", ":"))
    return (
        "Return one JSON object only, labelled by this contract: COMPILED_STORY_JSON. "
        "Create an immutable compiled-story-v1 authoring input. Include stable IDs, "
        "characters, protected revelations, and required Freytag beats. Include at least "
        "one crisis, climax, and resolution; the climax must depend on earlier required work, "
        "and a resolution must answer the central question. Pacing thresholds must increase.\n"
        f"Genre profile: {profile}\nOutline: {outline.strip()}"
    )


def build_blueprint_compiler_prompt(outline: str, genre_profile: Mapping[str, object]) -> str:
    """Request a full causal blueprint as a JSON object before play begins."""

    profile = json.dumps(dict(genre_profile), sort_keys=True, separators=(",", ":"))
    return (
        "Return one JSON object only, labelled by this contract: STORY_BLUEPRINT_JSON. "
        "Compile immutable story-blueprint-v1 data, never runtime facts or executable effects. "
        "Plan backward from the genre terminal truth. Declare dramatic phases, required outcomes, "
        "optional/substitutable beats, multiple genuinely distinct player-facing realization routes, "
        "protected facts, pressure responses, and bounded failure-forward results. Every required "
        "revelation needs the profile's minimum distinct route roles unless the profile explicitly says otherwise. "
        "Include source_outline.id and source_outline.content_hash as placeholders that the caller may "
        "verify locally.\n"
        f"Genre profile: {profile}\nOutline: {outline.strip()}"
    )

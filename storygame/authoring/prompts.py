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
    """Request one immutable causal V2 blueprint as a JSON object before play begins."""

    profile = json.dumps(dict(genre_profile), sort_keys=True, separators=(",", ":"))
    return (
        "Return one JSON object only for the STORY_BLUEPRINT_V2_JSON contract. "
        "Compile immutable story-blueprint-v2 authoring data, never runtime facts or executable effects. "
        "Declare structured locations, routes, participants, causal events, evidence opportunities, "
        "knowledge protections, revelations, realization routes, outcomes, beats, and end states. "
        "Include the supplied source provenance unchanged. Local validation is authoritative.\n"
        f"Genre profile: {profile}\nOutline: {outline.strip()}"
    )

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

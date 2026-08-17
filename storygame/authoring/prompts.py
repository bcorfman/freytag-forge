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


def build_blueprint_compiler_prompt(
    outline: str,
    genre_profile: Mapping[str, object],
    source_provenance: Mapping[str, object],
    *,
    diagnostics: tuple[Mapping[str, str], ...] = (),
) -> str:
    """Request an immutable, backwards-planned causal V2 blueprint."""

    profile = json.dumps(dict(genre_profile), sort_keys=True, separators=(",", ":"))
    provenance = json.dumps(dict(source_provenance), sort_keys=True, separators=(",", ":"))
    repair = ""
    if diagnostics:
        repair = (
            "\nRepair the candidate against these structured local diagnostics only. "
            "Do not change source provenance, weaken profile obligations, or remove obligations. "
            f"Diagnostics: {json.dumps(diagnostics, sort_keys=True, separators=(',', ':'))}"
        )
    return (
        "Return one JSON object only for the STORY_BLUEPRINT_V2_JSON contract. "
        "Compile immutable story-blueprint-v2 authoring data, never runtime facts or executable effects. "
        "Plan in order: establish terminal truths; enumerate causal events and timeline; work backward "
        "to evidence, testimony, and reachable opportunities; bind them to concrete locations; then assign "
        "revelation gates and Freytag beats. "
        "For every profile-required revelation declare independently realizable proof routes, distinguish proof "
        "from suspicion, classify each beat as required, optional/substitutable, or an alternative satisfier, "
        "and provide bounded failure-forward consequences without prescribing player actions. "
        "Include the supplied source provenance unchanged. Local validation is authoritative.\n"
        f"Genre profile: {profile}\nSource provenance: {provenance}\nOutline: {outline.strip()}{repair}"
    )

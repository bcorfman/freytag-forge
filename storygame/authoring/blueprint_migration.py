"""Temporary one-way bridge from the public ``CompiledStory`` API to Phase-1 blueprints."""

from __future__ import annotations

import hashlib

from storygame.authoring.blueprint_contracts import StoryBlueprint, validate_story_blueprint
from storygame.authoring.contracts import CompiledStory


def compiled_story_as_blueprint(story: CompiledStory) -> StoryBlueprint:
    """Project a reduced legacy fixture into the generic immutable contract.

    This deliberately preserves only the causal information already present in
    ``CompiledStory``. It is an authoring projection, never a second source of
    runtime truth, and lets consumers migrate without changing its public API.
    """

    tag_ids = [tag.id for beat in story.beats for tag in beat.completion_tags]
    tag_owner = {tag.id: beat.id for beat in story.beats for tag in beat.completion_tags}
    protected_facts = [
        {
            "id": protected.id,
            "truth_id": protected.reveal_after[0],
            "release_after": [tag_owner[tag] for tag in protected.reveal_after],
        }
        for protected in story.protected_revelations
    ]
    revelations = [
        {
            "id": beat.id,
            "summary": beat.summary,
            "prerequisite_revelations": list(beat.prerequisites),
            "completion_conditions": [tag.id for tag in beat.completion_tags],
            "protected_facts": [
                protected.id
                for protected in story.protected_revelations
                if beat.id in {tag_owner[tag] for tag in protected.reveal_after}
            ],
            "unlocks": list(beat.unlocks),
            "required": beat.required,
        }
        for beat in story.beats
    ]
    routes = [
        {
            "id": f"{beat.id}_legacy_route",
            "revelation_id": beat.id,
            "role": "legacy_completion",
            "satisfiers": [{"truth_id": tag.id, "operator": "establish"} for tag in beat.completion_tags],
            "failure_forward": {"result_truths": [tag.id for tag in beat.completion_tags]},
        }
        for beat in story.beats
    ]
    required_beats = [
        {
            "id": beat.id,
            "phase": beat.phase,
            "role": "legacy_required",
            "question": story.central_question,
            "required_outcome": beat.completion_tags[0].id,
            "revelation_dependencies": [beat.id],
            "pressure_change": 0,
            "pacing": beat.pacing.advance_after,
        }
        for beat in story.beats
        if beat.required
    ]
    optional_beats = [
        {
            "id": beat.id,
            "phase": beat.phase,
            "role": "legacy_optional",
            "narrative_function": beat.summary,
            "optional_purpose": "complication",
            "pressure_change": 0,
            "pacing": beat.pacing.advance_after,
        }
        for beat in story.beats
        if not beat.required
    ]
    answers = [beat for beat in story.beats if beat.answers_central_question]
    payload = {
        "schema_version": "story-blueprint-v1",
        "id": story.id,
        "version": story.version,
        "source_outline": {
            "id": f"{story.id}_compiled_story",
            "content_hash": hashlib.sha256(story.model_dump_json().encode()).hexdigest(),
        },
        "genre": story.genre,
        "title": story.title,
        "premise": story.premise,
        "central_question": story.central_question,
        "canonical_truths": [{"id": tag_id, "summary": f"Legacy completion tag '{tag_id}'."} for tag_id in tag_ids],
        "protected_facts": protected_facts,
        "revelations": revelations,
        "realization_routes": routes,
        "required_beats": required_beats,
        "optional_beats": optional_beats,
        "opposition_clocks": [],
        "end_states": [
            {
                "id": "legacy_resolution",
                "summary": "The legacy compiled story reaches its declared resolution.",
                "required_truths": [tag.id for beat in answers for tag in beat.completion_tags],
                "required_revelations": [beat.id for beat in story.beats if beat.required],
                "answers_central_question": True,
            }
        ],
    }
    return validate_story_blueprint(payload)

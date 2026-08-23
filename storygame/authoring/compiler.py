"""Local validation and opt-in model compilation for immutable V2 stories."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from storygame.authoring.contracts import (
    Beat,
    BeatPacing,
    Character,
    CompiledStory,
    CompletionTag,
    OpeningMetadata,
    ProtectedRevelation,
)
from storygame.authoring.prompts import build_compiler_prompt


class CompilationError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        self.detail = detail
        super().__init__(f"{code}: {detail}")


class CompilerTransport(Protocol):
    """The only authoring dependency on a model/provider adapter."""

    def generate(self, prompt: str) -> str | Mapping[str, object]: ...


def _ids(values: object, category: str) -> set[str]:
    seen: set[str] = set()
    for value in values:  # type: ignore[union-attr]
        identifier = value.id
        if identifier in seen:
            raise CompilationError("DUPLICATE_ID", f"duplicate {category} id '{identifier}'")
        seen.add(identifier)
    return seen


def _validate_pacing(story: CompiledStory) -> None:
    for beat in story.beats:
        values = (
            beat.pacing.nudge_after,
            beat.pacing.advance_after,
            beat.pacing.escalate_after,
            beat.pacing.force_consequence_after,
        )
        if values != tuple(sorted(values)) or len(set(values)) != len(values):
            raise CompilationError("INVALID_PACING", f"beat '{beat.id}' pacing thresholds must strictly increase")


def _validate_beat_graph(story: CompiledStory) -> None:
    beat_ids = _ids(story.beats, "beat")
    for beat in story.beats:
        for reference in (*beat.prerequisites, *beat.unlocks):
            if reference not in beat_ids:
                raise CompilationError("UNKNOWN_REFERENCE", f"beat '{beat.id}' references unknown beat '{reference}'")
    visiting: set[str] = set()
    visited: set[str] = set()
    by_id = {beat.id: beat for beat in story.beats}

    def visit(beat_id: str) -> None:
        if beat_id in visiting:
            raise CompilationError("PREREQUISITE_CYCLE", f"prerequisite graph contains '{beat_id}'")
        if beat_id in visited:
            return
        visiting.add(beat_id)
        for prerequisite in by_id[beat_id].prerequisites:
            visit(prerequisite)
        visiting.remove(beat_id)
        visited.add(beat_id)

    for beat_id in beat_ids:
        visit(beat_id)


def _validate_structure(story: CompiledStory) -> None:
    phases = {beat.phase for beat in story.beats}
    for phase in ("crisis", "climax", "resolution"):
        if phase not in phases:
            raise CompilationError("MISSING_REQUIRED_PHASE", f"story requires at least one '{phase}' beat")
    climax_beats = [beat for beat in story.beats if beat.phase == "climax"]
    beats_by_id = {beat.id: beat for beat in story.beats}
    if not any(
        beat.required and any(beats_by_id[prerequisite].required for prerequisite in beat.prerequisites)
        for beat in climax_beats
    ):
        raise CompilationError(
            "CLIMAX_PREREQUISITE_REQUIRED", "a required climax must depend on preceding required work"
        )
    if not any(beat.phase == "resolution" and beat.answers_central_question for beat in story.beats):
        raise CompilationError("RESOLUTION_ANSWER_REQUIRED", "a resolution must answer the central question")


def _validate_tags_and_protections(story: CompiledStory) -> None:
    tag_ids: set[str] = set()
    for beat in story.beats:
        if not beat.completion_tags:
            raise CompilationError("COMPLETION_TAG_REQUIRED", f"beat '{beat.id}' needs a completion tag")
        for tag in beat.completion_tags:
            if tag.id in tag_ids:
                raise CompilationError("DUPLICATE_ID", f"duplicate completion tag id '{tag.id}'")
            tag_ids.add(tag.id)
    _ids(story.characters, "character")
    _ids(story.protected_revelations, "protected revelation")
    for revelation in story.protected_revelations:
        for tag in revelation.reveal_after:
            if tag not in tag_ids:
                raise CompilationError(
                    "UNKNOWN_REFERENCE", f"protection '{revelation.id}' references unknown tag '{tag}'"
                )


def validate_compiled_story(payload: Mapping[str, object] | CompiledStory) -> CompiledStory:
    """Parse and locally validate all authoring semantics before session use."""

    try:
        story = payload if isinstance(payload, CompiledStory) else CompiledStory.model_validate(payload)
    except ValidationError as exc:
        first = exc.errors()[0]
        path = ".".join(str(part) for part in first["loc"])
        raise CompilationError("CONTRACT_INVALID", f"{path}: {first['type']}") from exc
    _validate_beat_graph(story)
    _validate_structure(story)
    _validate_tags_and_protections(story)
    _validate_pacing(story)
    _validate_opening(story)
    return story


def _validate_opening(story: CompiledStory) -> None:
    if story.opening is None:
        return
    character_ids = {character.id for character in story.characters}
    for contact in story.opening.contacts:
        if contact.id not in character_ids:
            raise CompilationError("OPENING_CONTACT_UNKNOWN", f"opening contact '{contact.id}' is not in the cast")
        if contact.location != story.initial_world_state.get("location"):
            raise CompilationError(
                "OPENING_CONTACT_OFF_SCENE", f"opening contact '{contact.id}' is not at the opening location"
            )
    protected_text = " ".join(revelation.summary for revelation in story.protected_revelations).casefold()
    opening_text = " ".join(
        (
            story.opening.scene,
            story.opening.protagonist_context,
            story.opening.arrival_context,
            *story.opening.public_briefing,
            story.opening.scene_purpose,
            *story.opening.first_available_actions,
        )
    ).casefold()
    if protected_text and any(
        summary.casefold() in opening_text for summary in (r.summary for r in story.protected_revelations)
    ):
        raise CompilationError("OPENING_PROTECTED_FACT", "opening metadata discloses a protected revelation")


class CompiledStoryCompiler:
    def __init__(self, transport: CompilerTransport | None, fixture_root: Path | None = None) -> None:
        self._transport = transport
        self._fixture_root = fixture_root or Path("data/compiled_stories/v1")

    def compile(self, outline: str, genre_profile: Mapping[str, object]) -> CompiledStory:
        if self._transport is None:
            raise CompilationError("COMPILER_TRANSPORT_UNAVAILABLE", "an injected compiler transport is required")
        response = self._transport.generate(build_compiler_prompt(outline, genre_profile))
        if isinstance(response, str):
            try:
                payload = json.loads(response)
            except json.JSONDecodeError as exc:
                raise CompilationError("COMPILER_OUTPUT_INVALID", "compiler response is not JSON") from exc
        else:
            payload = dict(response)
        if not isinstance(payload, dict):
            raise CompilationError("COMPILER_OUTPUT_INVALID", "compiler response must be a JSON object")
        return validate_compiled_story(payload)

    def compile_live(self, outline: str, genre_profile: Mapping[str, object]) -> CompiledStory:
        if os.getenv("FREYTAG_ENABLE_LIVE_COMPILER") != "1":
            raise CompilationError("LIVE_COMPILATION_DISABLED", "set FREYTAG_ENABLE_LIVE_COMPILER=1 to use a model")
        return self.compile(outline, genre_profile)


def load_compiled_story_fixture(genre: str, root: Path | None = None) -> CompiledStory:
    fixture_root = root or Path("data/compiled_stories/v1")
    if root is None:
        approved = _approved_fixture_path(genre)
        if approved is not None:
            return _load_reviewed_blueprint(approved)
    path = fixture_root / f"{genre}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompilationError("FIXTURE_NOT_FOUND", f"compiled fixture '{genre}' does not exist") from exc
    except json.JSONDecodeError as exc:
        raise CompilationError("FIXTURE_INVALID", f"compiled fixture '{genre}' is not JSON") from exc
    return validate_compiled_story(payload)


def _approved_fixture_path(genre: str) -> Path | None:
    manifest_path = Path("data/compiled_stories/v2/runtime-fixtures.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None
    except json.JSONDecodeError as exc:
        raise CompilationError("FIXTURE_MAP_INVALID", "approved runtime fixture map is not JSON") from exc
    if not isinstance(manifest, dict) or manifest.get("schema_version") != "runtime-fixture-map-v1":
        raise CompilationError("FIXTURE_MAP_INVALID", "approved runtime fixture map has an unsupported schema")
    fixtures = manifest.get("fixtures")
    filename = fixtures.get(genre) if isinstance(fixtures, dict) else None
    if filename is None:
        return None
    if not isinstance(filename, str) or Path(filename).name != filename or not filename.endswith(".reviewed.json"):
        raise CompilationError("FIXTURE_MAP_INVALID", f"approved fixture mapping for '{genre}' is invalid")
    return manifest_path.parent / filename


def _load_reviewed_blueprint(path: Path) -> CompiledStory:
    from storygame.authoring.candidate_review import ReviewedCausalStory
    from storygame.authoring.causal_contracts import CausalValidationError, validate_causal_compiled_story
    from storygame.authoring.causal_profiles import CausalProfileRegistry

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        reviewed = ReviewedCausalStory.model_validate(payload)
    except FileNotFoundError as exc:
        raise CompilationError("FIXTURE_NOT_FOUND", f"approved fixture '{path.name}' does not exist") from exc
    except (json.JSONDecodeError, ValidationError) as exc:
        raise CompilationError("FIXTURE_INVALID", f"approved fixture '{path.name}' is invalid") from exc
    if not reviewed.review.approved:
        raise CompilationError("FIXTURE_NOT_APPROVED", f"approved fixture '{path.name}' lacks approval")
    try:
        story = validate_causal_compiled_story(reviewed.story)
        CausalProfileRegistry.from_directory(Path("data/genre_profiles")).validate(story)
    except CausalValidationError as exc:
        raise CompilationError("FIXTURE_INVALID", f"approved fixture '{path.name}' failed causal validation") from exc
    return _causal_story_as_compiled_story(story)


def _causal_story_as_compiled_story(story: object) -> CompiledStory:
    truths = {truth.id: truth for truth in story.truths}
    participants = tuple(
        Character(
            id=participant.id,
            name=participant.id.replace("_", " ").title(),
            role=participant.role,
            description=f"Story participant with role: {participant.role}.",
        )
        for participant in story.participants
    )
    beats: list[Beat] = []
    for index, declaration in enumerate(story.required_beats):
        prerequisites = (story.required_beats[index - 1].id,) if index else ()
        tag_id = f"{declaration.id}_completed"
        beats.append(
            Beat(
                id=declaration.id,
                phase=declaration.phase,
                summary=f"Advance the declared {declaration.phase.replace('_', ' ')} beat.",
                prerequisites=prerequisites,
                completion_tags=(CompletionTag(id=tag_id, description=f"The '{declaration.id}' beat is complete."),),
                pacing=BeatPacing(nudge_after=2, advance_after=4, escalate_after=6, force_consequence_after=8),
                answers_central_question=declaration.phase == "resolution",
            )
        )
    beat_tags = {beat.id: beat.completion_tags[0].id for beat in beats}
    protected = tuple(
        ProtectedRevelation(
            id=f"protected_{protection.truth_id}",
            summary=truths[protection.truth_id].summary,
            reveal_after=tuple(
                beat_tags[beat_id]
                for revelation_id in protection.release_after_revelation_ids
                for revelation in story.revelations
                if revelation.id == revelation_id
                for beat_id in revelation.gate_beat_ids
                if beat_id in beat_tags
            ),
        )
        for protection in story.knowledge_protections
    )
    if any(not revelation.reveal_after for revelation in protected):
        raise CompilationError("FIXTURE_INVALID", "approved fixture has a protected truth without a runtime release")
    location = next((item.id for item in story.locations if item.initial_access), "opening")
    opening_locations = {item.id: item for item in story.locations if item.initial_access}
    routes_from_opening = [route for route in story.connected_routes if route.from_location_id == location]
    projected = CompiledStory(
        schema_version="compiled-story-v1",
        id=story.id,
        version=story.version,
        genre=story.genre,
        title=story.title,
        premise=story.premise,
        central_question=f"How does the story resolve its central situation? {story.premise}"[:500],
        opening=OpeningMetadata(
            scene=story.opening.scene if story.opening is not None else "The opening scene.",
            protagonist_context=(
                story.opening.protagonist_context or story.opening.player_context
                if story.opening is not None
                else "You have just arrived to begin the story."
            ),
            arrival_context=(
                story.opening.arrival_context or story.opening.player_context
                if story.opening is not None
                else "You have just arrived at the opening location."
            ),
            public_briefing=(
                story.opening.public_briefing or (story.opening.situation,)
                if story.opening is not None
                else (story.premise,)
            ),
            scene_purpose=(
                story.opening.scene_purpose or story.opening.situation
                if story.opening is not None
                else "Establish the situation and its first choice."
            ),
            first_available_actions=(
                story.opening.first_available_actions or story.opening.next_steps
                if story.opening is not None
                else ("Investigate the opening situation.",)
            ),
        ),
        initial_world_state={
            "location": location,
            "flags": list(story.opening_truth_ids),
            "premise": story.premise,
            "opening_truth_ids": list(story.opening_truth_ids),
            "opening_context": {
                "premise": story.premise,
                "public_facts": [truths[truth_id].summary for truth_id in story.opening_truth_ids],
                "current_location": location,
                "location_purpose": (
                    opening_locations[location].role if location in opening_locations else "opening scene"
                ),
                "figures": [participant.id.replace("_", " ").title() for participant in story.participants],
                "available_destinations": [
                    route.aliases[0] if route.aliases else route.to_location_id.replace("_", " ")
                    for route in routes_from_opening
                ],
                "first_beat": (
                    "Investigate the opening situation, speak with relevant people, and choose an available lead."
                ),
                **(story.opening.model_dump(mode="json") if story.opening is not None else {}),
            },
            "navigation": {
                "names": {item.id: item.id.replace("_", " ").title() for item in story.locations},
                "routes": [
                    {
                        "from": route.from_location_id,
                        "to": route.to_location_id,
                        "aliases": list(route.aliases),
                        "prerequisite_truths": list(route.prerequisite_truths),
                    }
                    for route in story.connected_routes
                ],
            },
        },
        characters=participants,
        beats=tuple(beats),
        protected_revelations=protected,
    )
    return validate_compiled_story(projected)

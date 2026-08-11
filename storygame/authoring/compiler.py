"""Local validation and opt-in model compilation for immutable V2 stories."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol

from pydantic import ValidationError

from storygame.authoring.contracts import CompiledStory
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
    return story


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
    path = fixture_root / f"{genre}.json"
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompilationError("FIXTURE_NOT_FOUND", f"compiled fixture '{genre}' does not exist") from exc
    except json.JSONDecodeError as exc:
        raise CompilationError("FIXTURE_INVALID", f"compiled fixture '{genre}' is not JSON") from exc
    return validate_compiled_story(payload)

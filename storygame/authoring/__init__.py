"""Offline V2 story authoring contracts and compiler boundary."""

from storygame.authoring.blueprint_contracts import (
    BlueprintValidationError,
    CanonicalTruth,
    DramaticBeat,
    EndState,
    FailureForward,
    OppositionClock,
    ProtectedFact,
    RealizationRoute,
    Revelation,
    RouteSatisfier,
    SourceOutlineProvenance,
    StoryBlueprint,
    load_story_blueprint_fixture,
    validate_story_blueprint,
)
from storygame.authoring.blueprint_migration import compiled_story_as_blueprint
from storygame.authoring.compiler import CompilationError, CompiledStoryCompiler, validate_compiled_story
from storygame.authoring.contracts import Beat, BeatPacing, Character, CompiledStory, CompletionTag, ProtectedRevelation

__all__ = [
    "Beat",
    "BeatPacing",
    "BlueprintValidationError",
    "CanonicalTruth",
    "Character",
    "CompilationError",
    "CompiledStory",
    "CompiledStoryCompiler",
    "compiled_story_as_blueprint",
    "CompletionTag",
    "DramaticBeat",
    "EndState",
    "FailureForward",
    "load_story_blueprint_fixture",
    "OppositionClock",
    "ProtectedRevelation",
    "ProtectedFact",
    "RealizationRoute",
    "Revelation",
    "RouteSatisfier",
    "SourceOutlineProvenance",
    "StoryBlueprint",
    "validate_compiled_story",
    "validate_story_blueprint",
]

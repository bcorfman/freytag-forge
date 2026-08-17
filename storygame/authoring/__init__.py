"""Offline V2 compiled-story authoring boundary."""

from storygame.authoring.causal_contracts import (
    CausalCompiledStory,
    CausalValidationError,
    validate_causal_compiled_story,
)
from storygame.authoring.causal_critics import CausalCompletenessCritic, FreytagProgressionCritic, RouteFairnessCritic
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError, CompiledStoryCompiler, validate_compiled_story
from storygame.authoring.contracts import Beat, BeatPacing, Character, CompiledStory, CompletionTag, ProtectedRevelation
from storygame.authoring.sources import NormalizedStorySource, StoryBrief, StorySourceLoader

__all__ = [
    "Beat",
    "BeatPacing",
    "Character",
    "CausalCompiledStory",
    "CausalCompletenessCritic",
    "CausalProfileRegistry",
    "CausalValidationError",
    "CompilationError",
    "CompiledStory",
    "CompiledStoryCompiler",
    "CompletionTag",
    "ProtectedRevelation",
    "NormalizedStorySource",
    "StoryBrief",
    "StorySourceLoader",
    "FreytagProgressionCritic",
    "RouteFairnessCritic",
    "validate_causal_compiled_story",
    "validate_compiled_story",
]

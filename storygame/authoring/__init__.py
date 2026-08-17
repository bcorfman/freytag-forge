"""Offline V2 compiled-story authoring boundary."""

from storygame.authoring.compiler import CompilationError, CompiledStoryCompiler, validate_compiled_story
from storygame.authoring.contracts import Beat, BeatPacing, Character, CompiledStory, CompletionTag, ProtectedRevelation
from storygame.authoring.sources import NormalizedStorySource, StoryBrief, StorySourceLoader

__all__ = [
    "Beat",
    "BeatPacing",
    "Character",
    "CompilationError",
    "CompiledStory",
    "CompiledStoryCompiler",
    "CompletionTag",
    "ProtectedRevelation",
    "NormalizedStorySource",
    "StoryBrief",
    "StorySourceLoader",
    "validate_compiled_story",
]

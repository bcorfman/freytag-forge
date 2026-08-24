"""Stable compiler model-tier policy for OpenAI-backed authoring."""

from __future__ import annotations

from typing import Literal

from storygame.authoring.compiler import CompilationError

CompilerQualityTier = Literal["preferred", "minimum"]

_MODELS: dict[CompilerQualityTier, str] = {
    "preferred": "gpt-5.6-sol",
    "minimum": "gpt-5.6-terra",
}
_REASONING_EFFORT = "high"


def resolve_compiler_model(quality_tier: str | None, *, debug: bool = False) -> tuple[str, str]:
    """Resolve one reviewed-authoring quality tier into a model and effort."""

    if debug:
        if quality_tier is not None:
            raise CompilationError("COMPILER_MODE_SELECTION_INVALID", "--debug cannot be combined with --quality-tier")
        return "gpt-5.6-luna", "low"
    if quality_tier is None:
        raise CompilationError(
            "COMPILER_QUALITY_TIER_REQUIRED", "pass --quality-tier preferred or --quality-tier minimum"
        )
    if quality_tier not in _MODELS:
        raise CompilationError("COMPILER_QUALITY_TIER_INVALID", "quality tier must be one of: preferred, minimum")
    return _MODELS[quality_tier], _REASONING_EFFORT  # type: ignore[index]

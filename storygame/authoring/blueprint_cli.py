"""Operator command for writing a non-overwriting reviewed blueprint candidate."""

from __future__ import annotations

import argparse
import importlib
import json
from pathlib import Path
from typing import cast

import yaml

from storygame.authoring.blueprint_compiler import (
    BlueprintCompilationError,
    BlueprintCompiler,
    BlueprintCompilerTransport,
)
from storygame.authoring.genre_profiles import GenreProfileRegistry


def _selected_outline(path: Path, outline_id: str, genre: str) -> str:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    for story in payload.get("stories", []):
        if str(story.get("id")) == outline_id and story.get("genre") == genre:
            return str(story["outline"])
    raise BlueprintCompilationError("OUTLINE_NOT_FOUND", f"no {genre!r} outline with id {outline_id!r}")


def _transport(factory_path: str) -> BlueprintCompilerTransport:
    module_name, separator, attribute = factory_path.partition(":")
    if not separator or not module_name or not attribute:
        raise BlueprintCompilationError("TRANSPORT_FACTORY_INVALID", "use module.path:factory")
    factory = getattr(importlib.import_module(module_name), attribute)
    return cast(BlueprintCompilerTransport, factory())


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Compile one raw outline into a reviewed Story Blueprint candidate")
    parser.add_argument("--outline-id", required=True)
    parser.add_argument("--genre", required=True)
    parser.add_argument("--outlines", type=Path, default=Path("data/story_outlines.yaml"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--transport-factory",
        required=True,
        help="Injected live transport factory: module.path:factory",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Acknowledge that this command may make a paid model request",
    )
    args = parser.parse_args(argv)
    if not args.live:
        parser.error("--live is required; compilation never runs implicitly")
    if args.output.exists():
        parser.error(f"refusing to overwrite reviewed or candidate artifact: {args.output}")
    if args.output.suffix != ".json" or not args.output.name.endswith(".candidate.json"):
        parser.error("--output must end in .candidate.json so it cannot be mistaken for a reviewed fixture")
    outline = _selected_outline(args.outlines, args.outline_id, args.genre)
    compiler = BlueprintCompiler(_transport(args.transport_factory), GenreProfileRegistry.from_directory())
    result = compiler.compile_live(outline, genre=args.genre, source_outline_id=args.outline_id)
    if not result.accepted:
        raise BlueprintCompilationError(
            "BLUEPRINT_REVIEW_REJECTED",
            "; ".join(detail for report in result.provenance.critic_results for detail in report.diagnostics),
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {"blueprint": result.blueprint.model_dump(mode="json"), "provenance": result.provenance.__dict__},
            indent=2,
            sort_keys=True,
            default=lambda value: value.__dict__,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

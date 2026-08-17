"""Phase-0 offline source selector for future causal compilation."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path

from storygame.authoring.blueprint_compiler import BlueprintCompiler, BlueprintCompilerTransport
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.openai_transport import OpenAIBlueprintTransport, OpenAICompilerConfig
from storygame.authoring.sources import StorySourceLoader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-blueprint")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--outline-id")
    selection.add_argument("--story", type=Path)
    parser.add_argument("--inventory", type=Path, default=Path("data/story_outlines.yaml"))
    parser.add_argument("--profile-root", type=Path, default=Path("data/genre_profiles"))
    parser.add_argument("--live", action="store_true", help="acknowledge an offline paid provider request")
    provider = parser.add_mutually_exclusive_group()
    provider.add_argument("--provider", choices=("openai",))
    provider.add_argument("--transport-factory")
    parser.add_argument("--model")
    parser.add_argument("--output", type=Path)
    return parser


def select_source(args: argparse.Namespace) -> dict[str, object]:
    loader = StorySourceLoader(args.inventory, args.profile_root)
    source = loader.select_outline(args.outline_id) if args.outline_id else loader.load_brief(args.story)
    return source.model_dump(mode="json")


def _load_transport_factory(path: str) -> BlueprintCompilerTransport:
    module_name, separator, factory_name = path.partition(":")
    if not separator or not module_name or not factory_name:
        raise CompilationError("TRANSPORT_FACTORY_INVALID", "transport factory must be module.path:factory")
    try:
        factory = getattr(importlib.import_module(module_name), factory_name)
        transport = factory()
    except (AttributeError, ImportError, TypeError) as exc:
        raise CompilationError("TRANSPORT_FACTORY_INVALID", "transport factory could not be constructed") from exc
    if not callable(getattr(transport, "generate", None)):
        raise CompilationError("TRANSPORT_FACTORY_INVALID", "transport factory must return a blueprint transport")
    return transport


def _compile_candidate(args: argparse.Namespace) -> dict[str, object]:
    if not args.live:
        raise CompilationError("LIVE_COMPILATION_ACK_REQUIRED", "pass --live to make an offline provider request")
    if os.getenv("FREYTAG_ENABLE_LIVE_COMPILER") != "1":
        raise CompilationError("LIVE_COMPILATION_DISABLED", "set FREYTAG_ENABLE_LIVE_COMPILER=1 to compile")
    loader = StorySourceLoader(args.inventory, args.profile_root)
    source = loader.select_outline(args.outline_id) if args.outline_id else loader.load_brief(args.story)
    if args.provider == "openai":
        config = OpenAICompilerConfig.from_environment(model=args.model)
        transport: BlueprintCompilerTransport = OpenAIBlueprintTransport(config)
        provider, model = "openai", config.model
    elif args.transport_factory:
        if not args.model:
            raise CompilationError("OPENAI_MODEL_REQUIRED", "--model is required with --transport-factory")
        transport = _load_transport_factory(args.transport_factory)
        provider, model = "custom", args.model
    else:
        raise CompilationError("COMPILER_PROVIDER_REQUIRED", "select --provider openai or --transport-factory")
    compiler = BlueprintCompiler(
        transport, CausalProfileRegistry.from_directory(args.profile_root), provider=provider, model=model
    )
    compilation = compiler.compile(source)
    return compilation.model_dump(mode="json")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.provider or args.transport_factory or args.live:
            candidate = _compile_candidate(args)
            story = candidate.get("story")
            if not isinstance(story, dict) or not isinstance(story.get("id"), str):
                raise CompilationError("CANDIDATE_OUTPUT_INVALID", "candidate does not have a stable story ID")
            default_output = Path("data/story_blueprints/candidates") / f"{story['id']}.candidate.json"
            output = args.output or default_output
            if output.suffix != ".json" or not output.name.endswith(".candidate.json"):
                raise CompilationError("CANDIDATE_OUTPUT_INVALID", "candidate output must end in .candidate.json")
            output.parent.mkdir(parents=True, exist_ok=True)
            if output.exists():
                raise CompilationError(
                    "CANDIDATE_OUTPUT_EXISTS", "candidate artifacts never overwrite an existing file"
                )
            output.write_text(json.dumps(candidate, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            print(json.dumps({"candidate": str(output)}, sort_keys=True))
        else:
            print(json.dumps(select_source(args), sort_keys=True))
    except CompilationError as exc:
        raise SystemExit(str(exc)) from exc
    return 0

"""CLI for the authoring-only Phase 4 causal compiler evaluation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.cli import _load_transport_factory
from storygame.authoring.compiler import CompilationError
from storygame.authoring.evaluation import evaluate_corpus, write_evaluation
from storygame.authoring.model_tiers import resolve_compiler_model
from storygame.authoring.openai_transport import OpenAIBlueprintTransport, OpenAICompilerConfig
from storygame.authoring.sources import StorySourceLoader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-blueprint-evaluate")
    parser.add_argument("--inventory", type=Path, default=Path("data/story_outlines.yaml"))
    parser.add_argument("--profile-root", type=Path, default=Path("data/genre_profiles"))
    parser.add_argument("--baseline", type=Path, default=Path("data/story_blueprints/diagnostics/phase0-baseline.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="acknowledge the authoring-only provider run")
    parser.add_argument("--transport-factory", help="custom blueprint transport for tests or compatible endpoints")
    model_selection = parser.add_mutually_exclusive_group(required=True)
    model_selection.add_argument("--quality-tier", choices=("preferred", "minimum"))
    model_selection.add_argument("--debug", action="store_true")
    parser.add_argument("--timeout-seconds", type=float, help="finite timeout for each OpenAI request (default: 600)")
    background = parser.add_mutually_exclusive_group()
    background.add_argument(
        "--background", dest="background", action="store_true", help="poll the OpenAI Responses request"
    )
    background.add_argument(
        "--no-background", dest="background", action="store_false", help="do not poll a background Response"
    )
    parser.set_defaults(background=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.live:
        raise SystemExit("LIVE_COMPILATION_ACK_REQUIRED: pass --live to run the authoring evaluation")
    if os.getenv("FREYTAG_ENABLE_LIVE_COMPILER") != "1":
        raise SystemExit("LIVE_COMPILATION_DISABLED: set FREYTAG_ENABLE_LIVE_COMPILER=1 to evaluate")
    if args.transport_factory:

        def factory():
            return _load_transport_factory(args.transport_factory)

        provider, model = "custom", resolve_compiler_model(args.quality_tier, debug=args.debug)[0]
    else:
        config = OpenAICompilerConfig.from_environment(
            quality_tier=args.quality_tier,
            debug=args.debug,
            timeout_seconds=args.timeout_seconds,
            background=args.background,
        )

        def factory() -> OpenAIBlueprintTransport:
            return OpenAIBlueprintTransport(config)

        provider, model = "openai", config.model
    loader = StorySourceLoader(args.inventory, args.profile_root)
    report = evaluate_corpus(
        loader.list_outlines(),
        factory,
        CausalProfileRegistry.from_directory(args.profile_root),
        provider=provider,
        model=model,
        quality_tier=args.quality_tier,
        generation_mode="debug" if args.debug else "standard",
        baseline_path=args.baseline,
    )
    write_evaluation(args.output, report)
    print(f"evaluation: {args.output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except CompilationError as exc:
        raise SystemExit(str(exc)) from exc

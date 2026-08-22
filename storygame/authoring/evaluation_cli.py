"""CLI for the authoring-only Phase 4 causal compiler evaluation."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.cli import _load_transport_factory
from storygame.authoring.compiler import CompilationError
from storygame.authoring.evaluation import evaluate_corpus, write_evaluation
from storygame.authoring.openai_transport import OpenAIBlueprintTransport, OpenAICompilerConfig
from storygame.authoring.sources import StorySourceLoader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-blueprint-evaluate")
    parser.add_argument("--inventory", type=Path, default=Path("data/story_outlines.yaml"))
    parser.add_argument("--profile-root", type=Path, default=Path("data/genre_profiles"))
    parser.add_argument("--baseline", type=Path, default=Path("data/story_blueprints/diagnostics/phase0-baseline.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true", help="acknowledge the authoring-only provider run")
    provider = parser.add_mutually_exclusive_group(required=True)
    provider.add_argument("--provider", choices=("openai",))
    provider.add_argument("--transport-factory")
    parser.add_argument("--model")
    parser.add_argument("--timeout-seconds", type=float)
    parser.add_argument("--background", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.live:
        raise SystemExit("LIVE_COMPILATION_ACK_REQUIRED: pass --live to run the authoring evaluation")
    if os.getenv("FREYTAG_ENABLE_LIVE_COMPILER") != "1":
        raise SystemExit("LIVE_COMPILATION_DISABLED: set FREYTAG_ENABLE_LIVE_COMPILER=1 to evaluate")
    if args.provider == "openai":
        config = OpenAICompilerConfig.from_environment(
            model=args.model, timeout_seconds=args.timeout_seconds, background=args.background
        )

        def factory() -> OpenAIBlueprintTransport:
            return OpenAIBlueprintTransport(config)

        provider, model = "openai", config.model
    else:
        if not args.model:
            raise SystemExit("OPENAI_MODEL_REQUIRED: --model is required with --transport-factory")

        def factory():
            return _load_transport_factory(args.transport_factory)

        provider, model = "custom", args.model
    loader = StorySourceLoader(args.inventory, args.profile_root)
    report = evaluate_corpus(
        loader.list_outlines(),
        factory,
        CausalProfileRegistry.from_directory(args.profile_root),
        provider=provider,
        model=model,
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

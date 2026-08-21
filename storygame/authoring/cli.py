"""Phase-0 offline source selector for future causal compilation."""

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path

from storygame.authoring.blueprint_compiler import (
    BlueprintCompilationExhausted,
    BlueprintCompiler,
    BlueprintCompilerTransport,
)
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.openai_transport import OpenAIBlueprintTransport, OpenAICompilerConfig
from storygame.authoring.sources import NormalizedStorySource, StorySourceLoader


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="storygame-blueprint")
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--outline-id")
    selection.add_argument("--story", type=Path)
    selection.add_argument("--replay-diagnostic", type=Path, help="replay one diagnostic artifact without a provider")
    parser.add_argument("--inventory", type=Path, default=Path("data/story_outlines.yaml"))
    parser.add_argument("--profile-root", type=Path, default=Path("data/genre_profiles"))
    parser.add_argument("--live", action="store_true", help="acknowledge an offline paid provider request")
    provider = parser.add_mutually_exclusive_group()
    provider.add_argument("--provider", choices=("openai",))
    provider.add_argument("--transport-factory")
    parser.add_argument("--model")
    parser.add_argument("--timeout-seconds", type=float, help="finite timeout for each OpenAI request")
    parser.add_argument("--background", action="store_true", help="poll a long-running OpenAI Responses request")
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--diagnostic-output", type=Path, help="write raw exhausted attempts as a non-playable diagnostic artifact"
    )
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
        config = OpenAICompilerConfig.from_environment(
            model=args.model, timeout_seconds=args.timeout_seconds, background=args.background
        )
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


def _write_diagnostic(path: Path, artifact: dict[str, object]) -> None:
    if path.suffix != ".json" or not path.name.endswith(".diagnostic.json"):
        raise CompilationError("DIAGNOSTIC_OUTPUT_INVALID", "diagnostic output must end in .diagnostic.json")
    if path.exists():
        raise CompilationError("DIAGNOSTIC_OUTPUT_EXISTS", "diagnostic artifacts never overwrite an existing file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")


class _DiagnosticReplayTransport:
    def __init__(self, attempts: list[object]) -> None:
        self._attempts = list(attempts)

    def generate(self, prompt: str, *, json_object: bool) -> str:
        if not self._attempts:
            raise CompilationError("DIAGNOSTIC_REPLAY_INVALID", "diagnostic has no response for this compiler request")
        attempt = self._attempts.pop(0)
        if not isinstance(attempt, dict) or attempt.get("json_object") is not json_object:
            raise CompilationError(
                "DIAGNOSTIC_REPLAY_INVALID", "diagnostic request sequence does not match the compiler"
            )
        response = attempt.get("response")
        if isinstance(response, str):
            return response
        error_code = attempt.get("error_code")
        error_detail = attempt.get("error_detail")
        if isinstance(error_code, str) and isinstance(error_detail, str):
            raise CompilationError(error_code, error_detail)
        raise CompilationError("DIAGNOSTIC_REPLAY_INVALID", "diagnostic response is unavailable")


def _replay_diagnostic(path: Path, profile_root: Path) -> dict[str, object]:
    try:
        artifact = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise CompilationError("DIAGNOSTIC_NOT_FOUND", f"diagnostic '{path.name}' does not exist") from exc
    except json.JSONDecodeError as exc:
        raise CompilationError("DIAGNOSTIC_INVALID", f"diagnostic '{path.name}' is not JSON") from exc
    if not isinstance(artifact, dict) or artifact.get("schema_version") != "story-blueprint-diagnostic-v1":
        raise CompilationError("DIAGNOSTIC_INVALID", "diagnostic has an unsupported schema version")
    source_payload = artifact.get("source")
    attempts = artifact.get("attempts")
    provider = artifact.get("provider")
    model = artifact.get("model")
    if not isinstance(source_payload, dict) or not isinstance(attempts, list):
        raise CompilationError("DIAGNOSTIC_INVALID", "diagnostic is missing source or attempts")
    if not isinstance(provider, str) or not isinstance(model, str):
        raise CompilationError("DIAGNOSTIC_INVALID", "diagnostic is missing provider or model")
    try:
        source = NormalizedStorySource.model_validate(source_payload)
    except ValueError as exc:
        raise CompilationError("DIAGNOSTIC_INVALID", "diagnostic source is invalid") from exc
    compilation = BlueprintCompiler(
        _DiagnosticReplayTransport(attempts),
        CausalProfileRegistry.from_directory(profile_root),
        provider=provider,
        model=model,
    ).compile(source)
    return compilation.model_dump(mode="json")


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.replay_diagnostic:
            replay = _replay_diagnostic(args.replay_diagnostic, args.profile_root)
            print(
                json.dumps({"replay": "accepted", "validation_results": replay["validation_results"]}, sort_keys=True)
            )
            return 0
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
    except BlueprintCompilationExhausted as exc:
        if args.diagnostic_output:
            _write_diagnostic(args.diagnostic_output, exc.diagnostic_artifact())
            raise SystemExit(f"{exc} (diagnostic saved: {args.diagnostic_output})") from exc
        raise SystemExit(str(exc)) from exc
    except CompilationError as exc:
        raise SystemExit(str(exc)) from exc
    return 0

"""Authoring-only Phase 4 evaluation for the causal blueprint compiler."""

from __future__ import annotations

import json
from collections import Counter
from collections.abc import Sequence
from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from storygame.authoring.blueprint_compiler import (
    BlueprintCompilationExhausted,
    BlueprintCompiler,
    BlueprintCompilerTransport,
)
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from storygame.authoring.repair_context import structural_diff
from storygame.authoring.sources import NormalizedStorySource


class _Baseline(BaseModel):
    model_config = ConfigDict(frozen=True, extra="allow")

    schema_version: str
    cases: dict[str, dict[str, object]] = Field(default_factory=dict)


class Phase4Case(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    genre: str
    accepted: bool = False
    first_pass_accepted: bool = False
    repair_accepted: bool = False
    request_count: int = 0
    diagnostic_codes: tuple[str, ...] = ()
    structural_diff: tuple[str, ...] = ()
    error_code: str | None = None


class Phase4Summary(BaseModel):
    model_config = ConfigDict(frozen=True)

    cases: int = 0
    accepted: int = 0
    first_pass_acceptance: int = 0
    repair_attempts: int = 0
    repair_acceptance: int = 0
    budget_exhaustions: int = 0
    diagnostic_categories: dict[str, int] = Field(default_factory=dict)


class Phase4Comparison(BaseModel):
    model_config = ConfigDict(frozen=True)

    baseline_first_pass_acceptance: int = 0
    baseline_repair_attempts: int = 0
    baseline_budget_exhaustions: int = 0
    baseline_diagnostic_categories: dict[str, int] = Field(default_factory=dict)


class Phase4Evaluation(BaseModel):
    """Immutable evidence from an authoring run; never a playable artifact."""

    model_config = ConfigDict(frozen=True)

    schema_version: str
    provider: str = ""
    model: str = ""
    cases: tuple[Phase4Case, ...] = ()
    summary: Phase4Summary = Phase4Summary()
    baseline: _Baseline = _Baseline(schema_version="story-blueprint-phase0-baseline-v1")
    comparison: Phase4Comparison = Phase4Comparison()


class _Factory(Protocol):
    def __call__(self) -> BlueprintCompilerTransport: ...


def evaluate_corpus(
    sources: Sequence[NormalizedStorySource],
    transport_factory: _Factory,
    profiles: CausalProfileRegistry,
    *,
    provider: str,
    model: str,
    baseline_path: Path = Path("data/story_blueprints/diagnostics/phase0-baseline.json"),
) -> Phase4Evaluation:
    """Compile every source through the normal bounded provider path."""

    baseline = _load_baseline(baseline_path)
    cases = tuple(
        _evaluate_source(source, transport_factory, profiles, provider=provider, model=model) for source in sources
    )
    return Phase4Evaluation(
        schema_version="causal-compiler-phase4-evaluation-v1",
        provider=provider,
        model=model,
        cases=cases,
        summary=_summary(cases),
        baseline=baseline,
        comparison=_compare_baseline(baseline),
    )


def write_evaluation(path: Path, report: Phase4Evaluation) -> None:
    """Write one immutable evidence artifact, never a candidate or runtime input."""

    if path.suffix != ".json" or not path.name.endswith(".evaluation.json"):
        raise CompilationError("EVALUATION_OUTPUT_INVALID", "evaluation output must end in .evaluation.json")
    if path.exists():
        raise CompilationError("EVALUATION_OUTPUT_EXISTS", "evaluation artifacts never overwrite an existing file")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def _evaluate_source(
    source: NormalizedStorySource,
    transport_factory: _Factory,
    profiles: CausalProfileRegistry,
    *,
    provider: str,
    model: str,
) -> Phase4Case:
    transport = transport_factory()
    responses: list[object] = []
    compiler = BlueprintCompiler(_RecordingTransport(transport, responses), profiles, provider=provider, model=model)
    try:
        compilation = compiler.compile(source)
    except BlueprintCompilationExhausted as exc:
        return Phase4Case(
            source_id=source.source_id,
            genre=source.genre,
            request_count=len(exc.attempts),
            diagnostic_codes=(exc.code,),
            error_code=exc.code,
        )
    except CompilationError as exc:
        return Phase4Case(
            source_id=source.source_id,
            genre=source.genre,
            diagnostic_codes=(exc.code,),
            error_code=exc.code,
        )
    diffs = _repair_diff(responses)
    diagnostics = tuple(item.code for item in compilation.diagnostics)
    repaired = compilation.request_count > 1
    return Phase4Case(
        source_id=source.source_id,
        genre=source.genre,
        accepted=compilation.accepted,
        first_pass_accepted=compilation.accepted and not repaired,
        repair_accepted=compilation.accepted and repaired,
        request_count=compilation.request_count,
        diagnostic_codes=diagnostics,
        structural_diff=diffs,
    )


class _RecordingTransport:
    def __init__(self, delegate: BlueprintCompilerTransport, responses: list[object]) -> None:
        self._delegate = delegate
        self._responses = responses

    def generate(self, prompt: str, *, json_object: bool) -> str | dict[str, object]:
        try:
            response = self._delegate.generate(prompt, json_object=json_object)
        except CompilationError:
            raise
        self._responses.append(response)
        return response


def _repair_diff(responses: Sequence[object]) -> tuple[str, ...]:
    if len(responses) < 2:
        return ()
    return structural_diff(responses[0], responses[1]).render()


def _summary(cases: Sequence[Phase4Case]) -> Phase4Summary:
    categories = Counter(code for case in cases for code in case.diagnostic_codes)
    return Phase4Summary(
        cases=len(cases),
        accepted=sum(case.accepted for case in cases),
        first_pass_acceptance=sum(case.first_pass_accepted for case in cases),
        repair_attempts=sum(case.request_count > 1 for case in cases),
        repair_acceptance=sum(case.repair_accepted for case in cases),
        budget_exhaustions=sum(case.error_code == "BLUEPRINT_COMPILATION_EXHAUSTED" for case in cases),
        diagnostic_categories=dict(sorted(categories.items())),
    )


def _load_baseline(path: Path) -> _Baseline:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return _Baseline.model_validate(payload)
    except (FileNotFoundError, json.JSONDecodeError, ValueError) as exc:
        raise CompilationError("EVALUATION_BASELINE_INVALID", "Phase 0 baseline is unavailable or invalid") from exc


def _compare_baseline(baseline: _Baseline) -> Phase4Comparison:
    cases = tuple(baseline.cases.values())
    categories = Counter(code for case in cases for code in case.get("diagnostics", ()) if isinstance(code, str))
    request_counts = tuple(count for case in cases if isinstance((count := case.get("request_count")), int))
    return Phase4Comparison(
        baseline_first_pass_acceptance=sum(
            case.get("request_count") == 1 and not case.get("diagnostics") for case in cases
        ),
        baseline_repair_attempts=sum(count > 1 for count in request_counts),
        baseline_budget_exhaustions=sum(count > 2 for count in request_counts),
        baseline_diagnostic_categories=dict(sorted(categories.items())),
    )

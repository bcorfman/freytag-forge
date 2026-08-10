"""Deterministic fixtures and artifact-based checks for behavioral evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal, Protocol, TypedDict, cast

import yaml

FailureCategory = Literal[
    "contradiction",
    "impossible_action",
    "hidden_information_leak",
    "role_drift",
    "causal_omission",
    "uncommitted_narration",
    "exhausted_provider_recovery",
    "repetitive_scene_pressure",
    "blocked_player_agency",
]

FAILURE_CATEGORIES: tuple[FailureCategory, ...] = (
    "contradiction",
    "impossible_action",
    "hidden_information_leak",
    "role_drift",
    "causal_omission",
    "uncommitted_narration",
    "exhausted_provider_recovery",
    "repetitive_scene_pressure",
    "blocked_player_agency",
)

INFORMATIONAL_DIRECT_OR_REPAIRED_SLO = 0.95


class GenerationSettings(TypedDict):
    temperature: int | float
    max_tokens: int


class EvaluationFixture(TypedDict):
    id: str
    genre: str
    tone: str
    session_length: str
    seed: int
    model: str
    prompt_version: str
    generation_settings: GenerationSettings
    commands: list[str]


class AdapterRevisions(TypedDict):
    openai: str
    ollama: str
    cloudflare_workers_ai: str


class AdapterMeasurement(TypedDict):
    """One ordinary-turn observation from a frozen evaluation fixture."""

    adapter: str
    revision: str
    proposal_valid: bool
    directly_accepted: bool
    repaired: bool
    repair_succeeded: bool
    failure_categories: tuple[FailureCategory, ...]
    latency_ms: int | float
    input_tokens: int
    output_tokens: int


class AdapterBaseline(TypedDict):
    revision: str
    turns: int
    proposal_validity: float
    direct_acceptance: float
    bounded_repair_success: float
    hidden_information_leaks: int
    role_drift: int
    latency_ms: float
    input_tokens: int
    output_tokens: int


class RuntimeQualityAdapterBaseline(AdapterBaseline):
    direct_or_one_repair_validation_rate: float
    protected_information_leaks: int
    uncommitted_state: int


class RuntimeQualitySlo(TypedDict):
    name: Literal["direct_or_one_repair_validation_rate"]
    target: float
    enforced: Literal[False]


class RuntimeQualityReport(TypedDict):
    kind: Literal["informational_runtime_quality"]
    adapters: dict[str, RuntimeQualityAdapterBaseline]
    missing_adapters: tuple[str, ...]
    slo: RuntimeQualitySlo


class RuntimeQualityRegression(TypedDict):
    id: str
    accepted: bool
    failure_categories: tuple[FailureCategory, ...]


class AdapterMeasurementReport(TypedDict):
    kind: Literal["informational_baseline"]
    adapters: dict[str, AdapterBaseline]
    missing_adapters: tuple[str, ...]


class FixturePackageFactory(Protocol):
    def build(self, fixture: Mapping[str, object]) -> dict[str, Any]: ...


class FixtureScriptedPlayer(Protocol):
    def play(self, package: dict[str, Any], style: str) -> dict[str, object]: ...


def _fixtures_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "evaluation_fixtures.yaml"


def _runtime_quality_regressions_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "runtime_quality_regressions.yaml"


def _require_string(payload: Mapping[str, object], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Evaluation fixture requires a non-empty '{key}'.")
    return value


def _load_fixture(raw: object) -> EvaluationFixture:
    if not isinstance(raw, Mapping):
        raise ValueError("Evaluation fixtures must be mappings.")
    seed = raw.get("seed")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise ValueError("Evaluation fixture requires an integer 'seed'.")
    commands = raw.get("commands")
    valid_commands = (
        isinstance(commands, list) and commands and all(isinstance(command, str) and command for command in commands)
    )
    if not valid_commands:
        raise ValueError("Evaluation fixture requires one or more string commands.")
    settings = raw.get("generation_settings")
    if not isinstance(settings, Mapping):
        raise ValueError("Evaluation fixture requires 'generation_settings'.")
    temperature = settings.get("temperature")
    max_tokens = settings.get("max_tokens")
    if not isinstance(temperature, int | float) or isinstance(temperature, bool):
        raise ValueError("Evaluation fixture requires numeric generation_settings.temperature.")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise ValueError("Evaluation fixture requires positive generation_settings.max_tokens.")
    return {
        "id": _require_string(raw, "id"),
        "genre": _require_string(raw, "genre"),
        "tone": _require_string(raw, "tone"),
        "session_length": _require_string(raw, "session_length"),
        "seed": seed,
        "model": _require_string(raw, "model"),
        "prompt_version": _require_string(raw, "prompt_version"),
        "generation_settings": {"temperature": temperature, "max_tokens": max_tokens},
        "commands": list(cast(list[str], commands)),
    }


def load_evaluation_fixtures(path: Path | None = None) -> tuple[EvaluationFixture, ...]:
    """Load the frozen Phase 0 fixture inputs used by repeatable evaluation."""
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    payload = yaml.load((path or _fixtures_path()).read_text(encoding="utf-8"), Loader=loader)
    if not isinstance(payload, Mapping) or payload.get("version") != "phase0-v1":
        raise ValueError("Unsupported evaluation fixture version.")
    raw_fixtures = payload.get("fixtures")
    if not isinstance(raw_fixtures, list):
        raise ValueError("Evaluation fixture payload requires a 'fixtures' list.")
    fixtures = tuple(_load_fixture(raw) for raw in raw_fixtures)
    fixture_ids = [fixture["id"] for fixture in fixtures]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("Evaluation fixture ids must be unique.")
    return fixtures


def load_evaluation_adapter_revisions(path: Path | None = None) -> AdapterRevisions:
    """Load the fixed ordinary-runtime adapter protocol revisions."""
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    payload = yaml.load((path or _fixtures_path()).read_text(encoding="utf-8"), Loader=loader)
    if not isinstance(payload, Mapping):
        raise ValueError("Evaluation fixture payload must be a mapping.")
    raw_revisions = payload.get("adapter_revisions")
    required = ("openai", "ollama", "cloudflare_workers_ai")
    if not isinstance(raw_revisions, Mapping):
        raise ValueError("Evaluation fixture payload requires adapter_revisions.")
    revisions = {adapter: _require_string(raw_revisions, adapter) for adapter in required}
    return cast(AdapterRevisions, revisions)


def classify_structured_artifact(artifact: Mapping[str, object]) -> tuple[FailureCategory, ...]:
    """Classify deterministic artifact signals without interpreting player-facing prose."""
    categories: list[FailureCategory] = []
    if "contradiction" in _strings(artifact, "invariant_violations"):
        categories.append("contradiction")
    if artifact.get("action_outcome") == "impossible":
        categories.append("impossible_action")
    if _strings(artifact, "knowledge_leaks"):
        categories.append("hidden_information_leak")
    if _strings(artifact, "role_violations"):
        categories.append("role_drift")
    if _strings(artifact, "causal_gaps"):
        categories.append("causal_omission")
    if set(_strings(artifact, "rendered_claims")) - set(_strings(artifact, "committed_claims")):
        categories.append("uncommitted_narration")
    provider_recovery = artifact.get("provider_recovery")
    if isinstance(provider_recovery, Mapping) and provider_recovery.get("exhausted") is True:
        categories.append("exhausted_provider_recovery")
    pressure = _strings(artifact, "scene_pressure")
    if len(pressure) >= 3 and len(set(pressure)) == 1:
        categories.append("repetitive_scene_pressure")
    if artifact.get("agency_outcome") == "blocked" and not artifact.get("clarification_requested"):
        categories.append("blocked_player_agency")
    return tuple(categories)


def summarize_adapter_measurements(
    measurements: tuple[AdapterMeasurement, ...],
    *,
    required_adapters: tuple[str, ...],
) -> AdapterMeasurementReport:
    """Aggregate frozen turn observations without turning a baseline into a gate."""
    grouped: dict[str, list[AdapterMeasurement]] = {}
    for measurement in measurements:
        grouped.setdefault(measurement["adapter"], []).append(measurement)
    baselines = {adapter: _adapter_baseline(adapter_measurements) for adapter, adapter_measurements in grouped.items()}
    return {
        "kind": "informational_baseline",
        "adapters": baselines,
        "missing_adapters": tuple(adapter for adapter in required_adapters if adapter not in baselines),
    }


def evaluate_frozen_adapter_matrix() -> RuntimeQualityReport:
    """Report deterministic ordinary-turn quality for every supported adapter.

    This is deliberately an offline, credential-free fixture run. It validates
    the evaluation contract and keeps a stable comparison baseline; live or
    paid provider experiments belong in explicitly configured follow-up jobs.
    """
    fixtures = load_evaluation_fixtures()
    revisions = load_evaluation_adapter_revisions()
    measurements = tuple(
        _frozen_measurement(adapter, revision, fixture)
        for adapter, revision in revisions.items()
        for fixture in fixtures
        for _command in fixture["commands"]
    )
    grouped: dict[str, list[AdapterMeasurement]] = {}
    for measurement in measurements:
        grouped.setdefault(measurement["adapter"], []).append(measurement)
    report = summarize_adapter_measurements(measurements, required_adapters=tuple(revisions))
    return {
        "kind": "informational_runtime_quality",
        "adapters": {
            adapter: _runtime_quality_baseline(baseline, grouped[adapter])
            for adapter, baseline in report["adapters"].items()
        },
        "missing_adapters": report["missing_adapters"],
        "slo": {
            "name": "direct_or_one_repair_validation_rate",
            "target": INFORMATIONAL_DIRECT_OR_REPAIRED_SLO,
            "enforced": False,
        },
    }


def load_runtime_quality_regressions(path: Path | None = None) -> tuple[RuntimeQualityRegression, ...]:
    """Load fail-closed runtime regressions as structured, prose-free fixtures."""
    loader = getattr(yaml, "CSafeLoader", yaml.SafeLoader)
    payload = yaml.load((path or _runtime_quality_regressions_path()).read_text(encoding="utf-8"), Loader=loader)
    if not isinstance(payload, Mapping) or payload.get("version") != "stage4-v1":
        raise ValueError("Unsupported runtime quality regression version.")
    raw_regressions = payload.get("regressions")
    if not isinstance(raw_regressions, list):
        raise ValueError("Runtime quality regressions require a 'regressions' list.")
    regressions = tuple(_load_runtime_quality_regression(raw) for raw in raw_regressions)
    if len({regression["id"] for regression in regressions}) != len(regressions):
        raise ValueError("Runtime quality regression ids must be unique.")
    return regressions


def _adapter_baseline(measurements: list[AdapterMeasurement]) -> AdapterBaseline:
    turns = len(measurements)
    if turns == 0:
        raise ValueError("Adapter baselines require at least one measurement.")
    revisions = {measurement["revision"] for measurement in measurements}
    if len(revisions) != 1:
        raise ValueError("Each adapter baseline must use one frozen revision.")
    repaired = [measurement for measurement in measurements if measurement["repaired"]]
    return {
        "revision": revisions.pop(),
        "turns": turns,
        "proposal_validity": _rate(measurements, "proposal_valid"),
        "direct_acceptance": _rate(measurements, "directly_accepted"),
        "bounded_repair_success": _rate(repaired, "repair_succeeded") if repaired else 0.0,
        "hidden_information_leaks": _failure_count(measurements, "hidden_information_leak"),
        "role_drift": _failure_count(measurements, "role_drift"),
        "latency_ms": sum(float(measurement["latency_ms"]) for measurement in measurements) / turns,
        "input_tokens": sum(measurement["input_tokens"] for measurement in measurements),
        "output_tokens": sum(measurement["output_tokens"] for measurement in measurements),
    }


def _runtime_quality_baseline(
    baseline: AdapterBaseline, measurements: list[AdapterMeasurement]
) -> RuntimeQualityAdapterBaseline:
    return {
        **baseline,
        "direct_or_one_repair_validation_rate": sum(
            measurement["directly_accepted"] or measurement["repair_succeeded"] for measurement in measurements
        )
        / len(measurements),
        "protected_information_leaks": baseline["hidden_information_leaks"],
        "uncommitted_state": _failure_count(measurements, "uncommitted_narration"),
    }


def _frozen_measurement(adapter: str, revision: str, fixture: EvaluationFixture) -> AdapterMeasurement:
    """Create the known-good deterministic observation for one frozen turn."""
    return {
        "adapter": adapter,
        "revision": revision,
        "proposal_valid": True,
        "directly_accepted": True,
        "repaired": False,
        "repair_succeeded": False,
        "failure_categories": (),
        "latency_ms": 0,
        "input_tokens": 0,
        "output_tokens": 0,
    }


def _load_runtime_quality_regression(raw: object) -> RuntimeQualityRegression:
    if not isinstance(raw, Mapping):
        raise ValueError("Runtime quality regression must be a mapping.")
    accepted = raw.get("accepted")
    if not isinstance(accepted, bool):
        raise ValueError("Runtime quality regression requires boolean 'accepted'.")
    categories = raw.get("failure_categories")
    if not isinstance(categories, list) or not categories:
        raise ValueError("Runtime quality regression requires failure_categories.")
    invalid_categories = [category for category in categories if category not in FAILURE_CATEGORIES]
    if invalid_categories:
        raise ValueError("Runtime quality regression contains an unsupported failure category.")
    return {
        "id": _require_string(raw, "id"),
        "accepted": accepted,
        "failure_categories": tuple(cast(FailureCategory, category) for category in categories),
    }


def _rate(
    measurements: list[AdapterMeasurement],
    key: Literal["proposal_valid", "directly_accepted", "repair_succeeded"],
) -> float:
    return sum(measurement[key] for measurement in measurements) / len(measurements)


def _failure_count(measurements: list[AdapterMeasurement], category: FailureCategory) -> int:
    return sum(category in measurement["failure_categories"] for measurement in measurements)


def evaluate_fixture_playability(
    package_factory: FixturePackageFactory,
    player: FixtureScriptedPlayer,
    fixtures: tuple[EvaluationFixture, ...] | None = None,
) -> dict[str, object]:
    """Run every required player style for each frozen evaluation fixture."""
    from storygame.story_packages import evaluate_package_playability

    results: dict[str, object] = {}
    for fixture in fixtures or load_evaluation_fixtures():
        results[fixture["id"]] = evaluate_package_playability(package_factory.build(fixture), player)
    return results


def _strings(artifact: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = artifact.get(key, ())
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(value for value in value if isinstance(value, str))

"""Offline story-package construction, validation, and playability evaluation.

Packages are authoring inputs.  This module deliberately never mutates a live
``GameState``: runtime realization remains fact-backed in ``engine.world``.
"""

from __future__ import annotations

from collections.abc import Mapping
from concurrent.futures import ThreadPoolExecutor
from time import perf_counter
from typing import Any, Protocol, TypedDict

from storygame.llm.coherence import DEFAULT_CRITICAL_FLOORS, DEFAULT_WEIGHTS, judge_critique_round
from storygame.llm.contracts import CritiqueReport, JudgeDecision, parse_critique_report

STORY_PACKAGE_SCHEMA_VERSION = "story-package-v1"
STORY_PACKAGE_RUBRIC_VERSION = "story-package-rubric-v1"
PLAY_STYLES = ("exploratory", "goal_focused", "social", "adversarial", "avoidant", "chaotic")
_REQUIRED_SPECIALISTS = frozenset({"continuity", "causality", "dialogue_fit"})


class StoryPackageValidationError(ValueError):
    """Raised when an authoring package cannot safely enter the runtime."""


class StoryPackageGenerator(Protocol):
    def generate(self, request: dict[str, object]) -> dict[str, Any]: ...


class StoryPackageCritic(Protocol):
    def critique(self, package: dict[str, Any]) -> dict[str, object]: ...


class StoryPackageRecoverer(Protocol):
    def recover(self, package: dict[str, Any], issues: tuple[str, ...]) -> dict[str, object]: ...


class ScriptedPlayer(Protocol):
    def play(self, package: dict[str, Any], style: str) -> dict[str, object]: ...


class RecoveryRecord(TypedDict):
    attempted: bool
    preserved_fact_categories: tuple[str, ...]
    modified_fact_categories: tuple[str, ...]
    discarded_fact_categories: tuple[str, ...]


class PackageEvaluation(TypedDict):
    rubric_version: str
    rounds: int
    token_usage: int
    elapsed_ms: int
    direct_validity: bool
    repair_rate: float
    contradiction_count: int
    leakage_count: int
    role_drift_count: int
    reports: tuple[CritiqueReport, ...]


class AuthoringResult(TypedDict):
    package: dict[str, Any]
    accepted: bool
    judge: JudgeDecision
    evaluation: PackageEvaluation
    recovery: RecoveryRecord


class PlayabilityRun(TypedDict):
    style: str
    ending_id: str
    artifact: dict[str, object]


class PlayabilityResult(TypedDict):
    passed: bool
    runs: tuple[PlayabilityRun, ...]


def _entries(package: Mapping[str, object], key: str) -> list[dict[str, Any]]:
    value = package.get(key, [])
    if not isinstance(value, list):
        raise StoryPackageValidationError(f"'{key}' must be a list.")
    if not all(isinstance(entry, Mapping) for entry in value):
        raise StoryPackageValidationError(f"'{key}' entries must be objects.")
    return [dict(entry) for entry in value]


def _ids(entries: list[dict[str, Any]], label: str) -> set[str]:
    identifiers = [str(entry.get("id", "")).strip() for entry in entries]
    if not all(identifiers) or len(identifiers) != len(set(identifiers)):
        raise StoryPackageValidationError(f"{label} require unique non-empty ids.")
    return set(identifiers)


def _strings(value: object, label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
        raise StoryPackageValidationError(f"'{label}' must be a list of non-empty strings.")
    return tuple(item.strip() for item in value)


def _require_reference(values: tuple[str, ...], known: set[str], label: str) -> None:
    missing = sorted(set(values) - known)
    if missing:
        raise StoryPackageValidationError(f"{label} references missing {', '.join(missing)}.")


def _validate_revelations(revelations: list[dict[str, Any]], secret_ids: set[str], clue_ids: set[str]) -> set[str]:
    revelation_ids = _ids(revelations, "Revelations")
    for revelation in revelations:
        revelation_id = str(revelation["id"])
        required_secrets = _strings(revelation.get("requires", []), f"revelation '{revelation_id}'.requires")
        _require_reference(required_secrets, secret_ids, "revelation")
        paths = revelation.get("acquisition_paths")
        if not isinstance(paths, list) or not paths:
            raise StoryPackageValidationError(f"revelation '{revelation_id}' requires an acquisition path.")
        normalized_paths: list[tuple[str, ...]] = []
        for path in paths:
            normalized_path = _strings(path, f"revelation '{revelation_id}'.acquisition_paths")
            _require_reference(normalized_path, clue_ids, "revelation path")
            normalized_paths.append(normalized_path)
        if revelation.get("resilient", False) and len({path for path in normalized_paths}) < 2:
            raise StoryPackageValidationError(f"resilient revelation '{revelation_id}' requires two distinct paths.")
    return revelation_ids


def validate_story_package(raw_package: Mapping[str, object]) -> dict[str, Any]:
    """Validate a generated package before it can be realized into canonical facts."""
    package = dict(raw_package)
    if package.get("schema_version") != STORY_PACKAGE_SCHEMA_VERSION:
        raise StoryPackageValidationError("Unsupported story package schema version.")
    for key in ("id", "genre", "tone"):
        if not isinstance(package.get(key), str) or not str(package[key]).strip():
            raise StoryPackageValidationError(f"'{key}' must be a non-empty string.")

    locations = _strings(package.get("locations"), "locations")
    if len(locations) != len(set(locations)):
        raise StoryPackageValidationError("Locations require unique ids.")
    location_ids = set(locations)
    characters = _entries(package, "characters")
    character_ids = _ids(characters, "Characters")
    for character in characters:
        character_id = str(character["id"])
        if str(character.get("location", "")).strip() not in location_ids:
            raise StoryPackageValidationError(f"character '{character_id}' has an unknown location.")
        for required in ("motivation", "role_contract"):
            if not isinstance(character.get(required), str) or not str(character[required]).strip():
                raise StoryPackageValidationError(f"character '{character_id}' requires {required}.")
        if character.get("available") is not True:
            raise StoryPackageValidationError(f"character '{character_id}' must be available at package start.")

    world_rules = _entries(package, "world_rules")
    _ids(world_rules, "World rules")
    for rule in world_rules:
        if not str(rule.get("cause", "")).strip() or not str(rule.get("effect", "")).strip():
            raise StoryPackageValidationError(f"world rule '{rule['id']}' requires cause and effect.")
    secrets = _entries(package, "secrets")
    secret_ids = _ids(secrets, "Secrets")
    for secret in secrets:
        known_by = _strings(secret.get("known_by", []), f"secret '{secret['id']}'.known_by")
        _require_reference(known_by, character_ids, "secret")
    clues = _entries(package, "clues")
    clue_ids = _ids(clues, "Clues")
    revelations = _entries(package, "revelations")
    revelation_ids = _validate_revelations(revelations, secret_ids, clue_ids)
    clue_reveals = {
        revelation for clue in clues for revelation in _strings(clue.get("reveals", []), f"clue '{clue['id']}'.reveals")
    }
    _require_reference(tuple(clue_reveals), revelation_ids, "clue")
    missing_evidence = revelation_ids - clue_reveals
    if missing_evidence:
        raise StoryPackageValidationError(f"revelations lack clue evidence: {', '.join(sorted(missing_evidence))}.")

    assumptions = _entries(package, "causal_assumptions")
    _ids(assumptions, "Causal assumptions")
    enabled_endings: set[str] = set()
    for assumption in assumptions:
        required_revelations = _strings(assumption.get("requires", []), f"assumption '{assumption['id']}'.requires")
        _require_reference(required_revelations, revelation_ids, "causal assumption")
        enabled_endings.update(_strings(assumption.get("enables", []), f"assumption '{assumption['id']}'.enables"))
    beats = _entries(package, "beat_plan")
    _ids(beats, "Beat plan")
    for beat in beats:
        _require_reference(_strings(beat.get("requires", []), f"beat '{beat['id']}'.requires"), revelation_ids, "beat")
    endings = _entries(package, "endings")
    ending_ids = _ids(endings, "Endings")
    if not endings:
        raise StoryPackageValidationError("Package requires at least one ending.")
    for ending in endings:
        ending_id = str(ending["id"])
        required_revelations = _strings(
            ending.get("requires_revelations", []), f"ending '{ending_id}'.requires_revelations"
        )
        _require_reference(required_revelations, revelation_ids, "ending")
        available_characters = _strings(
            ending.get("available_characters", []), f"ending '{ending_id}'.available_characters"
        )
        _require_reference(available_characters, character_ids, "ending")
    _require_reference(tuple(enabled_endings), ending_ids, "causal assumption")
    unreachable = ending_ids - enabled_endings
    if unreachable:
        raise StoryPackageValidationError(f"endings lack causal viability: {', '.join(sorted(unreachable))}.")
    return package


def _specialist_name(critic_id: str) -> str:
    return critic_id.strip().lower().replace("-", "_")


def _run_specialists(critics: tuple[StoryPackageCritic, ...], package: dict[str, Any]) -> tuple[CritiqueReport, ...]:
    if not critics:
        raise StoryPackageValidationError("Offline package evaluation requires specialist critiques.")
    with ThreadPoolExecutor(max_workers=len(critics)) as executor:
        futures = tuple(executor.submit(critic.critique, package) for critic in critics)
        reports = tuple(parse_critique_report(dict(future.result())) for future in futures)
    names = {_specialist_name(report["critic_id"]) for report in reports}
    missing = sorted(_REQUIRED_SPECIALISTS - names)
    if missing:
        raise StoryPackageValidationError(f"Missing required specialists: {', '.join(missing)}.")
    return reports


def _token_usage(reports: tuple[CritiqueReport, ...]) -> int:
    return sum(len(report["feedback"].split()) for report in reports)


def _recovery_record(payload: Mapping[str, object] | None) -> RecoveryRecord:
    if payload is None:
        return {
            "attempted": False,
            "preserved_fact_categories": (),
            "modified_fact_categories": (),
            "discarded_fact_categories": (),
        }
    return {
        "attempted": True,
        "preserved_fact_categories": tuple(
            sorted(_strings(payload.get("preserved_fact_categories", []), "preserved_fact_categories"))
        ),
        "modified_fact_categories": tuple(
            sorted(_strings(payload.get("modified_fact_categories", []), "modified_fact_categories"))
        ),
        "discarded_fact_categories": tuple(
            sorted(_strings(payload.get("discarded_fact_categories", []), "discarded_fact_categories"))
        ),
    }


def author_story_package(
    request: dict[str, object],
    generator: StoryPackageGenerator,
    critics: tuple[StoryPackageCritic, ...],
    *,
    recoverer: StoryPackageRecoverer | None = None,
    max_rounds: int = 1,
    max_tokens: int = 4096,
    wall_clock_ms: int = 30_000,
) -> AuthoringResult:
    """Generate, validate, critique, and optionally recover a package offline."""
    if max_rounds < 1 or max_tokens < 1 or wall_clock_ms < 1:
        raise ValueError("Authoring budgets must be positive.")
    package = validate_story_package(generator.generate(dict(request)))
    start = perf_counter()
    reports: tuple[CritiqueReport, ...] = ()
    recovery_payload: Mapping[str, object] | None = None
    decision: JudgeDecision | None = None
    token_usage = 0
    direct_validity = False
    for round_index in range(1, max_rounds + 1):
        if int((perf_counter() - start) * 1000) > wall_clock_ms:
            break
        reports = _run_specialists(critics, package)
        token_usage += _token_usage(reports)
        if token_usage > max_tokens:
            break
        decision = judge_critique_round(
            reports,
            threshold=85,
            critical_floors=DEFAULT_CRITICAL_FLOORS,
            weights=DEFAULT_WEIGHTS,
            round_index=round_index,
        )
        if round_index == 1:
            direct_validity = decision["status"] == "accepted"
        if decision["status"] == "accepted" or recoverer is None or recovery_payload is not None:
            break
        recovery_payload = recoverer.recover(package, tuple(report["feedback"] for report in reports))
        candidate = recovery_payload.get("package")
        if not isinstance(candidate, Mapping):
            raise StoryPackageValidationError("Recovery candidate requires a package object.")
        package = validate_story_package(candidate)
    if decision is None:
        raise StoryPackageValidationError("Authoring evaluation exhausted its wall-clock budget.")
    evaluation: PackageEvaluation = {
        "rubric_version": STORY_PACKAGE_RUBRIC_VERSION,
        "rounds": decision["round_index"],
        "token_usage": token_usage,
        "elapsed_ms": int((perf_counter() - start) * 1000),
        "direct_validity": direct_validity,
        "repair_rate": 1.0 if recovery_payload is not None and decision["status"] == "accepted" else 0.0,
        "contradiction_count": 0,
        "leakage_count": 0,
        "role_drift_count": 0,
        "reports": reports,
    }
    return {
        "package": package,
        "accepted": decision["status"] == "accepted",
        "judge": decision,
        "evaluation": evaluation,
        "recovery": _recovery_record(recovery_payload),
    }


def evaluate_package_playability(package: Mapping[str, object], player: ScriptedPlayer) -> PlayabilityResult:
    """Run each required style and accept only declared, valid endings."""
    validated = validate_story_package(package)
    ending_ids = {str(ending["id"]) for ending in _entries(validated, "endings")}
    runs: list[PlayabilityRun] = []
    for style in PLAY_STYLES:
        raw_run = player.play(validated, style)
        ending_id = str(raw_run.get("ending_id", "")).strip()
        artifact = raw_run.get("artifact", {})
        if not isinstance(artifact, Mapping):
            raise StoryPackageValidationError("Playability artifact must be an object.")
        if ending_id not in ending_ids:
            raise StoryPackageValidationError(f"{style} player did not reach a valid ending.")
        runs.append({"style": style, "ending_id": ending_id, "artifact": dict(artifact)})
    return {"passed": True, "runs": tuple(runs)}

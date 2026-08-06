"""Deterministic fixtures and artifact-based checks for behavioral evaluation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Literal, TypedDict, cast

import yaml

FailureCategory = Literal[
    "contradiction",
    "impossible_action",
    "hidden_information_leak",
    "role_drift",
    "causal_omission",
    "uncommitted_narration",
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
    "repetitive_scene_pressure",
    "blocked_player_agency",
)


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


def _fixtures_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "evaluation_fixtures.yaml"


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
    valid_commands = isinstance(commands, list) and commands and all(
        isinstance(command, str) and command for command in commands
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
    pressure = _strings(artifact, "scene_pressure")
    if len(pressure) >= 3 and len(set(pressure)) == 1:
        categories.append("repetitive_scene_pressure")
    if artifact.get("agency_outcome") == "blocked" and not artifact.get("clarification_requested"):
        categories.append("blocked_player_agency")
    return tuple(categories)


def _strings(artifact: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = artifact.get(key, ())
    if not isinstance(value, (list, tuple)):
        return ()
    return tuple(value for value in value if isinstance(value, str))

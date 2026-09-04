"""Prompt assembly, live execution, and statistics for the local bench."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import tempfile
import time
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean, stdev
from typing import Any

from storygame.runtime.cloudflare import DEFAULT_OUTPUT_EXAMPLE, CloudflareTurnProvider, NarrationProviderError
from storygame.runtime.contracts import join_narration
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

CRITERIA = (
    "canon_consistent",
    "scene_local",
    "progressive",
    "rich",
    "protected_safe",
    "exit_motivated",
    "rewards_investigation",
)
REFERENCE_SD = 2.24
REFERENCE_MDE_AT_FOUR = 3.87
DEFAULT_NARRATOR_MODEL = "@cf/meta/llama-3.1-8b-instruct-fast"
LEDGER_PATH = Path(__file__).resolve().parent / "results" / "ledger.jsonl"
DEFAULT_PROMPT_RULES = (
    "Narrate the concrete immediate consequence of the player's action.",
    "Ground narration in the scene and knowledge context.",
    "Use the authored place, texture, and physical detail.",
    "Answer what the player actually did.",
    "Never invent durable evidence, physical objects, items, or container contents.",
    "Treat the authored entry_text and beat details as already true.",
    "A grounding ID may name only committed knowledge or the selected candidate.",
    "Never ground on a candidate you did not select.",
    "Dialogue may use only its speaker's sayable knowledge.",
    "Select at most one candidate ID in selected_knowledge_ids.",
    "A selected candidate must be conveyed by one readable segment, and that segment must carry its ID "
    "in grounding_ids.",
    "A candidate with neither a statement nor a must_convey group cannot be selected.",
    "Leave selected_knowledge_ids empty when no candidate fits what just happened.",
    "Narrating a reveal without selecting it stalls the story.",
    "Never write source IDs, events, operations, facts, or transitions as prose.",
    "Return one paragraph per segment, roughly 30 to 55 words, with at most 5 segments.",
    "Never reuse a beat's sentences.",
    "Never contradict authored text.",
    "Never echo the request fields.",
)
T_CRITICAL_95 = {
    1: 12.706,
    2: 4.303,
    3: 3.182,
    4: 2.776,
    5: 2.571,
    6: 2.447,
    7: 2.365,
    8: 2.306,
    9: 2.262,
    10: 2.228,
    11: 2.201,
    12: 2.179,
    13: 2.160,
    14: 2.145,
    15: 2.131,
    16: 2.120,
    17: 2.110,
    18: 2.101,
    19: 2.093,
    20: 2.086,
    21: 2.080,
    22: 2.074,
    23: 2.069,
    24: 2.064,
    25: 2.060,
    26: 2.056,
    27: 2.052,
    28: 2.048,
    29: 2.045,
    30: 2.042,
}


def load_dotenv() -> None:
    """Load the local env file without adding a dotenv dependency."""

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.removeprefix("export ").strip()
        value = value.strip().strip("\"'")
        os.environ.setdefault(key, value)


def read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON file {path}: {error}") from error
    if not isinstance(value, dict):
        raise ValueError(f"JSON file {path} must contain an object")
    return value


def load_variation(path: Path) -> dict[str, Any]:
    variation = read_json(path)
    name = variation.get("name")
    if not isinstance(name, str) or not name:
        raise ValueError("variation must have a non-empty name")
    package_value = variation.get("story_package", variation.get("package"))
    if not isinstance(package_value, str) or not package_value:
        raise ValueError("variation must name story_package")
    variation["_path"] = str(path.resolve())
    package_path = resolve_package(path, package_value)
    variation["_package_path"] = str(materialize_package(package_path, variation.get("overrides")))
    variation["_package_hash"] = hash_package(Path(variation["_package_path"]))
    prompt = variation.get("system_prompt", {})
    user_prompt = variation.get("user_prompt", {})
    if not isinstance(prompt, dict) or not isinstance(user_prompt, dict):
        raise ValueError("system_prompt and user_prompt must be objects")
    beat_delivery = user_prompt.get("beat_delivery", "details")
    if beat_delivery not in {"details", "prose"}:
        raise ValueError("user_prompt.beat_delivery must be details or prose")
    rules = prompt.get("rules")
    if rules is not None and (not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules)):
        raise ValueError("system_prompt.rules must be a list of strings")
    include_output_example = prompt.get("include_output_example", True)
    if not isinstance(include_output_example, bool):
        raise ValueError("system_prompt.include_output_example must be a boolean")
    if "output_example" in prompt and not isinstance(prompt["output_example"], str):
        raise ValueError("system_prompt.output_example must be a string")
    resolved_output_example = prompt.get("output_example", DEFAULT_OUTPUT_EXAMPLE if include_output_example else None)
    if "output_example" in prompt:
        include_output_example = True
    variation["_prompt_variant"] = {
        **({"rules": rules} if rules is not None else {}),
        "include_output_example": include_output_example,
        "output_example": resolved_output_example,
        "beat_delivery": beat_delivery,
    }
    variation["_resolved_rules"] = list(rules if rules is not None else DEFAULT_PROMPT_RULES)
    variation["_resolved_output_example"] = resolved_output_example
    variation["_variation_hash"] = stable_hash(
        {
            "rules": variation["_resolved_rules"],
            "include_output_example": include_output_example,
            "output_example": resolved_output_example,
            "beat_delivery": beat_delivery,
        }
    )
    variation["_story_package_value"] = package_value
    return variation


def stable_hash(value: object) -> str:
    """Hash JSON content independently of paths, whitespace, or key order."""

    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def hash_package(root: Path) -> str:
    """Hash every effective package file, including its relative filename."""

    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix().encode("utf-8")
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def materialize_package(package_path: Path, overrides: object) -> Path:
    """Return the original package or an isolated effective copy with patches."""

    if overrides is None:
        return package_path
    if not isinstance(overrides, dict):
        raise ValueError("variation.overrides must be an object")
    temporary = tempfile.TemporaryDirectory(prefix="bench-package-")
    effective = Path(temporary.name)
    shutil.copytree(package_path, effective, dirs_exist_ok=True)
    # Keep the TemporaryDirectory alive for the duration of the command and any
    # direct test using the resolved variation.
    _TEMPORARY_PACKAGES.append(temporary)
    for filename, patch in overrides.items():
        if not isinstance(filename, str) or not filename:
            raise ValueError("override filenames must be non-empty strings")
        relative = Path(filename)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"override path escapes story package: {filename}")
        target = effective / relative
        if not target.is_file():
            raise ValueError(f"override file does not exist in story package: {filename}")
        if isinstance(patch, str):
            target.write_text(patch, encoding="utf-8")
            continue
        if not isinstance(patch, dict):
            raise ValueError(f"override for {filename} must be a replacement object or string")
        replacements = patch.get("replacements")
        if not isinstance(replacements, list) or not replacements:
            raise ValueError(f"override for {filename} must contain replacements")
        content = target.read_text(encoding="utf-8")
        for replacement in replacements:
            if not isinstance(replacement, dict):
                raise ValueError(f"replacement for {filename} must be an object")
            old, new = replacement.get("old"), replacement.get("new")
            if not isinstance(old, str) or not old or not isinstance(new, str):
                raise ValueError(f"replacement for {filename} needs non-empty old and string new")
            occurrences = content.count(old)
            if occurrences != 1:
                raise ValueError(f"replacement for {filename} expected one {old!r}, found {occurrences}")
            content = content.replace(old, new, 1)
        target.write_text(content, encoding="utf-8")
    return effective


_TEMPORARY_PACKAGES: list[tempfile.TemporaryDirectory[str]] = []


def resolve_package(variation_path: Path, package_value: str) -> Path:
    candidate = Path(package_value).expanduser()
    if candidate.is_absolute():
        return candidate
    for base in (Path.cwd(), variation_path.resolve().parents[2], variation_path.resolve().parent):
        resolved = (base / candidate).resolve()
        if resolved.is_dir():
            return resolved
    return (Path.cwd() / candidate).resolve()


def package_and_state(variation: dict[str, Any], scene_id: str | None = None) -> tuple[Any, RuntimeState]:
    package = load_story_package(Path(variation["_package_path"]))
    target_scene = scene_id or package.scenes[0].metadata.scene_id
    scene = next((item for item in package.scenes if item.metadata.scene_id == target_scene), None)
    if scene is None:
        raise ValueError(f"scene {target_scene} is not in package {package.story_id}")
    state = RuntimeState(package=package, current_scene_id=target_scene, phase=scene.metadata.freytag_phase)
    state._assert_scene_entry_fact(target_scene)
    return package, state


def provider_for(state: RuntimeState, variation: dict[str, Any]) -> CloudflareTurnProvider:
    return CloudflareTurnProvider.from_environment(state, prompt_variant=variation["_prompt_variant"])


def prompt_for(variation: dict[str, Any], scene_id: str, player_input: str) -> dict[str, str]:
    _, state = package_and_state(variation, scene_id)
    provider = CloudflareTurnProvider(worker_url="", token="", state=state, prompt_variant=variation["_prompt_variant"])
    RuntimeEngine(state, provider)._activate_pacing()
    assembled = provider.assemble_turn_prompt(player_input)
    context = assembled["context"]
    return {"system": str(assembled["system"]), "user": provider._tagged_user_prompt(context)}


_WORD_PATTERN = re.compile(r"\b[\w]+(?:[-'][\w]+)*\b", re.UNICODE)


def _example_words(text: str) -> tuple[str, ...]:
    return tuple(_WORD_PATTERN.findall(re.sub(r"\s+", " ", text).casefold()))


def has_example_leakage(narration: str, example: str | None) -> bool:
    """Return whether narration shares an eight-word contiguous span with example."""

    if not example:
        return False
    example_words = _example_words(example)
    narration_words = _example_words(narration)
    if len(example_words) < 8 or len(narration_words) < 8:
        return False
    spans = {example_words[index : index + 8] for index in range(len(example_words) - 7)}
    return any(narration_words[index : index + 8] in spans for index in range(len(narration_words) - 7))


def count_example_leakage(narrations: Iterable[str], example: str | None) -> int:
    """Count narration turns containing a distinctive span from the used example."""

    return sum(has_example_leakage(narration, example) for narration in narrations)


def scripts_for(variation: dict[str, Any], scene_id: str) -> list[dict[str, Any]]:
    scripts = variation.get("scripts", {})
    scene_scripts = scripts.get(scene_id, []) if isinstance(scripts, dict) else []
    if isinstance(scene_scripts, dict):
        scene_scripts = [scene_scripts]
    if not scene_scripts:
        scene_scripts = [{"name": "default", "inputs": ["I investigate the immediate scene carefully."] * 8}]
    output = []
    for index, script in enumerate(scene_scripts):
        if isinstance(script, list):
            name, inputs = f"script-{index + 1}", script
        elif isinstance(script, dict):
            name, inputs = script.get("name", f"script-{index + 1}"), script.get("inputs", [])
        else:
            raise ValueError(f"script {index + 1} for {scene_id} must be an object or list")
        if not isinstance(name, str) or not isinstance(inputs, list) or not inputs or not all(
            isinstance(item, str) and item for item in inputs
        ):
            raise ValueError(f"script {name!r} for {scene_id} must contain non-empty string inputs")
        output.append({"name": name, "inputs": inputs})
    return output


def run_scene(variation: dict[str, Any], scene_id: str, script: dict[str, Any], max_turns: int = 12) -> dict[str, Any]:
    package, state = package_and_state(variation, scene_id)
    provider = provider_for(state, variation)
    engine = RuntimeEngine(state, provider)
    try:
        opening = engine.opening()
    except NarrationProviderError as error:
        return _failed_scene_record(variation, scene_id, script, provider, error)
    turns = []
    inputs = script["inputs"]
    quota = None
    for turn_number in range(max_turns):
        player_input = inputs[turn_number % len(inputs)]
        prior_scene = state.current_scene_id
        try:
            proposal = _turn_with_rate_limit_retry(engine, player_input)
        except NarrationProviderError as error:
            return _failed_scene_record(
                variation,
                scene_id,
                script,
                provider,
                error,
                opening=opening.narration,
                turns=turns,
            )
        entered = state.current_scene_id != prior_scene
        segments = proposal.segments[:-1] if entered else proposal.segments
        narration = join_narration(tuple(segments)) if segments else ""
        if narration:
            turns.append(
                {
                    "player_input": player_input,
                    "narration": narration,
                    "left_scene": entered,
                    "beats_projected": list(state.last_turn_delivery.beats_projected),
                }
            )
        if entered:
            break
    else:
        return _failed_scene_record(
            variation,
            scene_id,
            script,
            provider,
            RuntimeError(f"scene {scene_id} did not leave within {max_turns} turns for script {script['name']}"),
            opening=opening.narration,
            turns=turns,
        )
    return {
        "status": "ok",
        "replicate": 0,
        "script": script["name"],
        "scene_id": scene_id,
        "opening": opening.narration,
        "turns": turns,
        "completed": quota is None and bool(turns),
        "quota": quota,
        "narration_turns": len(turns),
        "example_leakage": count_example_leakage(
            (turn["narration"] for turn in turns), variation.get("_resolved_output_example")
        ),
        "narration_requests": provider.request_count,
        "recovery_requests": provider.recovery_count,
        "package": str(package.root) if hasattr(package, "root") else str(variation["_package_path"]),
    }


def _failed_scene_record(
    variation: dict[str, Any],
    scene_id: str,
    script: dict[str, Any],
    provider: CloudflareTurnProvider,
    error: BaseException,
    *,
    opening: str = "",
    turns: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    error_code = getattr(error, "error_code", "")
    reason = f"{error_code}: {error}" if error_code else str(error)
    quota = None
    if error_code == "AI_QUOTA_EXCEEDED":
        quota = {"error": error_code, "message": "Workers AI quota is exhausted until 00:00 UTC."}
        reason = quota["message"]
    return {
        "status": "failed",
        "replicate": 0,
        "script": script["name"],
        "scene_id": scene_id,
        "opening": opening,
        "turns": turns or [],
        "completed": False,
        "quota": quota,
        "failure_reason": reason,
        "narration_turns": len(turns or []),
        "example_leakage": 0,
        "narration_requests": provider.request_count,
        "recovery_requests": provider.recovery_count,
        "package": str(variation["_package_path"]),
    }


def _turn_with_rate_limit_retry(engine: RuntimeEngine, player_input: str) -> Any:
    retries = int(os.getenv("BENCH_RATE_LIMIT_RETRIES", "3"))
    delay = float(os.getenv("BENCH_RATE_LIMIT_RETRY_SECONDS", "1"))
    for attempt in range(retries + 1):
        before = engine.state.model_copy(deep=True)
        try:
            return engine.turn(player_input)
        except NarrationProviderError as error:
            if error.error_code != "RATE_LIMITED" or attempt >= retries:
                raise
            for field in RuntimeState.model_fields:
                setattr(engine.state, field, getattr(before, field))
            engine.last_projection = None
            engine.last_post_selection_projection = None
            time.sleep(delay)
    raise AssertionError("unreachable")


def score_judgments(judgments: list[dict[str, Any]]) -> dict[str, Any]:
    per_criterion = {criterion: sum(bool(judgment.get(criterion)) for judgment in judgments) for criterion in CRITERIA}
    missing_total = 0
    attributed: dict[str, int] = {}
    for judgment in judgments:
        for item in judgment.get("missing_or_wrong", []):
            missing_total += 1
            text = item.get("criterion", "") if isinstance(item, dict) else str(item)
            for criterion in CRITERIA:
                if re.search(rf"\b{re.escape(criterion)}\b", text):
                    attributed[criterion] = attributed.get(criterion, 0) + 1
                    break
    return {
        "total": sum(per_criterion.values()),
        "per_criterion": per_criterion,
        "graded_secondary": {
            "metric": "missing_or_wrong entries (fewer is better); separate from the seven-criteria score",
            "total": missing_total,
            "per_criterion_where_attributable": attributed,
            "unattributed": missing_total - sum(attributed.values()),
        },
    }


def _stats(values: list[float], n_for_mde: int | None = None) -> dict[str, Any]:
    count = len(values)
    average = mean(values) if values else None
    deviation = stdev(values) if count > 1 else None
    if deviation is not None:
        critical = T_CRITICAL_95.get(count - 1, 1.96)
        margin = critical * deviation / math.sqrt(count)
        interval = [average - margin, average + margin]
    else:
        interval = None
    n_for_mde = n_for_mde or count
    mde = REFERENCE_MDE_AT_FOUR * math.sqrt(4 / n_for_mde) if n_for_mde else None
    return {
        "n": count,
        "mean": average,
        "standard_deviation": deviation,
        "confidence_interval_95": interval,
        "minimum_detectable_effect": mde,
        "replicate_scores": values,
    }


def aggregate_runs(runs: list[dict[str, Any]], judgments: list[dict[str, Any]], replicates: int) -> dict[str, Any]:
    paired = [{**run, "judgment": judgment} for run, judgment in zip(runs, judgments, strict=False)]
    values = [float(score_judgments([item["judgment"]])["total"]) for item in paired]
    pooled_judgment = score_judgments(judgments)
    completed_replicates = len({run["replicate"] for run in runs})
    judged_scene_ids = {
        judgment.get("scene_id")
        for judgment in judgments
        if isinstance(judgment, dict) and judgment.get("scene_id")
    }
    scenes_scored = len(judged_scene_ids or {run["scene_id"] for run in paired if run.get("scene_id")})
    max_score = scenes_scored * len(CRITERIA)
    by_script: dict[str, Any] = {}
    for script in sorted({run["script"] for run in runs}):
        script_judgments = [item["judgment"] for item in paired if item["script"] == script]
        script_values = [float(score_judgments([judgment])["total"]) for judgment in script_judgments]
        script_score = score_judgments(script_judgments)
        script_replicates = len({item["replicate"] for item in paired if item["script"] == script})
        by_script[script] = {
            "score_points": _stats(script_values, script_replicates),
            "example_leakage": sum(int(item.get("example_leakage", 0)) for item in paired if item["script"] == script),
            "per_criterion": script_score["per_criterion"],
            "graded_secondary": script_score["graded_secondary"],
        }
    return {
        "replicates": replicates,
        "completed_replicates": completed_replicates,
        "scenes_scored": scenes_scored,
        "max_score": max_score,
        "score_metric": (
            f"{max_score}-point record: seven equally weighted boolean criteria across "
            f"{scenes_scored} scene{'s' if scenes_scored != 1 else ''}"
        ),
        "pooled": {"score_points": _stats(values, completed_replicates), **pooled_judgment},
        "per_script": by_script,
        "replicate_scores": values,
        "example_leakage": sum(int(run.get("example_leakage", 0)) for run in runs),
        "criteria_weighting": "All seven booleans are weighted equally despite very different difficulty.",
    }


def _student_t_two_sided_p(statistic: float, degrees: float) -> float:
    """Numerically integrate the Student-t density for a dependency-free p-value."""

    absolute = abs(statistic)
    if not math.isfinite(absolute):
        return 0.0
    if absolute == 0:
        return 1.0
    if absolute > 20:
        return 0.0
    coefficient = math.exp(
        math.lgamma((degrees + 1) / 2) - math.lgamma(degrees / 2) - 0.5 * math.log(degrees * math.pi)
    )
    steps = 2000
    width = absolute / steps

    def density(value: float) -> float:
        return coefficient * (1 + value * value / degrees) ** (-(degrees + 1) / 2)

    weighted = density(0) + density(absolute)
    weighted += 4 * sum(density(index * width) for index in range(1, steps, 2))
    weighted += 2 * sum(density(index * width) for index in range(2, steps, 2))
    integral = weighted * width / 3
    return max(0.0, min(1.0, 1 - 2 * integral))


def welch_t_test(left: list[float], right: list[float]) -> dict[str, Any]:
    if len(left) < 2 or len(right) < 2:
        return {"available": False, "reason": "Welch t-test needs at least two runs in each arm."}
    left_var, right_var = stdev(left) ** 2, stdev(right) ** 2
    standard_error = math.sqrt(left_var / len(left) + right_var / len(right))
    difference = mean(left) - mean(right)
    if standard_error == 0:
        p_value = 1.0 if difference == 0 else 0.0
        degrees = float("inf")
        statistic = float("inf") if difference > 0 else float("-inf")
    else:
        statistic = difference / standard_error
        numerator = (left_var / len(left) + right_var / len(right)) ** 2
        denominator = (left_var**2 / (len(left) ** 2 * (len(left) - 1))) + (
            right_var**2 / (len(right) ** 2 * (len(right) - 1))
        )
        degrees = numerator / denominator if denominator else float("inf")
        p_value = _student_t_two_sided_p(statistic, degrees)
    return {
        "available": True,
        "test": "two-sided Welch t-test",
        "difference_in_means": difference,
        "t": statistic,
        "degrees_of_freedom": degrees,
        "p_value": p_value,
        "inside_noise": p_value >= 0.05,
        "statement": "this changed nothing detectable (difference is inside the observed noise)"
        if p_value >= 0.05
        else "the difference is detectable at p < 0.05",
    }


def ledger_rows(path: Path = LEDGER_PATH) -> list[dict[str, Any]]:
    """Read the append-only ledger in its stored order."""

    if not path.is_file():
        return []
    rows = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"ledger line {line_number} is not valid JSON: {error}") from error
        if not isinstance(row, dict):
            raise ValueError(f"ledger line {line_number} must be a JSON object")
        rows.append(row)
    return rows


def successful_ledger_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return successful rows; old rows without status were successful."""

    return [row for row in rows if row.get("status", "ok") == "ok"]


def scenes_scored_for_row(row: dict[str, Any]) -> int | None:
    """Read recorded coverage; missing or null coverage has an unknown scale."""

    if "scenes_scored" not in row or row["scenes_scored"] is None:
        return None
    coverage = row["scenes_scored"]
    if isinstance(coverage, int) and not isinstance(coverage, bool) and coverage >= 0:
        return coverage
    raise ValueError("ledger row has invalid scenes_scored")


def known_scale_ledger_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return successful rows whose scene denominator was explicitly recorded."""

    return [row for row in successful_ledger_rows(rows) if scenes_scored_for_row(row) is not None]


def unknown_scale_ledger_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Return successful rows without a recorded scene denominator."""

    return [row for row in successful_ledger_rows(rows) if scenes_scored_for_row(row) is None]


def append_ledger_row(row: dict[str, Any], path: Path = LEDGER_PATH) -> None:
    """Append exactly one immutable JSON row; never read-modify-write the file."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _git_provenance() -> tuple[str, bool]:
    sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], text=True
    ).strip()
    return sha, bool(status)


def ledger_row(
    variation: dict[str, Any],
    *,
    scene: str,
    scripts: list[dict[str, Any]],
    replicates: int,
    aggregate: dict[str, Any],
    status: str = "ok",
    failure_reason: str | None = None,
) -> dict[str, Any]:
    """Build the durable provenance record for one bench invocation."""

    git_sha, git_dirty = _git_provenance()
    pooled = aggregate["pooled"]
    scores = [int(score) for score in aggregate["replicate_scores"]]
    score_stats = pooled["score_points"]
    budget = aggregate["budget"]
    row = {
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "variation_name": variation["name"],
        "variation_hash": variation["_variation_hash"],
        "package_hash": variation["_package_hash"],
        "git_sha": git_sha,
        "git_dirty": git_dirty,
        "scene": scene,
        "scripts": [script["name"] for script in scripts],
        "replicates": replicates,
        "status": status,
        "scenes_scored": aggregate["scenes_scored"],
        "max_score": aggregate["max_score"],
        "score_metric": aggregate["score_metric"],
        "scores": scores,
        "example_leakage": int(aggregate.get("example_leakage", 0)),
        "mean": score_stats["mean"],
        "sd": score_stats["standard_deviation"],
        "per_criterion": pooled["per_criterion"],
        "missing_or_wrong": pooled["graded_secondary"],
        "spend": {
            "neurons": round(budget["estimated_workers_ai_neurons_from_requests"], 2),
            "judge_calls": budget["actual_openai_judge_calls"],
        },
        "model": os.getenv("CF_AI_MODEL", "").strip() or DEFAULT_NARRATOR_MODEL,
    }
    if failure_reason is not None:
        row["failure_reason"] = failure_reason
    return row


def baseline_scenes_scored(run_dir: Path) -> int | None:
    """Return recorded baseline coverage, or unknown when no denominator exists."""

    summary_path = run_dir / "summary.json"
    if summary_path.is_file():
        summary = read_json(summary_path)
        coverage = summary.get("scenes_scored")
        if isinstance(coverage, int) and not isinstance(coverage, bool) and coverage >= 0:
            return coverage
        return None
    judgment_path = run_dir / "e2e-llm-canon.json"
    if judgment_path.is_file():
        data = read_json(judgment_path)
        judgments = data.get("judgments", [])
        scene_ids = {item.get("scene_id") for item in judgments if isinstance(item, dict) and item.get("scene_id")}
        if scene_ids:
            return len(scene_ids)
        return None
    raise ValueError(f"baseline directory {run_dir} has no scene coverage metadata")


def baseline_scores(run_dir: Path) -> list[float]:
    if baseline_scenes_scored(run_dir) is None:
        return []
    summary_path = run_dir / "summary.json"
    if summary_path.is_file():
        summary = read_json(summary_path)
        scores = summary.get("replicate_scores") or summary.get("pooled", {}).get("score_points", {}).get(
            "replicate_scores", []
        )
        if scores:
            return [float(score) for score in scores]
    judgment_path = run_dir / "e2e-llm-canon.json"
    if judgment_path.is_file():
        data = read_json(judgment_path)
        return [float(score_judgments(data.get("judgments", []))["total"])]
    raise ValueError(f"baseline directory {run_dir} has no summary.json or e2e-llm-canon.json")


def run_judges(input_path: Path, output_path: Path) -> dict[str, Any]:
    command = [
        "node",
        str(Path(__file__).with_name("judge-cli.mjs")),
        "--input",
        str(input_path),
        "--output",
        str(output_path),
    ]
    result = subprocess.run(command, check=False, text=True, capture_output=True, env=os.environ.copy())
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "judge CLI failed")
    return read_json(output_path)

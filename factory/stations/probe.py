"""Replay a bounded live report against a ticket tree and judge the two arms.

The probe rules are fixed before a probe starts. ``replicates`` is the number
of bench replicates for each arm. ``max_stuck_ratio`` is the largest candidate
stuck-turn rate relative to control. ``min_control_stuck_turns`` is the minimum
control problem size needed to make a comparison meaningful.
``estimated_usd_per_turn`` prices one billed narrator turn for the spend gate.
``max_runs_per_probe`` is the total number of recorded scripts retained before
the two arms are run. ``max_turns_per_run`` caps each retained script.

``summarize_arm`` deliberately applies the live stuck-turn idea to bench
records: a turn is stuck when it is not rejected, selects no knowledge, and
adds no new grounding id within its run. Bench records do not carry a fired
storylet list, so this is the same fair, story-agnostic count for both arms,
but it is not the live harness's explicit stuck count.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import subprocess
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from factory.cloudflare_spend import read_worker_budget, spend_between
from factory.followups import _safe_id
from factory.guard import BudgetExhausted, Caps, LimitSleep, ProviderLimit, SpendLedger, Usage
from factory.line import StationHandler, StationResult
from factory.stations.live_playtest import (
    _factory_config,
    _fresh_staged_lock,
    _next_midnight,
    _pre_run_budget_gate,
    _raise_quota,
    _safe_budget_read,
    _scene_runs,
    _staged_lock_path,
    _valid_turns,
)
from factory.stations.tree import ticket_tree
from factory.stations.wiring import _story_root
from factory.tickets import _atomic_json_write

PROBE_VERSION = "probe-v1"
_RULES_PATH = Path(__file__).resolve().parents[1] / "config" / "probe_rules.json"
PROBE_RULES: dict[str, Any] = json.loads(_RULES_PATH.read_text(encoding="utf-8"))
_RUN_TIMEOUT_S = 2400


def _rules(value: dict[str, Any] | None) -> dict[str, Any]:
    selected = dict(PROBE_RULES if value is None else value)
    expected = {
        "replicates",
        "max_stuck_ratio",
        "min_control_stuck_turns",
        "estimated_usd_per_turn",
        "max_runs_per_probe",
        "max_turns_per_run",
    }
    if set(selected) != expected:
        raise ValueError("probe rules must contain exactly the six configured keys")
    return selected


def runs_from_report(report: dict, scene: str) -> list[dict]:
    """Extract bounded typed-command replay scripts from a live report."""

    result: list[dict] = []
    for replicate, scene_run in _scene_runs(report):
        if scene_run.get("scene") != scene:
            continue
        inputs = [turn["raw_input"] for turn in _valid_turns(scene_run) if isinstance(turn.get("raw_input"), str)]
        if len(inputs) < 2:
            continue
        result.append(
            {
                "run": f"{scene}-r{replicate}",
                "scene": scene,
                "inputs": inputs[: int(PROBE_RULES["max_turns_per_run"])],
            }
        )
    return result[: int(PROBE_RULES["max_runs_per_probe"]) // 2]


def build_variation(*, name: str, package_path: str, scene: str, run: dict) -> dict:
    """Build one story-package-only bench replay variation."""

    inputs = list(run["inputs"])
    return {
        "name": name,
        "story_package": str(Path(package_path).resolve()),
        "runtime": True,
        "entry_state": "thorough",
        "item_facts": {"mode": "single_call", "seed_from_package": True},
        "fixed_refusal": True,
        "engine_refusal": True,
        "fixed_turns": len(inputs),
        "scripts": {scene: [{"name": run["run"], "inputs": inputs}]},
    }


def _turns_in_file(path: Path) -> list[dict[str, Any]]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
        raise ValueError(f"malformed turn-records file: {path}") from error
    if not isinstance(value, dict) or not isinstance(value.get("runs"), list):
        raise ValueError(f"malformed turn-records file: {path}")
    return value["runs"]


def _transition_cause(run: dict[str, Any], turn: dict[str, Any]) -> str | None:
    cause = turn.get("transition_cause")
    if isinstance(cause, str):
        return cause
    transitions = run.get("scene_transitions")
    if not isinstance(transitions, list):
        return None
    turn_number = turn.get("turn_number")
    for transition in transitions:
        if not isinstance(transition, dict):
            continue
        if transition.get("after_turn") == turn_number:
            for field in ("cause", "transition_cause"):
                if isinstance(transition.get(field), str):
                    return transition[field]
    return None


def _rejected_count(run: dict[str, Any], turns: list[dict[str, Any]]) -> int:
    rejected = run.get("rejected_turns")
    if isinstance(rejected, list):
        return len(rejected)
    count = run.get("rejected_turn_count")
    if isinstance(count, int) and not isinstance(count, bool) and count >= 0:
        return count
    return sum(turn.get("rejected") is True for turn in turns)


def _run_is_complete(run: dict[str, Any]) -> bool:
    return run.get("status") in {"ok", "completed"} and run.get("completed") is not False


def summarize_arm(turn_records_files: list[Path]) -> dict:
    """Summarize completed bench runs, rejecting malformed record files."""

    summary = {
        "replicates": 0,
        "turns": 0,
        "stuck_turns": 0,
        "rejected_turns": 0,
        "game_breaks": 0,
        "earned_exits": 0,
        "forced_exits": 0,
    }
    for raw_path in turn_records_files:
        path = Path(raw_path)
        runs = _turns_in_file(path)
        for run in runs:
            if not isinstance(run, dict):
                raise ValueError(f"malformed turn-records file: {path}")
            if not _run_is_complete(run):
                continue
            raw_turns = run.get("turns")
            if not isinstance(raw_turns, list) or any(not isinstance(turn, dict) for turn in raw_turns):
                raise ValueError(f"malformed turn-records file: {path}")
            turns = [turn for turn in raw_turns if isinstance(turn, dict)]
            summary["replicates"] += 1
            rejected = _rejected_count(run, turns)
            summary["turns"] += len(turns) + rejected
            summary["rejected_turns"] += rejected
            earlier_grounding: set[str] = set()
            left_scene = False
            forced = False
            for turn in turns:
                grounding = turn.get("grounding_ids")
                grounding_ids = (
                    {item for item in grounding if isinstance(item, str)} if isinstance(grounding, list) else set()
                )
                selected = turn.get("selected_knowledge_ids")
                if (
                    turn.get("rejected") is not True
                    and not selected
                    and not grounding_ids.difference(earlier_grounding)
                ):
                    summary["stuck_turns"] += 1
                earlier_grounding.update(grounding_ids)
                if turn.get("game_break") is not None:
                    summary["game_breaks"] += 1
                if turn.get("left_scene") is True:
                    left_scene = True
                    forced = _transition_cause(run, turn) in {"forced", "timer"}
            if left_scene:
                summary["forced_exits" if forced else "earned_exits"] += 1
    return summary


def projected_cost_usd(runs: list[dict], replicates: int, rules: dict) -> float:
    """Estimate both arms' billed narrator cost for the selected replay scripts."""

    return (
        2
        * len(runs)
        * replicates
        * sum(len(run.get("inputs", ())) for run in runs)
        * float(rules["estimated_usd_per_turn"])
    )


def _rate(summary: dict, field: str, denominator: str) -> float:
    total = summary.get(denominator, 0)
    return summary.get(field, 0) / total if total else 0.0


def judge_probe(control: dict, candidate: dict, rules: dict) -> dict:
    """Apply the frozen comparison rule without reading or changing external state."""

    rules = _rules(rules)
    reasons: list[str] = []
    if control["stuck_turns"] < rules["min_control_stuck_turns"]:
        reasons.append(
            f"Control stuck turns {control['stuck_turns']} are below the minimum {rules['min_control_stuck_turns']}."
        )
    if not control["replicates"] or not candidate["replicates"]:
        reasons.append(
            f"Completed replicates are control {control['replicates']} and candidate {candidate['replicates']}."
        )
    if reasons:
        verdict = "inconclusive"
    else:
        control_stuck_rate = _rate(control, "stuck_turns", "turns")
        candidate_stuck_rate = _rate(candidate, "stuck_turns", "turns")
        if candidate_stuck_rate > float(rules["max_stuck_ratio"]) * control_stuck_rate:
            allowed_rate = float(rules["max_stuck_ratio"]) * control_stuck_rate
            reasons.append(f"Candidate stuck rate {candidate_stuck_rate:.6f} exceeds allowed rate {allowed_rate:.6f}.")
        if candidate["rejected_turns"] > control["rejected_turns"]:
            reasons.append(
                f"Candidate rejected turns {candidate['rejected_turns']} exceed control {control['rejected_turns']}."
            )
        if candidate["game_breaks"] > control["game_breaks"]:
            reasons.append(f"Candidate game breaks {candidate['game_breaks']} exceed control {control['game_breaks']}.")
        control_exit_rate = _rate(control, "earned_exits", "replicates")
        candidate_exit_rate = _rate(candidate, "earned_exits", "replicates")
        if candidate_exit_rate < control_exit_rate:
            reasons.append(
                f"Candidate earned-exit rate {candidate_exit_rate:.6f} is below control {control_exit_rate:.6f}."
            )
        verdict = "reject" if reasons else "keep"
    return {"verdict": verdict, "reasons": reasons, "control": control, "candidate": candidate}


def default_runner(root: Path, argv: list[str], env: dict[str, str], timeout_s: int):
    """Run the bench from the repository root, never from a ticket tree."""

    command = [str(root / ".venv/bin/python"), "-m", "bench", "run", *argv]
    return subprocess.run(
        command,
        cwd=root,
        env=env,
        timeout=timeout_s,
        check=False,
        capture_output=True,
        text=True,
    )


def _package_hash(package: Path) -> str:
    if not package.is_dir():
        raise ValueError(f"candidate story package is missing: {package}")
    digest = hashlib.sha256()
    files = sorted(
        (path for path in package.rglob("*") if path.is_file()), key=lambda path: path.relative_to(package).as_posix()
    )
    for path in files:
        digest.update(path.relative_to(package).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _input_hash(runs: list[dict], rules: dict, package_hash: str) -> str:
    value = {"runs": runs, "rules": rules, "package_hash": package_hash, "version": PROBE_VERSION}
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _resolve(root: Path, value: object) -> Path:
    if not isinstance(value, (str, Path)):
        raise ValueError("path must be a string")
    path = Path(value)
    return path if path.is_absolute() else root / path


def _story_packages(root: Path, tree: Path, payload: dict[str, Any]) -> tuple[Path, Path]:
    control = (
        _resolve(root, payload.get("story_package")) if payload.get("story_package") is not None else _story_root(root)
    )
    try:
        relative = control.resolve().relative_to(root.resolve())
    except ValueError:
        relative = Path("data") / "stories" / control.name
    return control.resolve(), (tree / relative).resolve()


def _line(result: dict) -> str:
    control = result["control"]
    candidate = result["candidate"]
    return (
        f"{result['verdict']}: control stuck {control['stuck_turns']}/{control['turns']} "
        f"candidate stuck {candidate['stuck_turns']}/{candidate['turns']} "
        f"rejected {control['rejected_turns']}/{candidate['rejected_turns']} "
        f"exits {control['earned_exits']}/{candidate['earned_exits']}"
    )


def _feedback(result: dict) -> str:
    return (
        f"verdict {result['verdict']} control {result['control']['stuck_turns']} {result['control']['turns']} "
        f"{result['control']['rejected_turns']} {result['control']['game_breaks']} "
        f"{result['control']['earned_exits']} {result['control']['forced_exits']} candidate "
        f"{result['candidate']['stuck_turns']} {result['candidate']['turns']} "
        f"{result['candidate']['rejected_turns']} {result['candidate']['game_breaks']} "
        f"{result['candidate']['earned_exits']} {result['candidate']['forced_exits']}"
    )


def _result(result: dict) -> StationResult:
    result = {
        "verdict": result["verdict"],
        "reasons": list(result["reasons"]),
        "control": dict(result["control"]),
        "candidate": dict(result["candidate"]),
    }
    result["feedback"] = _feedback(result)
    return StationResult(
        result["verdict"] == "keep",
        "probe",
        _line(result),
        tokens=0,
        payload_updates={"probe": result},
    )


def _record_probe_spend(
    ledger: SpendLedger,
    before: dict | None,
    after: dict | None,
    *,
    now: datetime,
    scene: str,
    ticket_id: str,
    estimate_usd: float | None,
) -> None:
    micro_usd = spend_between(before, after)
    ledger.record(
        Usage(
            at=now,
            provider="cloudflare",
            model_id="workers-ai",
            station="probe",
            scene=scene,
            ticket_id=ticket_id,
            tokens=0,
            usd=micro_usd / 1_000_000 if micro_usd is not None else None,
            cost_kind="dollars" if micro_usd is not None else "unknown",
            estimate_usd=estimate_usd,
        )
    )


def _raise_probe_quota(text: str, now: datetime) -> None:
    upper = text.upper()
    if "QUOTA" not in upper:
        return
    try:
        _raise_quota(text, now)
    except LimitSleep:
        raise
    report = None
    raise LimitSleep("cloudflare", _next_midnight(now)) from ProviderLimit(_next_midnight(now), report)


def probe_handler(
    root: Path | None = None,
    *,
    runner: Callable[..., Any] | None = None,
    read_budget: Callable[[], dict | None] | None = None,
    rules: dict[str, Any] | None = None,
) -> StationHandler:
    """Return station 12 with an injectable, hermetic bench runner."""

    repository_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]
    selected_rules = _rules(rules)
    budget_reader = read_budget or read_worker_budget

    def handle(ticket, now: datetime) -> StationResult:
        payload = getattr(ticket, "payload", None)
        if not isinstance(payload, dict):
            return StationResult(False, "probe", "missing payload key: runs", tokens=0)
        raw_runs = payload.get("runs")
        if isinstance(raw_runs, list):
            runs = raw_runs
        elif isinstance(payload.get("report_path"), str):
            report_path = _resolve(repository_root, payload["report_path"])
            try:
                report = json.loads(report_path.read_text(encoding="utf-8"))
            except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
                return StationResult(False, "probe", f"could not read report: {error}", tokens=0)
            runs = runs_from_report(report, getattr(ticket, "scene", payload.get("scene", "")))
        else:
            return StationResult(False, "probe", "missing payload key: runs", tokens=0)
        if not runs:
            scene = getattr(ticket, "scene", payload.get("scene", ""))
            return StationResult(False, "probe", f"no recorded runs to replay for scene {scene}", tokens=0)

        tree = ticket_tree(payload, str(getattr(ticket, "id", "")), repository_root)
        if tree is None:
            return StationResult(False, "probe", "no ticket tree to probe", tokens=0)
        if payload.get("billed_run_approved") is not True:
            return StationResult(False, "probe", "probe not approved: set billed_run_approved", tokens=0)
        lock_path = _staged_lock_path(repository_root)
        if lock_path.exists() and _fresh_staged_lock(lock_path, now):
            return StationResult(False, "probe", "a staged run is in progress", tokens=0)

        projected: float | None = None
        try:
            control_package, candidate_package = _story_packages(repository_root, tree, payload)
            package_hash = _package_hash(candidate_package)
        except (OSError, RuntimeError, ValueError) as error:
            return StationResult(False, "probe", str(error), tokens=0)
        input_hash = _input_hash(runs, selected_rules, package_hash)
        workspace = Path(str(payload["workspace"])).expanduser().resolve()
        saved_path = workspace / _safe_id(str(getattr(ticket, "id", ""))) / "probe.json"
        try:
            saved = json.loads(saved_path.read_text(encoding="utf-8")) if saved_path.is_file() else None
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            saved = None
        if (
            isinstance(saved, dict)
            and saved.get("input_hash") == input_hash
            and saved.get("verdict")
            in {
                "keep",
                "reject",
                "inconclusive",
            }
        ):
            return _result(saved)

        try:
            config = _factory_config(repository_root)
            caps = Caps.from_dict(config["caps"])
            ledger = SpendLedger(_resolve(repository_root, config["paths"]["ledger"]))
            projected = projected_cost_usd(runs, int(selected_rules["replicates"]), selected_rules)
            budget_error = _pre_run_budget_gate(ledger, caps, now)
            if budget_error is not None:
                return StationResult(False, "probe", budget_error, tokens=0)
            remaining = min(
                caps.total_budget_usd - ledger.total_usd(),
                caps.rate_max_usd - ledger.usd_in_window(now, caps.rate_window_s),
                caps.daily_cap_usd.get("cloudflare", 0.0) - ledger.day_usd("cloudflare", now.date()),
            )
            if projected > remaining:
                return StationResult(
                    False, "probe", f"projected probe cost ${projected:.4f} is above the remaining budget", tokens=0
                )
        except (KeyError, TypeError, ValueError, BudgetExhausted) as error:
            return StationResult(False, "probe", f"invalid factory budget configuration: {error}", tokens=0)

        lock_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            lock_path.write_text(f"{getattr(ticket, 'id', '')}\n{now.isoformat()}\n", encoding="utf-8")
        except OSError as error:
            return StationResult(False, "probe", f"could not create staged run lock: {error}", tokens=0)
        before = _safe_budget_read(budget_reader)
        try:
            arm_files: dict[str, list[Path]] = {"control": [], "candidate": []}
            scene = getattr(ticket, "scene", payload.get("scene", ""))
            for run in runs:
                for arm, package in (("control", control_package), ("candidate", candidate_package)):
                    safe_run = _safe_id(str(run["run"]))
                    probe_dir = workspace / _safe_id(str(getattr(ticket, "id", ""))) / "probe"
                    variation_path = probe_dir / f"{arm}-{safe_run}.json"
                    output_dir = probe_dir / f"{arm}-{safe_run}"
                    variation = build_variation(
                        name=f"probe-{arm}-{run['run']}",
                        package_path=str(package),
                        scene=scene,
                        run=run,
                    )
                    _atomic_json_write(variation_path, variation)
                    argv = [
                        "--variation",
                        str(variation_path),
                        "--scene",
                        scene,
                        "--replicates",
                        str(selected_rules["replicates"]),
                        "--out",
                        str(output_dir),
                        "--confirm",
                    ]
                    with contextlib.suppress(OSError):
                        (output_dir / "turn-records.json").unlink()
                    try:
                        completed = (runner or default_runner)(
                            repository_root,
                            argv,
                            os.environ.copy(),
                            _RUN_TIMEOUT_S * int(selected_rules["replicates"]),
                        )
                    except (LimitSleep, ProviderLimit):
                        raise
                    except Exception as error:
                        return StationResult(False, "probe", f"runner failed: {str(error)[:300]}", tokens=0)
                    combined = "\n".join(str(getattr(completed, field, "") or "") for field in ("stdout", "stderr"))
                    _raise_probe_quota(combined, now)
                    stderr = str(getattr(completed, "stderr", "") or "")
                    if getattr(completed, "returncode", 0) != 0:
                        return StationResult(False, "probe", f"runner failed: {stderr[:300]}", tokens=0)
                    records_path = output_dir / "turn-records.json"
                    if not records_path.is_file():
                        return StationResult(False, "probe", "runner failed: no output file", tokens=0)
                    arm_files[arm].append(records_path)
            result = judge_probe(
                summarize_arm(arm_files["control"]), summarize_arm(arm_files["candidate"]), selected_rules
            )
            saved_result = {"input_hash": input_hash, **result, "feedback": _feedback(result)}
            _atomic_json_write(saved_path, saved_result)
            return _result(saved_result)
        finally:
            after = _safe_budget_read(budget_reader)
            _record_probe_spend(
                ledger,
                before,
                after,
                now=now,
                scene=getattr(ticket, "scene", payload.get("scene", "")),
                ticket_id=str(getattr(ticket, "id", "")),
                estimate_usd=projected,
            )
            with contextlib.suppress(OSError):
                lock_path.unlink()

    return handle


__all__ = [
    "PROBE_RULES",
    "PROBE_VERSION",
    "build_variation",
    "default_runner",
    "judge_probe",
    "probe_handler",
    "projected_cost_usd",
    "runs_from_report",
    "summarize_arm",
]

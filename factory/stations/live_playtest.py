"""Grade the hosted blind-player playtest for station 7.

Payload keys accepted by :func:`live_playtest_handler` are ``scene`` (defaults
to the ticket scene), ``expected_sha`` (required for a live run), ``profile``
(``canonical`` by default), ``replicates`` (one by default and capped at three),
``report_path`` (grade a saved report without making any calls), and
``billed_run_approved`` (required by the default billed runner).

The saved report is the only evidence used to construct station-8 packets.  A
live run first checks the staging identity, then invokes the runner exactly once
and grades the newest report written after that invocation began.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.request
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any

from factory.guard import LimitSleep, ProviderLimit
from factory.limits import LimitReport
from factory.line import StationHandler, StationResult

EARNED_EXIT_CAUSES = frozenset({"play", "earned"})
"""Exit labels treated as earned by the station-7 gate."""

_DEFAULT_PROFILE = "canonical"
_MAX_REPLICATES = 3
_TURN_TIMEOUT_MS = "90000"
_RUN_TIMEOUT_S = 2400
_DEFAULTS: dict[str, Any] = {
    "player_input": "",
    "narration": "",
    "stuck": False,
    "candidates_offered": [],
    "matched_candidate": None,
    "committed": None,
    "engine_error": None,
    "match_issues": [],
    "item_facts_issues": [],
    "item_facts_unplaced": [],
    "flags": [],
}


def _valid_replicate(value: object) -> bool:
    return isinstance(value, (int, str)) and not isinstance(value, bool) and str(value) != ""


def _scene_runs(report: object) -> list[tuple[str, dict[str, Any]]]:
    """Return valid ``(replicate, scene_run)`` pairs without raising."""

    if not isinstance(report, dict) or not isinstance(report.get("replicates"), list):
        return []
    result: list[tuple[str, dict[str, Any]]] = []
    for replicate in report["replicates"]:
        if not isinstance(replicate, dict) or not _valid_replicate(replicate.get("replicate")):
            continue
        replicate_id = str(replicate["replicate"])
        scenes = replicate.get("scenes")
        candidates: Iterable[object]
        candidates = scenes if isinstance(scenes, list) else (replicate,)
        for scene_run in candidates:
            if not isinstance(scene_run, dict):
                continue
            if not isinstance(scene_run.get("scene"), str) or not isinstance(scene_run.get("turns"), list):
                continue
            result.append((replicate_id, scene_run))
    return result


def _valid_turns(scene_run: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        turn
        for turn in scene_run.get("turns", [])
        if isinstance(turn, dict) and isinstance(turn.get("turn"), int) and not isinstance(turn.get("turn"), bool)
    ]


def _packet_for_turn(prefix: str, replicate: str, scene_run: dict[str, Any], turn: dict[str, Any]) -> dict[str, Any]:
    scene = scene_run["scene"]
    packet = {
        "key": f"{prefix}{scene}-r{replicate}-t{turn['turn']}",
        "scene": scene,
        **{field: list(value) if isinstance(value, list) else value for field, value in _DEFAULTS.items()},
    }
    if isinstance(turn.get("raw_input"), str):
        packet["player_input"] = turn["raw_input"]
    if isinstance(turn.get("text"), str):
        packet["narration"] = turn["text"]
    stuck_turns = scene_run.get("stuck_turns")
    packet["stuck"] = isinstance(stuck_turns, list) and turn["turn"] in stuck_turns

    rejection = turn.get("rejection")
    if isinstance(rejection, str) and rejection:
        packet["match_issues"] = [rejection]

    semantic_match = turn.get("semantic_match")
    matched = semantic_match.get("matched") if isinstance(semantic_match, dict) else None
    if isinstance(matched, str) and matched:
        packet["matched_candidate"] = matched
        # The report has no candidate list.  This conservative surrogate keeps
        # a reported match out of the R2 "no candidates" route.
        packet["candidates_offered"] = [matched]
    return packet


def _turn_fails(scene_run: dict[str, Any], turn: dict[str, Any]) -> bool:
    stuck_turns = scene_run.get("stuck_turns")
    stuck = isinstance(stuck_turns, list) and turn["turn"] in stuck_turns
    return (
        stuck
        or turn.get("rejected") is True
        or turn.get("game_break") is not None
        or turn.get("outcome") != "committed"
        or turn.get("transition_cause") in {"forced", "timer"}
    )


def report_to_packets(report: dict, *, key_prefix: str = "") -> list[dict]:
    """Convert each failing turn in a report to one validated-shape packet."""

    packets: list[dict] = []
    for replicate, scene_run in _scene_runs(report):
        turns = _valid_turns(scene_run)
        for turn in turns:
            if _turn_fails(scene_run, turn):
                packets.append(_packet_for_turn(key_prefix, replicate, scene_run, turn))
        if (
            not any(packet["key"].startswith(f"{key_prefix}{scene_run['scene']}-r{replicate}-") for packet in packets)
            and scene_run.get("exit_cause") in {"forced", "timer"}
            and turns
        ):
            packets.append(_packet_for_turn(key_prefix, replicate, scene_run, turns[-1]))
    return packets


def _run_summary(replicate: str, scene_run: dict[str, Any]) -> dict[str, Any]:
    turns = _valid_turns(scene_run)
    stuck_turns = scene_run.get("stuck_turns")
    stuck_count = len(stuck_turns) if isinstance(stuck_turns, list) else 0
    return {
        "replicate": replicate,
        "scene": scene_run["scene"],
        "turns": len(turns),
        "stuck_turns": stuck_count,
        "rejected": sum(turn.get("rejected") is True for turn in turns),
        "game_breaks": sum(turn.get("game_break") is not None for turn in turns),
        "exit_cause": scene_run.get("exit_cause") if isinstance(scene_run.get("exit_cause"), str) else None,
        "transition_fired": scene_run.get("transition_fired") is True,
        "scenes": 1,
        "ending_reached": scene_run.get("ending_reached") is True,
    }


def playtest_summary(report: dict) -> dict:
    """Return deterministic per-scene and aggregate counts needed by the gate."""

    runs = [_run_summary(replicate, scene_run) for replicate, scene_run in _scene_runs(report)]
    return {
        "runs": runs,
        "turns": sum(run["turns"] for run in runs),
        "stuck_turns": sum(run["stuck_turns"] for run in runs),
        "rejected": sum(run["rejected"] for run in runs),
        "game_breaks": sum(run["game_breaks"] for run in runs),
        "exit_cause": [run["exit_cause"] for run in runs],
        "transition_fired": sum(run["transition_fired"] for run in runs),
        "scenes": len(runs),
        "ending_reached": any(run["ending_reached"] for run in runs),
    }


def _gate_passes(summary: dict) -> bool:
    runs = summary.get("runs")
    if not isinstance(runs, list) or not runs:
        return False
    return all(
        run.get("stuck_turns") == 0
        and run.get("rejected") == 0
        and run.get("game_breaks") == 0
        and run.get("transition_fired") is True
        and run.get("exit_cause") in EARNED_EXIT_CAUSES
        for run in runs
    )


def _summary_line(summary: dict, packets: list[dict]) -> str:
    line = (
        f"runs={summary.get('scenes', 0)} turns={summary.get('turns', 0)} "
        f"stuck={summary.get('stuck_turns', 0)} rejected={summary.get('rejected', 0)} "
        f"game_breaks={summary.get('game_breaks', 0)}"
    )
    if packets:
        line += " failing=" + ",".join(packet["key"] for packet in packets)
    return line


def _load_json(path: Path) -> dict | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _resolve(root: Path, value: object) -> Path:
    if not isinstance(value, (str, Path)):
        raise ValueError("path must be a string")
    path = Path(value)
    return path if path.is_absolute() else root / path


def _now() -> datetime:
    return datetime.now(UTC)


def _as_timestamp(value: datetime) -> float:
    if value.tzinfo is None or value.utcoffset() is None:
        value = value.replace(tzinfo=UTC)
    return value.timestamp()


def _next_midnight(now: datetime) -> datetime:
    if now.tzinfo is None or now.utcoffset() is None:
        now = now.replace(tzinfo=UTC)
    current = now.astimezone(UTC)
    return datetime.combine(current.date() + timedelta(days=1), time.min, tzinfo=UTC)


def _raise_quota(text: str, now: datetime) -> None:
    if any(marker in text.upper() for marker in ("AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED", "HTTP 429")):
        resume_at = _next_midnight(now)
        report = LimitReport("cloudflare", (), None, None)
        raise LimitSleep("cloudflare", resume_at) from ProviderLimit(resume_at, report)


def _fetch_version(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=20) as response:
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("version response must be an object")
    return value


def _default_runner(root: Path, payload: dict[str, Any], env: dict[str, str], timeout_s: int):
    if payload.get("billed_run_approved") is not True:
        raise RuntimeError("billed_run_approved must be true for the default live playtest runner")
    command = ["npm", "run", "test:e2e", "--", "--grep", "@blind-player"]
    return subprocess.run(
        command,
        cwd=root / "frontend",
        env=env,
        timeout=timeout_s,
        check=False,
        capture_output=True,
        text=True,
    )


def _fresh_report(root: Path, started_at: float) -> dict | None:
    artifact_dir = root / "artifacts"
    try:
        candidates = list(artifact_dir.glob("e2e-blind-player*.json"))
    except OSError:
        return None
    fresh: list[Path] = []
    for path in candidates:
        try:
            if path.is_file() and path.stat().st_mtime > started_at:
                fresh.append(path)
        except OSError:
            continue
    if not fresh:
        return None
    return _load_json(max(fresh, key=lambda path: path.stat().st_mtime))


def live_playtest_handler(
    root: Path | None = None,
    *,
    runner: Callable[[dict[str, str], int], Any] | None = None,
    fetch_version: Callable[[str], dict[str, Any]] | None = None,
    now_fn: Callable[[], datetime] = _now,
) -> StationHandler:
    """Return the station-7 grader with an injectable version fetch and runner."""

    repository_root = Path(root) if root is not None else Path(__file__).resolve().parents[2]

    def handle(ticket, now: datetime) -> StationResult:
        payload = getattr(ticket, "payload", None)
        if not isinstance(payload, dict):
            return StationResult(False, "live_playtest", "missing ticket payload", turns=None)
        scene = payload.get("scene", getattr(ticket, "scene", "1A"))
        if not isinstance(scene, str) or not scene:
            return StationResult(False, "live_playtest", "scene must be a non-empty string", turns=None)
        profile = payload.get("profile", _DEFAULT_PROFILE)
        if not isinstance(profile, str) or not profile:
            return StationResult(False, "live_playtest", "profile must be a non-empty string", turns=None)
        replicates = payload.get("replicates", 1)
        if isinstance(replicates, bool) or not isinstance(replicates, int) or replicates < 1:
            return StationResult(False, "live_playtest", "replicates must be a positive integer", turns=None)
        replicates = min(replicates, _MAX_REPLICATES)

        report_value = payload.get("report_path")
        if report_value is not None:
            try:
                report = _load_json(_resolve(repository_root, report_value))
            except ValueError as error:
                return StationResult(False, "live_playtest", str(error), turns=None)
            if report is None:
                return StationResult(False, "live_playtest", "could not read report", turns=None)
            summary = playtest_summary(report)
            if not summary["runs"]:
                return StationResult(False, "live_playtest", "report has no valid scene runs", turns=None)
            packets = report_to_packets(report)
            output = _summary_line(summary, packets)
            if _gate_passes(summary) and not packets:
                return StationResult(True, "live_playtest", output)
            return StationResult(False, "live_playtest", output, turns=packets or None)

        expected_sha = payload.get("expected_sha")
        if not isinstance(expected_sha, str) or not expected_sha:
            return StationResult(False, "live_playtest", "missing payload key: expected_sha", turns=None)
        if runner is None and payload.get("billed_run_approved") is not True:
            return StationResult(False, "live_playtest", "billed_run_approved must be true", turns=None)

        version_fetch = fetch_version or _fetch_version
        try:
            version = version_fetch(os.environ.get("E2E_API_BASE_URL", "").rstrip("/") + "/api/v1/version")
        except Exception as error:
            return StationResult(False, "live_playtest", f"could not read staging identity: {error}", turns=None)
        if (
            not isinstance(version, dict)
            or version.get("channel") != "staging"
            or version.get("runtime") != "scene-v1"
            or version.get("sha") != expected_sha
        ):
            return StationResult(False, "live_playtest", "staging identity mismatch", turns=None)

        started_at = _as_timestamp(now_fn())
        artifact_dir = repository_root / "artifacts"
        try:
            for path in artifact_dir.glob("e2e-blind-player*.json"):
                if path.is_file():
                    path.unlink()
        except OSError as error:
            return StationResult(False, "live_playtest", f"could not clear stale reports: {error}", turns=None)

        environment = os.environ.copy()
        environment.update(
            {
                "E2E_BLIND_SCENE": scene,
                "BLIND_PLAYER_PROFILE": profile,
                "E2E_BLIND_REPLICATES": str(replicates),
                "E2E_TURN_TIMEOUT_MS": _TURN_TIMEOUT_MS,
            }
        )
        run = runner or (lambda env, timeout_s: _default_runner(repository_root, payload, env, timeout_s))
        try:
            completed = run(environment, _RUN_TIMEOUT_S * replicates)
            combined = "\n".join(str(getattr(completed, field, "") or "") for field in ("stdout", "stderr"))
            _raise_quota(combined, now)
        except (LimitSleep, ProviderLimit):
            raise
        except Exception as error:
            _raise_quota(str(error), now)
            return StationResult(False, "live_playtest", f"runner failed: {error}", turns=None)

        if getattr(completed, "returncode", 0) != 0:
            return StationResult(False, "live_playtest", "live playtest runner failed", turns=None)
        report = _fresh_report(repository_root, started_at)
        if report is None:
            return StationResult(False, "live_playtest", "no fresh e2e-blind-player report", turns=None)
        summary = playtest_summary(report)
        if not summary["runs"]:
            return StationResult(False, "live_playtest", "fresh report has no valid scene runs", turns=None)
        packets = report_to_packets(report)
        output = _summary_line(summary, packets)
        if _gate_passes(summary) and not packets:
            return StationResult(True, "live_playtest", output)
        return StationResult(False, "live_playtest", output, turns=packets or None)

    return handle


def _select_scene(report: dict, scene: str | None) -> dict:
    if scene is None:
        return report
    selected: list[dict] = []
    for replicate in report.get("replicates", []) if isinstance(report.get("replicates"), list) else []:
        if not isinstance(replicate, dict):
            continue
        scenes = replicate.get("scenes")
        if isinstance(scenes, list):
            matching = [run for run in scenes if isinstance(run, dict) and run.get("scene") == scene]
            if matching:
                selected.append({**replicate, "scenes": matching})
        elif replicate.get("scene") == scene:
            selected.append(replicate)
    return {**report, "replicates": selected}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    grade = subparsers.add_parser("grade")
    grade.add_argument("report", metavar="REPORT.json")
    grade.add_argument("--scene")
    return parser


def main(argv: list[str] | None = None) -> int:
    """Grade a saved report without invoking the live runner."""

    options = _parser().parse_args(argv)
    report = _load_json(Path(options.report))
    if report is None:
        print("bad report input")
        return 2
    report = _select_scene(report, options.scene)
    summary = playtest_summary(report)
    if not summary["runs"]:
        print("report has no valid scene runs")
        return 2
    packets = report_to_packets(report)
    print(json.dumps({"summary": summary, "packets": packets}, indent=2, ensure_ascii=False))
    return 0 if _gate_passes(summary) and not packets else 1


if __name__ == "__main__":
    raise SystemExit(main())

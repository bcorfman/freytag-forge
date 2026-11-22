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
import contextlib
import json
import math
import os
import subprocess
import urllib.request
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, time, timedelta
from pathlib import Path
from typing import Any

from factory.cloudflare_spend import read_worker_budget, spend_between
from factory.guard import BudgetExhausted, Caps, LimitSleep, ProviderLimit, SpendLedger, Usage
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


def load_prices(path: str | Path) -> dict:
    """Load the model price table, returning an empty table when it is unreadable."""

    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError):
        return {}
    return value if isinstance(value, dict) else {}


def _nonnegative_number(value: object) -> bool:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return False
    try:
        return math.isfinite(float(value)) and value >= 0
    except (OverflowError, ValueError):
        return False


def _usage_values(player_usage: object) -> tuple[str, int, int, int, int] | None:
    if not isinstance(player_usage, dict) or not isinstance(player_usage.get("model"), str):
        return None
    fields = ("calls", "input_tokens", "cached_input_tokens", "output_tokens")
    if any(
        isinstance(player_usage.get(field), bool)
        or not isinstance(player_usage.get(field), int)
        or player_usage.get(field) < 0
        for field in fields
    ):
        return None
    return (
        player_usage["model"],
        player_usage["calls"],
        player_usage["input_tokens"],
        player_usage["cached_input_tokens"],
        player_usage["output_tokens"],
    )


def usage_cost_usd(player_usage: dict, prices: dict) -> float | None:
    """Calculate a player's usage cost from an explicit per-million-token price."""

    values = _usage_values(player_usage)
    if values is None or not isinstance(prices, dict):
        return None
    model, _calls, input_tokens, cached_input_tokens, output_tokens = values
    models = prices.get("models", prices)
    price = models.get(model) if isinstance(models, dict) else None
    if not isinstance(price, dict):
        return None
    fields = ("input", "cached_input", "output")
    if any(not _nonnegative_number(price.get(field)) for field in fields):
        return None
    cached_input_tokens = min(cached_input_tokens, input_tokens)
    return (
        (input_tokens - cached_input_tokens) * price["input"]
        + cached_input_tokens * price["cached_input"]
        + output_tokens * price["output"]
    ) / 1_000_000


def collect_player_usage(report: object) -> list[dict]:
    """Collect player usage from every scene run in either report shape."""

    return [
        scene_run["player_usage"]
        for _replicate, scene_run in _scene_runs(report)
        if isinstance(scene_run.get("player_usage"), dict)
    ]


def player_spend(report: object, prices: dict) -> tuple[float | None, int, int, int]:
    """Return ``(usd, tokens, calls, missing_runs)`` for all scene runs."""

    runs = _scene_runs(report)
    if not runs:
        return None, 0, 0, 0
    total_usd = 0.0
    total_tokens = 0
    total_calls = 0
    missing = 0
    for _replicate, scene_run in runs:
        usage = scene_run.get("player_usage")
        values = _usage_values(usage)
        cost = usage_cost_usd(usage, prices) if isinstance(usage, dict) else None
        if values is None or cost is None:
            missing += 1
        if values is not None:
            _model, calls, input_tokens, _cached_input_tokens, output_tokens = values
            total_calls += calls
            total_tokens += input_tokens + output_tokens
        if cost is not None:
            total_usd += cost
    return (None if missing else total_usd), total_tokens, total_calls, missing


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

    if "candidates_offered" in turn:
        offered = turn.get("candidates_offered")
        candidates: list[str] = []
        if isinstance(offered, list):
            for candidate in offered:
                if isinstance(candidate, str) and candidate not in candidates:
                    candidates.append(candidate)
        matched_candidate = turn.get("matched_candidate") if "matched_candidate" in turn else matched
        if not isinstance(matched_candidate, str):
            matched_candidate = None
        if matched_candidate is not None and matched_candidate not in candidates:
            candidates.append(matched_candidate)
        packet["candidates_offered"] = candidates
        packet["matched_candidate"] = matched_candidate
        return packet

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


def _summary_line(
    summary: dict,
    packets: list[dict],
    player_usd: float | None = None,
    player_calls: int = 0,
    cloudflare_usd: float | None = None,
) -> str:
    line = (
        f"runs={summary.get('scenes', 0)} turns={summary.get('turns', 0)} "
        f"stuck={summary.get('stuck_turns', 0)} rejected={summary.get('rejected', 0)} "
        f"game_breaks={summary.get('game_breaks', 0)}"
    )
    if player_usd is None:
        line += " openai spend unknown"
    else:
        line += f" openai ${player_usd:.4f} ({player_calls} calls)"
    if cloudflare_usd is None:
        line += " cloudflare spend unknown"
    else:
        line += f" cloudflare ${cloudflare_usd:.4f}"
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


def _factory_config(root: Path) -> dict[str, Any]:
    config_path = root / "factory/config/factory.json"
    if not config_path.is_file():
        config_path = Path(__file__).resolve().parents[2] / "factory/config/factory.json"
    return _load_json(config_path) or {}


def _prices_for_root(root: Path) -> dict:
    prices_path = root / "factory/config/prices.json"
    if not prices_path.is_file():
        prices_path = Path(__file__).resolve().parents[2] / "factory/config/prices.json"
    return load_prices(prices_path)


def _utc_day(value: datetime):
    current = value if value.tzinfo is not None and value.utcoffset() is not None else value.replace(tzinfo=UTC)
    return current.astimezone(UTC).date()


def _pre_run_budget_gate(ledger: SpendLedger, caps: Caps, now: datetime) -> str | None:
    if ledger.total_usd() >= caps.total_budget_usd:
        raise BudgetExhausted("total model budget exhausted")
    rate_usd = ledger.usd_in_window(now, caps.rate_window_s)
    if rate_usd > caps.rate_max_usd:
        raise BudgetExhausted(f"rate-of-spend breaker exceeded: {rate_usd} USD in {caps.rate_window_s} seconds")

    utc_day = _utc_day(now)
    for provider in ("openai", "cloudflare"):
        daily_cap = caps.daily_cap_usd.get(provider)
        if daily_cap is None:
            return f"missing daily cap for {provider}"
        if ledger.day_usd(provider, utc_day) >= daily_cap:
            raise LimitSleep(provider, _next_midnight(now))
    return None


def _record_player_spend(
    ledger: SpendLedger,
    report: dict | None,
    prices: dict,
    *,
    now: datetime,
    scene: str,
    ticket_id: str,
) -> tuple[float | None, int, int]:
    model_id = "gpt-5.6-luna"
    if report is not None:
        usages = collect_player_usage(report)
        for usage in usages:
            if isinstance(usage.get("model"), str) and usage["model"]:
                model_id = usage["model"]
                break
    if report is None or not _scene_runs(report):
        spend, tokens, calls = None, 0, 0
    else:
        spend, tokens, calls, _missing = player_spend(report, prices)
    ledger.record(
        Usage(
            at=now,
            provider="openai",
            model_id=model_id,
            station="live_playtest",
            scene=scene,
            ticket_id=ticket_id,
            tokens=tokens,
            usd=spend,
            cost_kind="dollars" if spend is not None else "unknown",
        )
    )
    return spend, tokens, calls


def _safe_budget_read(read_budget: Callable[[], dict | None]) -> dict | None:
    try:
        reading = read_budget()
    except Exception:
        return None
    return reading if isinstance(reading, dict) else None


def _record_cloudflare_spend(
    ledger: SpendLedger,
    before: dict | None,
    after: dict | None,
    *,
    now: datetime,
    scene: str,
    ticket_id: str,
) -> int | None:
    micro_usd = spend_between(before, after)
    ledger.record(
        Usage(
            at=now,
            provider="cloudflare",
            model_id="workers-ai",
            station="live_playtest",
            scene=scene,
            ticket_id=ticket_id,
            tokens=0,
            usd=micro_usd / 1_000_000 if micro_usd is not None else None,
            cost_kind="dollars" if micro_usd is not None else "unknown",
        )
    )
    return micro_usd


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


def _staged_lock_path(root: Path) -> Path:
    return root / "factory/state/staged_run.lock"


def _fresh_staged_lock(path: Path, now: datetime) -> bool:
    try:
        age = _as_timestamp(now) - path.stat().st_mtime
    except OSError:
        return False
    return age < timedelta(hours=6).total_seconds()


def live_playtest_handler(
    root: Path | None = None,
    *,
    runner: Callable[[dict[str, str], int], Any] | None = None,
    fetch_version: Callable[[str], dict[str, Any]] | None = None,
    now_fn: Callable[[], datetime] = _now,
    ledger: SpendLedger | None = None,
    read_budget: Callable[[], dict | None] = read_worker_budget,
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
            from factory.stations.probe import runs_from_report

            runs = runs_from_report(report, scene)
            payload_updates = {"runs": runs} if runs else None
            packets = report_to_packets(report)
            spend, _tokens, calls, _missing = player_spend(report, _prices_for_root(repository_root))
            output = _summary_line(summary, packets, spend, calls)
            if _gate_passes(summary) and not packets:
                return StationResult(True, "live_playtest", output, payload_updates=payload_updates)
            return StationResult(False, "live_playtest", output, turns=packets or None, payload_updates=payload_updates)

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

        config = _factory_config(repository_root)
        try:
            caps = Caps.from_dict(config["caps"])
            configured_ledger = ledger or SpendLedger(_resolve(repository_root, config["paths"]["ledger"]))
        except (KeyError, TypeError, ValueError) as error:
            return StationResult(False, "live_playtest", f"invalid factory budget configuration: {error}", turns=None)
        budget_error = _pre_run_budget_gate(configured_ledger, caps, now)
        if budget_error is not None:
            return StationResult(False, "live_playtest", budget_error, turns=None)

        prices = _prices_for_root(repository_root)
        ticket_id = str(getattr(ticket, "id", ""))

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
        budget_before = _safe_budget_read(read_budget)
        lock_path = _staged_lock_path(repository_root)
        if lock_path.exists() and _fresh_staged_lock(lock_path, now):
            return StationResult(False, "live_playtest", "staged run already in progress", turns=None)
        try:
            lock_path.parent.mkdir(parents=True, exist_ok=True)
            lock_path.write_text(f"{ticket_id}\n{now.isoformat()}\n", encoding="utf-8")
        except OSError as error:
            return StationResult(False, "live_playtest", f"could not create staged run lock: {error}", turns=None)
        try:
            try:
                completed = run(environment, _RUN_TIMEOUT_S * replicates)
            except (LimitSleep, ProviderLimit):
                budget_after = _safe_budget_read(read_budget)
                _record_player_spend(
                    configured_ledger,
                    _fresh_report(repository_root, started_at),
                    prices,
                    now=now,
                    scene=scene,
                    ticket_id=ticket_id,
                )
                _record_cloudflare_spend(
                    configured_ledger,
                    budget_before,
                    budget_after,
                    now=now,
                    scene=scene,
                    ticket_id=ticket_id,
                )
                raise
            except Exception as error:
                budget_after = _safe_budget_read(read_budget)
                _record_player_spend(
                    configured_ledger,
                    _fresh_report(repository_root, started_at),
                    prices,
                    now=now,
                    scene=scene,
                    ticket_id=ticket_id,
                )
                _record_cloudflare_spend(
                    configured_ledger,
                    budget_before,
                    budget_after,
                    now=now,
                    scene=scene,
                    ticket_id=ticket_id,
                )
                _raise_quota(str(error), now)
                return StationResult(False, "live_playtest", f"runner failed: {error}", turns=None)
        finally:
            with contextlib.suppress(OSError):
                lock_path.unlink()

        budget_after = _safe_budget_read(read_budget)
        try:
            combined = "\n".join(str(getattr(completed, field, "") or "") for field in ("stdout", "stderr"))
            _raise_quota(combined, now)
        except (LimitSleep, ProviderLimit):
            _record_player_spend(
                configured_ledger,
                _fresh_report(repository_root, started_at),
                prices,
                now=now,
                scene=scene,
                ticket_id=ticket_id,
            )
            _record_cloudflare_spend(
                configured_ledger,
                budget_before,
                budget_after,
                now=now,
                scene=scene,
                ticket_id=ticket_id,
            )
            raise
        except Exception as error:
            _record_player_spend(
                configured_ledger,
                _fresh_report(repository_root, started_at),
                prices,
                now=now,
                scene=scene,
                ticket_id=ticket_id,
            )
            _record_cloudflare_spend(
                configured_ledger,
                budget_before,
                budget_after,
                now=now,
                scene=scene,
                ticket_id=ticket_id,
            )
            _raise_quota(str(error), now)
            return StationResult(False, "live_playtest", f"runner failed: {error}", turns=None)

        report = _fresh_report(repository_root, started_at)
        spend, _tokens, calls = _record_player_spend(
            configured_ledger,
            report,
            prices,
            now=now,
            scene=scene,
            ticket_id=ticket_id,
        )
        micro_usd = _record_cloudflare_spend(
            configured_ledger,
            budget_before,
            budget_after,
            now=now,
            scene=scene,
            ticket_id=ticket_id,
        )
        if getattr(completed, "returncode", 0) != 0:
            return StationResult(False, "live_playtest", "live playtest runner failed", turns=None)
        if report is None:
            return StationResult(False, "live_playtest", "no fresh e2e-blind-player report", turns=None)
        summary = playtest_summary(report)
        if not summary["runs"]:
            return StationResult(False, "live_playtest", "fresh report has no valid scene runs", turns=None)
        from factory.stations.probe import runs_from_report

        runs = runs_from_report(report, scene)
        payload_updates = {"runs": runs} if runs else None
        packets = report_to_packets(report)
        output = _summary_line(
            summary,
            packets,
            spend,
            calls,
            micro_usd / 1_000_000 if micro_usd is not None else None,
        )
        if _gate_passes(summary) and not packets:
            return StationResult(True, "live_playtest", output, payload_updates=payload_updates)
        return StationResult(False, "live_playtest", output, turns=packets or None, payload_updates=payload_updates)

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

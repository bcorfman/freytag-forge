"""Validate a delivery report.

The report shape is ``{"candidate_sha": str, "turn_ceiling": int,
"total_turns": int, "replicates": [R, ...]}``.  Each replicate R contains
``replicate``, ``profile`` (``canonical`` or ``raw``), ``status``
(``complete`` or ``failed``), nine scene records, ``ending_reached``, an
``epilogue`` with ``offered``/``taken``, and ``continuity``/``fun`` objects
with ``passed`` booleans.  A scene contains its scene id, entry provenance,
exit fact hash, transition cause, turn count, and a classify_run result.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any


def _problem(code: str, replicate: int | None, scene: str | None, detail: str) -> dict[str, Any]:
    return {"code": code, "replicate": replicate, "scene": scene, "detail": detail}


def validate_final_report(
    report: Any,
    *,
    expected_replicates: int = 12,
    scene_order: Sequence[str] = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C"),
) -> dict[str, Any]:
    problems: list[dict[str, Any]] = []
    if not isinstance(report, dict):
        return {
            "ok": False,
            "problems": [_problem("malformed", None, None, "report must be an object")],
            "replicates_checked": 0,
        }
    replicates = report.get("replicates")
    if not isinstance(replicates, list):
        return {
            "ok": False,
            "problems": [_problem("malformed", None, None, "replicates must be a list")],
            "replicates_checked": 0,
        }
    if not isinstance(report.get("turn_ceiling"), int) or isinstance(report["turn_ceiling"], bool):
        problems.append(_problem("malformed", None, None, "turn_ceiling must be an integer"))
    if not isinstance(report.get("total_turns"), int) or isinstance(report["total_turns"], bool):
        problems.append(_problem("malformed", None, None, "total_turns must be an integer"))
    numbers: list[int] = []
    for item in replicates:
        if (
            isinstance(item, dict)
            and isinstance(item.get("replicate"), int)
            and not isinstance(item.get("replicate"), bool)
        ):
            numbers.append(item["replicate"])
    if len(replicates) != expected_replicates or len(numbers) != len(set(numbers)):
        problems.append(_problem("replicate_count", None, None, "replicate count or numbers are invalid"))
    total = 0
    for raw in replicates:
        if not isinstance(raw, dict):
            problems.append(_problem("malformed", None, None, "replicate must be an object"))
            continue
        rep = raw.get("replicate") if isinstance(raw.get("replicate"), int) else None
        scenes = raw.get("scenes")
        if raw.get("status") != "complete":
            problems.append(_problem("failed_replicate", rep, None, "replicate is not complete"))
        if not isinstance(scenes, list):
            problems.append(_problem("malformed", rep, None, "scenes must be a list"))
            continue
        ids = [s.get("scene") for s in scenes if isinstance(s, dict)]
        if ids != list(scene_order):
            problems.append(_problem("partial_scenes", rep, None, "scene list does not match the required order"))
        previous_exit = None
        for index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                problems.append(_problem("malformed", rep, None, "scene must be an object"))
                continue
            sid = scene.get("scene") if isinstance(scene.get("scene"), str) else None
            entry, contract = scene.get("entry"), scene.get("contract")
            required = ("entry", "exit_facts_sha256", "transition_cause", "turns", "contract")
            if (
                any(key not in scene for key in required)
                or not isinstance(entry, dict)
                or not isinstance(contract, dict)
            ):
                problems.append(_problem("malformed", rep, sid, "scene is missing required fields"))
                continue
            turns = scene["turns"]
            if not isinstance(turns, int) or isinstance(turns, bool):
                problems.append(_problem("malformed", rep, sid, "turns must be an integer"))
                turns = 0
            total += turns
            source, entry_hash = entry.get("source"), entry.get("facts_sha256")
            exit_hash = scene.get("exit_facts_sha256")
            if (
                (index == 0 and source != "fresh")
                or (index > 0 and source != "carried")
                or (index > 0 and entry_hash != previous_exit)
            ):
                problems.append(_problem("substituted_snapshot", rep, sid, "scene entry provenance is invalid"))
            previous_exit = exit_hash
            cause, exit_value = scene.get("transition_cause"), contract.get("exit")
            if index < len(scene_order) - 1 and (cause in {"forced", "timer"} or exit_value in {"forced", "timer"}):
                problems.append(_problem("forced_exit", rep, sid, "scene forced or timed out"))
            if (
                cause == "unknown"
                or exit_value == "unknown"
                or (index < len(scene_order) - 1 and (cause == "none" or exit_value != "earned"))
                or (index == len(scene_order) - 1 and cause != "none")
            ):
                problems.append(_problem("unknown_cause", rep, sid, "scene transition cause is invalid"))
            if contract.get("confirmed_stuck"):
                problems.append(_problem("stuck_turns", rep, sid, "confirmed stuck turns reported"))
            if contract.get("unresolved"):
                problems.append(_problem("unresolved", rep, sid, "unresolved cases reported"))
            if (
                index == len(scene_order) - 1
                and exit_value != "ending"
                or index < len(scene_order) - 1
                and exit_value == "ending"
                or raw.get("ending_reached") is not True
            ):
                problems.append(_problem("false_terminal", rep, sid, "ending state is invalid"))
        epilogue = raw.get("epilogue")
        if not isinstance(epilogue, dict) or epilogue.get("offered") is not True:
            problems.append(_problem("epilogue_not_offered", rep, None, "epilogue was not offered"))
        continuity = raw.get("continuity")
        fun = raw.get("fun")
        if not isinstance(continuity, dict) or continuity.get("passed") is not True:
            problems.append(_problem("continuity_failed", rep, None, "continuity gate failed"))
        if not isinstance(fun, dict) or fun.get("passed") is not True:
            problems.append(_problem("fun_failed", rep, None, "fun gate failed"))
    if (
        isinstance(report.get("total_turns"), int)
        and total != report["total_turns"]
        or isinstance(report.get("turn_ceiling"), int)
        and total > report["turn_ceiling"]
    ):
        problems.append(_problem("turn_ceiling", None, None, "turn total or ceiling is invalid"))
    return {"ok": not problems, "problems": problems, "replicates_checked": len(replicates)}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("--replicates", type=int, default=12)
    args = parser.parse_args(argv)
    try:
        report = json.loads(Path(args.file).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        print(f"unable to read report: {exc}", file=sys.stderr)
        return 2
    result = validate_final_report(report, expected_replicates=args.replicates)
    for item in result["problems"]:
        print(f"{item['code']} {item['replicate']} {item['scene']}: {item['detail']}")
    print("ok" if result["ok"] else f"FAILED {len(result['problems'])} problems")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

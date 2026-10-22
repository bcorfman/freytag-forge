"""Validate Stage 7 3C recall replay artifacts without network access."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _read_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} is not a JSON object")
    return value


def _failure_file(out: Path) -> Path | None:
    for path in (out / "failure.txt", out / "run-failure.txt", out / "run-failure" / "failure.txt"):
        if path.is_file():
            return path
    return None


def _rows(out: Path) -> list[dict[str, object]]:
    path = out / "rows.jsonl"
    rows: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"rows.jsonl line {line_number} is not an object")
        rows.append(value)
    return rows


def check(out: Path, n: int, mode: str, experiment: str = "c1") -> list[str]:
    errors: list[str] = []
    if experiment not in {"c1", "broadcast"}:
        return [f"unknown experiment: {experiment}"]
    second_arm = "broadcast" if experiment == "broadcast" else "recall"
    summary_path = out / "summary.json"
    if mode == "dry":
        second_name = f"{second_arm}-request.json"
        for name in ("pump-request.json", second_name, "request.diff", "summary.json", "failure.txt"):
            if not (out / name).is_file():
                errors.append(f"missing {name}")
        if errors:
            return errors
        summary = _read_json(summary_path)
        if experiment == "broadcast":
            arms = summary.get("arms")
            if not isinstance(arms, dict) or set(arms) != {"pump", "broadcast"}:
                errors.append("dry summary arms are not pump and broadcast")
        if summary.get("requests") != 0:
            errors.append("dry summary requests is not 0")
        isolation = summary.get("isolation")
        if not isinstance(isolation, dict) or isolation.get("pump_equals_recording") is not True:
            errors.append("dry isolation pump_equals_recording is not true")
        trace_key = "broadcast_trace_remaining" if experiment == "broadcast" else "recall_old_c1_remaining"
        if not isinstance(isolation, dict) or isolation.get(trace_key) is not False:
            errors.append(f"dry isolation {trace_key} is not false")
        if summary.get("replacement_occurrences") != 3:
            errors.append("dry replacement_occurrences is not 3")
        return errors

    for name in ("rows.jsonl", "summary.json"):
        if not (out / name).is_file():
            errors.append(f"missing {name}")
    if errors:
        return errors
    try:
        rows = _rows(out)
        summary = _read_json(summary_path)
    except Exception as error:  # noqa: BLE001 - report malformed artifacts
        return [f"could not read artifacts: {error}"]

    failed = _failure_file(out) is not None
    expected = 2 * n
    if not failed and len(rows) != expected:
        errors.append(f"expected {expected} rows without failure file, found {len(rows)}")
    if len(rows) > expected:
        errors.append(f"artifact rows exceed expected maximum {expected}")
    expected_arms = [arm for _index in range(n) for arm in ("pump", second_arm)]
    if [row.get("arm") for row in rows] != expected_arms[: len(rows)]:
        errors.append("rows are not alternating pump, recall")
    for position, row in enumerate(rows):
        if row.get("arm") not in {"pump", second_arm}:
            errors.append(f"row {position} has an invalid arm")
        if row.get("index") != position // 2:
            errors.append(f"row {position} has the wrong index")
        if not isinstance(row.get("request_count"), int) or row["request_count"] not in {1, 2}:
            errors.append(f"row {position} request_count is not 1 or 2")
        if not isinstance(row.get("raw_reply_text"), str):
            errors.append(f"row {position} is missing raw_reply_text")
    request_sum = sum(row.get("request_count", 0) for row in rows if isinstance(row.get("request_count"), int))
    if summary.get("requests") != request_sum:
        errors.append("summary requests does not equal row request counts")
    cap = summary.get("max_requests")
    if not isinstance(cap, int):
        errors.append("summary does not record an integer max_requests cap")
    elif request_sum > cap:
        errors.append("request sum exceeds the summary max_requests cap")
    if summary.get("semantic_judge_calls") != 0:
        errors.append("semantic-judge calls are not zero")
    if summary.get("player_model_calls") != 0:
        errors.append("player-model calls are not zero")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("n_per_arm", type=int)
    parser.add_argument("--mode", choices=("dry", "artifacts"), required=True)
    parser.add_argument("--experiment", choices=("c1", "broadcast"), default="c1")
    args = parser.parse_args()
    try:
        errors = (
            ["n_per_arm must be positive"]
            if args.n_per_arm < 1
            else check(args.out, args.n_per_arm, args.mode, args.experiment)
        )
    except Exception as error:  # noqa: BLE001 - checker must explain every failure
        errors = [f"checker failed: {error}"]
    if errors:
        for error in errors:
            print(f"WHY: {error}", file=sys.stderr)
        return 1
    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

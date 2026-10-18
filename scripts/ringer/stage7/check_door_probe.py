"""Offline validation for dry and live Stage 7 door-probe artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from door_continuation import _matches_all
from door_prompt import ARMS, patch_prompt, select_prompt

from bench.core import ledger_rows


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _spend(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _check_rows(rows: list[dict[str, Any]], n: int, live: bool, errors: list[str]) -> None:
    expected = len(ARMS) * n
    if len(rows) != expected:
        errors.append(f"results.json: expected {expected} rows, found {len(rows)}")
    expected_order = [(rep, arm) for rep in range(1, n + 1) for arm in ARMS]
    if [(row.get("rep"), row.get("arm")) for row in rows] != expected_order:
        errors.append("results.json: rows are not unique rep-major rows in the required arm order")
    if len({row.get("row_id") for row in rows}) != len(rows):
        errors.append("results.json: row_id values are not unique")
    for row in rows:
        if not live:
            continue
        commands = row.get("commands", [row.get("command")] if row.get("command") is not None else [])
        if not isinstance(commands, list) or len(commands) > 2:
            errors.append(f"{row.get('row_id')}: more than two continuation commands")
        turns = row.get("continuation", {}).get("turns", [])
        if len(turns) > 2:
            errors.append(f"{row.get('row_id')}: continuation has more than two turn records")
        for index, turn in enumerate(turns):
            eligible = turn.get("eligible", [])
            matched = turn.get("matched", [])
            evidence = turn.get("evidence", {})
            if not isinstance(eligible, list) or not isinstance(matched, list):
                errors.append(f"{row.get('row_id')}: turn {index + 1} lacks eligible/matched lists")
                continue
            recomputed = sorted(
                identifier
                for identifier in eligible
                if identifier in evidence
                and _matches_all(tuple(tuple(group) for group in evidence[identifier]), turn.get("command", ""))
            )
            if recomputed != sorted(matched):
                errors.append(f"{row.get('row_id')}: turn {index + 1} matcher result differs from saved evidence")


def check(out: Path, n: int, mode: str) -> list[str]:
    errors: list[str] = []
    required = (
        "run.json",
        "prompts",
        "results.json",
        "spend.jsonl",
        "summary.json",
        "source-before.json",
        "source-after.json",
        "verdicts",
        "notes.md",
    )
    for name in required:
        if not (out / name).exists():
            errors.append(f"{out / name}: missing required artifact")
    if errors:
        return errors
    try:
        run, results, summary = (_read(out / name) for name in ("run.json", "results.json", "summary.json"))
        rows = results.get("rows", [])
        events = _spend(out / "spend.jsonl")
    except Exception as exc:
        return [f"{out}: malformed artifact: {exc}"]
    live = mode != "dry"
    if mode == "dry" and run.get("mode") != "dry":
        errors.append("run.json: expected dry mode for dry checker")
    if live and run.get("mode") != "live":
        errors.append("run.json: expected live mode for artifacts checker")
    _check_rows(rows, n, live, errors)
    expected = len(ARMS) * n
    if summary.get("n") != n or summary.get("rows", summary.get("planned_rows")) != len(rows):
        errors.append("summary.json: row count disagrees with N/results")
    if mode == "dry" and summary.get("planned_rows") != expected:
        errors.append("summary.json: planned_rows disagrees with N")
    if live:
        experiment_id = run.get("experiment_id")
        if not experiment_id or summary.get("experiment_id") != experiment_id:
            errors.append("summary/run: experiment_id does not reconcile")
        cloudflare = sum(event.get("kind") == "cloudflare" for event in events)
        players = sum(event.get("kind") == "raw_player" for event in events)
        if summary.get("cloudflare_requests") != cloudflare:
            errors.append("summary.json: cloudflare_requests disagrees with spend events")
        if summary.get("raw_player_attempts") != players:
            errors.append("summary.json: raw_player_attempts disagrees with spend events")
        caps = summary.get("caps", {})
        if cloudflare > caps.get("cloudflare", -1) or players > caps.get("player", -1):
            errors.append("summary.json: spend exceeds request or player cap")
        ledger_path = Path(run.get("ledger_path", "bench/results/ledger.jsonl"))
        if not ledger_path.exists():
            errors.append("ledger: configured ledger path is missing")
        else:
            matching = [row for row in ledger_rows(ledger_path) if row.get("experiment_id") == experiment_id]
            if not matching:
                errors.append("ledger: experiment_id is missing")
            elif (
                matching[-1].get("cloudflare_requests") != cloudflare
                or matching[-1].get("raw_player_attempts") != players
            ):
                errors.append("ledger: spend counts do not reconcile")
    selection = select_prompt()
    source = _read(out / "source-before.json")
    prompts = source.get("prompts", {})
    for arm in ("control", "review", "stale-scene", "wording"):
        expected_prompt = patch_prompt(selection, arm)
        if prompts.get(arm, {}).get("hashes") != expected_prompt["hashes"]:
            errors.append(f"prompts/{arm}: prompt hashes differ from fixture")
    if mode == "reviewed":
        for row in rows:
            verdict = out / "verdicts" / f"{row['row_id']}.json"
            if not verdict.exists():
                errors.append(f"{verdict}: missing review verdict")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("n", type=int)
    parser.add_argument("--mode", choices=("dry", "artifacts", "reviewed"), required=True)
    args = parser.parse_args()
    errors = check(args.out, args.n, args.mode)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"door probe {args.mode} artifacts valid: {len(ARMS) * args.n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

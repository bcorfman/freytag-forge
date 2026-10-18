"""Offline validation for dry and live Stage 7 door-probe artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from door_continuation import _matches_all
from door_probe import EXPERIMENTS, ROOT, _package_bridge_material
from door_prompt import THINGS_ASSUMPTION, patch_prompt, select_prompt

from bench.core import ledger_rows


def _read(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _spend(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _check_rows(rows: list[dict[str, Any]], n: int, live: bool, arms: tuple[str, ...], errors: list[str]) -> None:
    expected = len(arms) * n
    if len(rows) != expected:
        errors.append(f"results.json: expected {expected} rows, found {len(rows)}")
    expected_order = [(rep, arm) for rep in range(1, n + 1) for arm in arms]
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


def _canonical_row_hash(row: dict[str, Any]) -> str:
    body = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


POSITIVE_FIELDS = (
    "upstream_invention",
    "downstream_new_invention",
    "inherited_invention",
    "player_pursuit",
    "premature_disclosure",
    "contradictory_delivery",
)
REVIEW_FIELDS = POSITIVE_FIELDS + ("earned_by_command_2",)


def _row_text(row: dict[str, Any]) -> str:
    values = [row.get("screen", ""), row.get("responses", []), row.get("commands", [])]
    return json.dumps(values, ensure_ascii=False)


def _check_reviewed(out: Path, rows: list[dict[str, Any]], n: int, arms: tuple[str, ...], errors: list[str]) -> None:
    verdicts: dict[str, dict[str, Any]] = {}
    for row in rows:
        path = out / "verdicts" / f"{row['row_id']}.json"
        if not path.exists():
            errors.append(f"{path}: missing review verdict")
            continue
        try:
            verdict = _read(path)
        except Exception as exc:
            errors.append(f"{path}: malformed verdict: {exc}")
            continue
        verdicts[row["row_id"]] = verdict
        if verdict.get("row_id") != row["row_id"]:
            errors.append(f"{path}: row_id field does not match row")
        if verdict.get("row_hash") != _canonical_row_hash(row):
            errors.append(f"{path}: row_hash field does not match canonical row")
        if not isinstance(verdict.get("reviewer"), str) or not verdict["reviewer"]:
            errors.append(f"{path}: reviewer field must be a nonempty string")
        evidence = verdict.get("evidence")
        if not isinstance(evidence, dict):
            errors.append(f"{path}: evidence field must be an object")
            evidence = {}
        text = _row_text(row)
        fields = REVIEW_FIELDS
        grounded_fields = (
            "declared_panel_used",
            "invented_access_object",
            "reached_archive_without_new_credential",
        )
        if out.joinpath("run.json").exists() and _read(out / "run.json").get("experiment") == "grounded":
            fields = fields + grounded_fields
        for field in fields:
            value = verdict.get(field)
            if field in grounded_fields:
                if type(value) is not bool:
                    errors.append(f"{path}: {field} field must be true or false")
            elif value not in (True, False, "needs_review"):
                errors.append(f"{path}: {field} field must be true, false, or needs_review")
            if value is True and field in POSITIVE_FIELDS:
                quote = evidence.get(field)
                if not isinstance(quote, str) or not quote or quote not in text:
                    errors.append(f"{path}: evidence.{field} must be a nonempty exact quote in row text")
        earned = any(turn.get("status") == "earned" for turn in row.get("continuation", {}).get("turns", [])[:2])
        if verdict.get("earned_by_command_2") is not earned:
            errors.append(f"{path}: earned_by_command_2 field disagrees with continuation turns")
    if errors:
        return
    grounded = _read(out / "run.json").get("experiment") == "grounded"
    count_fields = ("earned", "unsupported_access", "premature_disclosure", "contradictory_delivery")
    if grounded:
        count_fields += (
            "declared_panel_used",
            "invented_access_object",
            "reached_archive_without_new_credential",
            "door_appears",
        )
    counts = {arm: {field: 0 for field in count_fields} for arm in arms}
    for row in rows:
        verdict = verdicts[row["row_id"]]
        arm_counts = counts[row["arm"]]
        if verdict["earned_by_command_2"]:
            arm_counts["earned"] += 1
        if any(
            verdict[field] is True for field in ("upstream_invention", "downstream_new_invention", "player_pursuit")
        ):
            arm_counts["unsupported_access"] += 1
        if verdict["premature_disclosure"] is True:
            arm_counts["premature_disclosure"] += 1
        if verdict["contradictory_delivery"] is True:
            arm_counts["contradictory_delivery"] += 1
        if grounded:
            for field in (
                "declared_panel_used",
                "invented_access_object",
                "reached_archive_without_new_credential",
            ):
                if verdict[field] is True:
                    arm_counts[field] += 1
            if verdict["declared_panel_used"] is True or verdict["invented_access_object"] is True:
                arm_counts["door_appears"] += 1
    summary_path = out / "review-summary.json"
    if not summary_path.exists():
        return
    try:
        review_summary = _read(summary_path)
    except Exception as exc:
        errors.append(f"{summary_path}: malformed review summary: {exc}")
        return
    saved = review_summary.get("arms")
    if not isinstance(saved, dict):
        errors.append(f"{summary_path}: arms field must be an object")
        return
    for arm in arms:
        entry = saved.get(arm)
        if not isinstance(entry, dict):
            errors.append(f"{summary_path}: arms.{arm} field is missing or not an object")
            continue
        for field, value in counts[arm].items():
            if entry.get(field) != value:
                errors.append(f"{summary_path}: arms.{arm}.{field} disagrees with verdicts")
        decision = entry.get("decision")
        if n != 12:
            expected_decision = "not_decided"
        else:
            control_earned = counts["control"]["earned"]
            if grounded:
                expected_decision = (
                    "wins"
                    if arm == "grounded"
                    and counts[arm]["reached_archive_without_new_credential"] >= 10
                    and counts[arm]["earned"] >= 10
                    and counts[arm]["invented_access_object"] <= 2
                    and counts[arm]["premature_disclosure"] == 0
                    and counts[arm]["contradictory_delivery"] == 0
                    and counts[arm]["earned"] >= control_earned + 3
                    else "does_not_win"
                )
            else:
                expected_decision = (
                    "wins"
                    if counts[arm]["earned"] >= 10
                    and counts[arm]["unsupported_access"] <= 2
                    and counts[arm]["premature_disclosure"] == 0
                    and counts[arm]["contradictory_delivery"] == 0
                    and counts[arm]["earned"] > control_earned
                    else "does_not_win"
                )
        if decision != expected_decision:
            errors.append(f"{summary_path}: arms.{arm}.decision disagrees with screen rule")


def _check_completion(source: dict[str, Any], rows: list[dict[str, Any]], live: bool, errors: list[str]) -> None:
    prompts = source.get("prompts", {})
    control = prompts.get("control", {})
    no_finish = prompts.get("no-finish", {})
    line = "Finish each action the player gives.\n"
    control_system = control.get("system")
    no_finish_system = no_finish.get("system")
    if not isinstance(control_system, str) or not isinstance(no_finish_system, str):
        errors.append("completion prompts: control and no-finish systems must be strings")
        return
    if control.get("hashes", {}).get("system") != control.get("hashes", {}).get("original_system"):
        errors.append("completion control: system hash differs from original_system hash")
    if control_system.count(line) != 1:
        errors.append("completion control: finish instruction does not occur exactly once")
    if no_finish.get("original_system") != control.get("original_system"):
        errors.append("completion: original systems differ across arms")
    expected_no_finish = control_system.replace(line, "", 1)
    if no_finish_system != expected_no_finish:
        errors.append("completion no-finish: system is not exactly control minus the finish instruction")
    if no_finish.get("system_diff") == control.get("system_diff"):
        errors.append("completion no-finish: system diff is not distinct from control")
    for field in ("user", "original_user"):
        if control.get("hashes", {}).get(field) != no_finish.get("hashes", {}).get(field):
            errors.append(f"completion: {field} hashes differ across arms")
    bridge = source.get("bridge", {})
    if not isinstance(bridge.get("bridge"), str) or not isinstance(bridge.get("entry"), str):
        errors.append("completion: bridge and entry must be strings")
    if live:
        fixed = bridge.get("fixed")
        if not isinstance(fixed, str):
            errors.append("completion: fixed bridge/entry suffix is missing")
        else:
            for row in rows:
                if not isinstance(row.get("screen"), str) or not row["screen"].endswith(fixed):
                    errors.append(f"{row.get('row_id')}: authored bridge/entry differs from completion control")


def _check_grounded(source: dict[str, Any], errors: list[str]) -> None:
    prompts = source.get("prompts", {})
    control = prompts.get("control", {})
    grounded = prompts.get("grounded", {})
    if source.get("things_assumption") != THINGS_ASSUMPTION:
        errors.append("grounded: things_assumption is missing or incorrect")
    if grounded.get("things_assumption") != THINGS_ASSUMPTION:
        errors.append("grounded prompt: things_assumption is missing or incorrect")
    if control.get("user") != control.get("original_user"):
        errors.append("grounded control: user differs from original_user")
    if grounded.get("original_user") != control.get("original_user"):
        errors.append("grounded: original users differ across arms")
    if control.get("system") != grounded.get("system"):
        errors.append("grounded: system prompts differ across arms")
    if control.get("hashes", {}).get("system") != control.get("hashes", {}).get("original_system"):
        errors.append("grounded control: system hash differs from original_system hash")
    if grounded.get("hashes", {}).get("system") != grounded.get("hashes", {}).get("original_system"):
        errors.append("grounded: system hash differs from original_system hash")
    expected = patch_prompt(select_prompt(), "grounded", "grounded")
    if grounded.get("user") != expected["user"] or grounded.get("diff") != expected["diff"]:
        errors.append("grounded: user is not exactly the derived THINGS/SCENE/CONSTRAINTS additions")
    if grounded.get("diff") == control.get("diff"):
        errors.append("grounded: user diff is not distinct from control")
    bridges = source.get("bridges")
    if not isinstance(bridges, dict):
        errors.append("grounded: per-arm bridge material is missing")
        return
    prefix = source.get("bridge", {}).get("prefix")
    if not isinstance(prefix, str):
        errors.append("grounded: recorded narrator prefix is missing")
        return
    for arm in EXPERIMENTS["grounded"]["arms"]:
        saved = bridges.get(arm)
        if not isinstance(saved, dict):
            errors.append(f"grounded: bridge material for {arm} is missing")
            continue
        path = ROOT / "bench/variations" / EXPERIMENTS["grounded"]["variations"][arm]
        expected_bridge = _package_bridge_material(path, prefix)
        for field in ("bridge", "entry", "fixed"):
            if saved.get(field) != expected_bridge[field]:
                errors.append(f"grounded {arm}: {field} does not match its variation package")


def check(out: Path, n: int, mode: str, experiment: str = "door") -> list[str]:
    errors: list[str] = []
    try:
        config = EXPERIMENTS[experiment]
    except KeyError:
        return [f"run.json: unknown experiment {experiment}"]
    arms = config["arms"]
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
    live = mode == "artifacts" or (mode == "reviewed" and run.get("mode") == "live")
    if mode == "dry" and run.get("mode") != "dry":
        errors.append("run.json: expected dry mode for dry checker")
    if mode == "artifacts" and run.get("mode") != "live":
        errors.append("run.json: expected live mode for artifacts checker")
    if run.get("experiment", "door") != experiment:
        errors.append("run.json: experiment field does not match selected experiment")
    if run.get("arms") != list(arms):
        errors.append("run.json: arms field does not match selected experiment")
    _check_rows(rows, n, live, arms, errors)
    expected = len(arms) * n
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
    for arm in arms:
        expected_prompt = patch_prompt(selection, arm, experiment)
        if prompts.get(arm, {}).get("hashes") != expected_prompt["hashes"]:
            errors.append(f"prompts/{arm}: prompt hashes differ from fixture")
    if experiment == "completion":
        _check_completion(source, rows, live, errors)
    elif experiment == "grounded":
        _check_grounded(source, errors)
    if mode == "reviewed":
        _check_reviewed(out, rows, n, arms, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("n", type=int)
    parser.add_argument("--mode", choices=("dry", "artifacts", "reviewed"), required=True)
    parser.add_argument("--experiment", choices=tuple(EXPERIMENTS), default="door")
    args = parser.parse_args()
    errors = check(args.out, args.n, args.mode, args.experiment)
    if errors:
        print("\n".join(errors))
        return 1
    print(f"door probe {args.mode} artifacts valid: {len(EXPERIMENTS[args.experiment]['arms']) * args.n} rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Command line interface for ``python -m bench``."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path

from bench.core import (
    LEDGER_PATH,
    REFERENCE_MDE_AT_FOUR,
    _stats,
    aggregate_runs,
    append_ledger_row,
    baseline_scenes_scored,
    baseline_scores,
    known_scale_ledger_rows,
    ledger_row,
    ledger_rows,
    load_dotenv,
    load_variation,
    prompt_for,
    run_judges,
    run_scene,
    scenes_scored_for_row,
    score_judgments,
    scripts_for,
    successful_ledger_rows,
    unknown_scale_ledger_rows,
    welch_t_test,
)
from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.engine import RuntimeEngine


def parser() -> argparse.ArgumentParser:
    command = argparse.ArgumentParser(prog="python -m bench", description="Local narration prompt benchmark")
    sub = command.add_subparsers(dest="command", required=True)
    chat = sub.add_parser("chat", help="play interactively and show every prompt")
    chat.add_argument("--variation", type=Path, required=True)
    describe = sub.add_parser("describe", help="resolve and inspect a variation without calling a model")
    describe.add_argument("--variation", type=Path, required=True)
    describe.add_argument("--json", action="store_true", help="print only the JSON description")
    log = sub.add_parser("log", help="read the append-only results ledger")
    log.add_argument("--json", action="store_true", help="print only the JSON rows")
    log.add_argument("--variation")
    log.add_argument("--limit", type=int)
    log.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    compare = sub.add_parser("compare", help="compare pooled ledger results for two variations")
    compare.add_argument("name_a")
    compare.add_argument("name_b")
    compare.add_argument("--ledger", type=Path, default=LEDGER_PATH)
    compare.add_argument(
        "--allow-package-mismatch",
        action="store_true",
        help="allow comparison when effective story package hashes differ",
    )
    compare.add_argument(
        "--allow-coverage-mismatch",
        action="store_true",
        help="allow comparison when the number of scored scenes differs",
    )
    run = sub.add_parser("run", help="run live narration replicates and judge them")
    run.add_argument("--variation", type=Path, required=True)
    run.add_argument("--scene", required=True)
    run.add_argument("--replicates", type=int, default=4)
    run.add_argument("--script")
    run.add_argument("--out", type=Path, required=True)
    run.add_argument("--baseline", type=Path)
    run.add_argument(
        "--allow-coverage-mismatch",
        action="store_true",
        help="allow --baseline comparison when the number of scored scenes differs",
    )
    run.add_argument("--confirm", action="store_true")
    run.add_argument("--confirm-threshold-neurons", type=float)
    score = sub.add_parser("score", help="score an archived hosted run")
    score.add_argument("--run-dir", type=Path, required=True)
    prompt = sub.add_parser("prompt", help="assemble a prompt without calling a model")
    prompt.add_argument("--variation", type=Path, required=True)
    prompt.add_argument("--scene", required=True)
    prompt.add_argument("--turn", type=int, required=True)
    prompt.add_argument("--player-input", required=True)
    return command


def _json(value: object) -> None:
    print(json.dumps(value, ensure_ascii=False, separators=(",", ":")))


def _score(args: argparse.Namespace) -> int:
    data = json.loads((args.run_dir / "e2e-llm-canon.json").read_text(encoding="utf-8"))
    result = score_judgments(data.get("judgments", []))
    # This subcommand is intentionally a stable, minimal fixture adapter. The
    # richer graded metric is present in live summary.json, not this exact API.
    _json({"total": result["total"], "per_criterion": result["per_criterion"]})
    return 0


def _prompt(args: argparse.Namespace) -> int:
    if args.turn < 1:
        raise ValueError("--turn must be at least 1")
    variation = load_variation(args.variation)
    _json(prompt_for(variation, args.scene, args.player_input))
    return 0


def _describe(args: argparse.Namespace) -> int:
    variation = load_variation(args.variation)
    # Loading the effective package validates both the base package and every
    # overlay without constructing a provider or contacting a model.
    from bench.core import package_and_state

    package_and_state(variation)
    _json(
        {
            "name": variation["name"],
            "variation_hash": variation["_variation_hash"],
            "package_hash": variation["_package_hash"],
            "include_output_example": variation["_prompt_variant"]["include_output_example"],
            "output_example": variation["_resolved_output_example"],
            "beat_delivery": variation["_prompt_variant"]["beat_delivery"],
            "story_package": variation["_story_package_value"],
            "rules": variation["_resolved_rules"],
        }
    )
    return 0


def _log(args: argparse.Namespace) -> int:
    rows = ledger_rows(args.ledger)
    if args.variation:
        rows = [row for row in rows if row.get("variation_name") == args.variation]
    if args.limit is not None:
        if args.limit < 1:
            raise ValueError("--limit must be at least 1")
        rows = rows[-args.limit:]
    if args.json:
        _json(rows)
        return 0
    print(
        "timestamp  variation  scene  coverage  status  replicates  mean  sd  scores  "
        "example_leakage  failure_reason"
    )
    for row in rows:
        if "scenes_scored" not in row:
            coverage = "legacy/unknown-scale"
        elif row["scenes_scored"] is None:
            coverage = "unknown-scale (null)"
        else:
            coverage = row["scenes_scored"]
        print(
            f"{row.get('timestamp', '')}  {row.get('variation_name', '')}  {row.get('scene', '')}  "
            f"{coverage}  {row.get('status', 'ok')}  {row.get('replicates', '')}  "
            f"{row.get('mean', '')}  {row.get('sd', '')}  {row.get('scores', '')}  "
            f"{row.get('example_leakage', '')}  "
            f"{row.get('failure_reason', '')}"
        )
    if not rows:
        print("(no ledger rows)")
    return 0


def _compare(args: argparse.Namespace) -> int:
    rows = ledger_rows(args.ledger)
    left_successful = successful_ledger_rows([row for row in rows if row.get("variation_name") == args.name_a])
    right_successful = successful_ledger_rows([row for row in rows if row.get("variation_name") == args.name_b])
    _report_unknown_scale_rows(args.name_a, unknown_scale_ledger_rows(left_successful))
    if args.name_b != args.name_a:
        _report_unknown_scale_rows(args.name_b, unknown_scale_ledger_rows(right_successful))
    left_rows = known_scale_ledger_rows(left_successful)
    right_rows = known_scale_ledger_rows(right_successful)
    if not left_rows or not right_rows:
        raise ValueError("both variation names must have at least one successful scored ledger row")
    left_coverage = sorted({scenes_scored_for_row(row) for row in left_rows})
    right_coverage = sorted({scenes_scored_for_row(row) for row in right_rows})
    if (left_coverage != right_coverage or len(left_coverage) != 1) and not args.allow_coverage_mismatch:
        raise RuntimeError(
            "refusing comparison: scene coverage differs or is mixed "
            f"(scenes_scored: {args.name_a}={left_coverage}, {args.name_b}={right_coverage}); "
            "rerun with --allow-coverage-mismatch to compare anyway"
        )
    package_hashes = {row.get("package_hash") for row in (*left_rows, *right_rows)}
    if len(package_hashes) > 1 and not args.allow_package_mismatch:
        raise RuntimeError(
            "refusing comparison: story data was not held constant (package_hash differs); "
            "rerun with --allow-package-mismatch to compare anyway"
        )
    try:
        left = [float(score) for row in left_rows for score in row.get("scores", [])]
        right = [float(score) for row in right_rows for score in row.get("scores", [])]
    except (TypeError, ValueError) as error:
        raise ValueError(f"ledger scores are invalid: {error}") from error
    if not left or not right:
        raise ValueError("both variation names must have scored replicates")
    available_n = min(len(left), len(right))
    left_stats = _stats(left, available_n)
    right_stats = _stats(right, available_n)
    test = welch_t_test(left, right)
    warnings = []
    if len(package_hashes) > 1:
        warnings.append("WARNING: story data was not held constant (package_hash differs)")
    if left_coverage != right_coverage or len(left_coverage) != 1:
        warnings.append("WARNING: scene coverage was not held constant (scenes_scored differs)")
    print(
        f"{args.name_a}: n={left_stats['n']} mean={left_stats['mean']:.2f} "
        f"sd={_format_number(left_stats['standard_deviation'])}"
    )
    print(
        f"{args.name_b}: n={right_stats['n']} mean={right_stats['mean']:.2f} "
        f"sd={_format_number(right_stats['standard_deviation'])}"
    )
    print(
        "example_leakage (turns containing an 8+ word example span): "
        f"{args.name_a}={_format_metric_total(left_rows, 'example_leakage')} "
        f"{args.name_b}={_format_metric_total(right_rows, 'example_leakage')}"
    )
    difference = test.get("difference_in_means", left_stats["mean"] - right_stats["mean"])
    print(f"difference ({args.name_a} - {args.name_b}): {difference:.2f}")
    for warning in warnings:
        print(warning)
    if test.get("available"):
        print(
            f"two-sided Welch t-test: t={test['t']:.3f}, df={test['degrees_of_freedom']:.2f}, "
            f"p={test['p_value']:.4f}"
        )
        print(test["statement"])
    else:
        print(f"two-sided Welch t-test: unavailable ({test['reason']})")
    mde = REFERENCE_MDE_AT_FOUR * math.sqrt(4 / available_n) if available_n else None
    print(f"minimum detectable effect (N={available_n} available per arm): {_format_number(mde)}")
    return 0


def _report_unknown_scale_rows(name: str, rows: list[dict[str, object]]) -> None:
    missing = sum("scenes_scored" not in row for row in rows)
    null = sum("scenes_scored" in row and row["scenes_scored"] is None for row in rows)
    if missing:
        noun = "row" if missing == 1 else "rows"
        print(f"skipped {missing} legacy {noun} for {name}: no scenes_scored recorded, so its scale is unknown")
    if null:
        noun = "row" if null == 1 else "rows"
        print(f"skipped {null} unknown-scale {noun} for {name}: scenes_scored is null, so its scale is unknown")


def _format_number(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.2f}"


def _format_metric_total(rows: list[dict[str, object]], key: str) -> str:
    values = [row.get(key) for row in rows]
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in values):
        return "unavailable"
    return str(sum(values))


def _confirm(args: argparse.Namespace, projected: float, script_count: int) -> None:
    threshold = args.confirm_threshold_neurons
    if threshold is None:
        threshold = float(os.getenv("BENCH_CONFIRM_THRESHOLD_NEURONS", "500"))
    print(
        f"Projected spend for {args.replicates} replicates across {script_count} "
        f"script(s): {projected:.0f} Workers AI neurons and the corresponding number of OpenAI judge calls.",
        file=sys.stderr,
    )
    if projected <= threshold or args.confirm:
        return
    if not sys.stdin.isatty():
        raise RuntimeError(f"projected spend exceeds {threshold:.0f}; rerun with --confirm")
    answer = input(f"Continue above {threshold:.0f} neurons? [y/N] ")
    if answer.casefold() not in {"y", "yes"}:
        raise RuntimeError("run cancelled")


def _run(args: argparse.Namespace) -> int:
    if args.replicates < 1:
        raise ValueError("--replicates must be at least 1")
    if args.replicates == 1:
        print(
            "Warning: one replicate cannot estimate within-arm noise; standard deviation and confidence interval "
            "will be unavailable. Use the default four replicates for a comparison.",
            file=sys.stderr,
        )
    variation = load_variation(args.variation)
    scripts = scripts_for(variation, args.scene)
    if args.script:
        scripts = [script for script in scripts if script["name"] == args.script]
        if not scripts:
            raise ValueError(f"no script named {args.script!r} for scene {args.scene}")
    if args.baseline:
        baseline_coverage = baseline_scenes_scored(args.baseline)
        if baseline_coverage is None:
            print(
                f"skipped unknown-scale baseline {args.baseline}: no scenes_scored recorded, so its scale is unknown"
            )
        elif baseline_coverage != 1 and not args.allow_coverage_mismatch:
            raise RuntimeError(
                "refusing baseline comparison: scene coverage differs "
                f"(run scenes_scored=1, baseline scenes_scored={baseline_coverage}); "
                "rerun with --allow-coverage-mismatch to compare anyway"
            )
    planned_turns = sum(len(script["inputs"]) + 1 for script in scripts) * args.replicates
    projected = planned_turns * 330 / 30
    _confirm(args, projected, len(scripts))
    args.out.mkdir(parents=True, exist_ok=True)
    runs = []
    failed_runs = []
    quota = None
    for replicate in range(1, args.replicates + 1):
        for script in scripts:
            try:
                record = run_scene(variation, args.scene, script)
            except (NarrationProviderError, RuntimeError) as error:
                record = {
                    "status": "failed",
                    "script": script["name"],
                    "scene_id": args.scene,
                    "opening": "",
                    "turns": [],
                    "completed": False,
                    "quota": None,
                    "failure_reason": _failure_reason(error),
                    "narration_turns": 0,
                    "narration_requests": 0,
                    "recovery_requests": 0,
                    "package": variation.get("_package_path", ""),
                }
            record["replicate"] = replicate
            runs.append(record)
            if record.get("status", "ok") != "ok":
                failed_runs.append(record)
            if record.get("quota"):
                quota = {
                    **record["quota"],
                    "completed_runs": len(runs) - 1,
                    "planned_runs": args.replicates * len(scripts),
                }
                break
        if quota:
            break
    judged_runs = [run for run in runs if run.get("status", "ok") == "ok" and run.get("quota") is None]
    pending = args.out / "turn-records.json"
    pending.write_text(
        json.dumps(
            {"scene_id": args.scene, "package_path": variation["_package_path"], "runs": judged_runs},
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    judged_path = args.out / "judgments.json"
    judged = {"judgments": [], "judge_calls": 0}
    judge_failure_reason = None
    if judged_runs:
        try:
            judged = run_judges(pending, judged_path)
        except (OSError, ValueError, RuntimeError) as error:
            judge_failure_reason = _failure_reason(error)
            failed_runs.extend(judged_runs)
            judged_runs = []
    judgments = judged["judgments"]
    if len(judgments) < len(judged_runs):
        missing = judged_runs[len(judgments) :]
        for run in missing:
            run["status"] = "failed"
            run["failure_reason"] = (
                f"judge returned {len(judgments)} result(s) for {len(judged_runs)} completed run(s)"
            )
        failed_runs.extend(missing)
        judged_runs = judged_runs[: len(judgments)]
    if judgments:
        (args.out / "judgment.json").write_text(
            json.dumps(judgments[0], indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
    aggregate = aggregate_runs(judged_runs, judgments, args.replicates)
    aggregate["budget"] = {
        "projected_workers_ai_neurons": projected,
        "actual_narration_turns": sum(run["narration_turns"] for run in runs),
        "actual_narration_requests": sum(run["narration_requests"] for run in runs),
        "estimated_workers_ai_neurons_from_requests": sum(run["narration_requests"] for run in runs) * 330 / 30,
        "actual_openai_judge_calls": judged.get("judge_calls", 0),
        "quota": quota,
    }
    if args.baseline and aggregate["replicate_scores"]:
        baseline_values = baseline_scores(args.baseline)
        if baseline_values:
            aggregate["comparison"] = welch_t_test(aggregate["replicate_scores"], baseline_values)
    summary_path = args.out / "summary.json"
    summary_path.write_text(json.dumps(aggregate, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if judged_runs:
        append_ledger_row(
            ledger_row(
                variation,
                scene=args.scene,
                scripts=scripts,
                replicates=args.replicates,
                aggregate=aggregate,
            ),
            LEDGER_PATH,
        )
    failure_aggregate = aggregate_runs([], [], args.replicates)
    for failed in failed_runs:
        failure_budget = {
            "estimated_workers_ai_neurons_from_requests": failed.get("narration_requests", 0) * 330 / 30,
            "actual_openai_judge_calls": 0,
        }
        failure_aggregate["budget"] = failure_budget
        append_ledger_row(
            ledger_row(
                variation,
                scene=args.scene,
                scripts=[{"name": failed["script"]}],
                replicates=1,
                aggregate=failure_aggregate,
                status="failed",
                failure_reason=failed.get("failure_reason") or judge_failure_reason or "run failed",
            ),
            LEDGER_PATH,
        )
    _json(aggregate)
    return 2 if quota or failed_runs or judge_failure_reason else 0


def _failure_reason(error: BaseException) -> str:
    error_code = getattr(error, "error_code", "")
    return f"{error_code}: {error}" if error_code else str(error)


def _chat(args: argparse.Namespace) -> int:
    variation = load_variation(args.variation)
    _, state = __import__("bench.core", fromlist=["package_and_state"]).package_and_state(variation)
    provider = __import__("bench.core", fromlist=["provider_for"]).provider_for(state, variation)
    engine = RuntimeEngine(state, provider)
    opening = engine.opening()
    print(
        f"\nNARRATION:\n{opening.narration}\n\nPROMPT SYSTEM:\n{provider.last_prompt['system']}"
        f"\n\nPROMPT USER:\n{provider.last_prompt['user']}"
    )
    while True:
        try:
            player_input = input("\n> ")
        except EOFError:
            break
        if not player_input.strip():
            continue
        proposal = engine.turn(player_input)
        print(f"\nNARRATION:\n{proposal.narration}")
        if provider.last_prompt:
            print(f"\nPROMPT SYSTEM:\n{provider.last_prompt['system']}\n\nPROMPT USER:\n{provider.last_prompt['user']}")
    return 0


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = parser().parse_args(argv)
    try:
        if args.command == "score":
            return _score(args)
        if args.command == "prompt":
            return _prompt(args)
        if args.command == "describe":
            return _describe(args)
        if args.command == "log":
            return _log(args)
        if args.command == "compare":
            return _compare(args)
        if args.command == "run":
            return _run(args)
        if args.command == "chat":
            return _chat(args)
        raise AssertionError(args.command)
    except (OSError, ValueError, RuntimeError) as error:
        print(f"bench: {error}", file=sys.stderr)
        return 2

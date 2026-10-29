"""Probe whether scene and starting-place context fixes drain observations."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration.holder_wording_probe import (
    _lock_matches as _shared_lock_matches,
)
from scripts.ringer.environment_narration.holder_wording_probe import (
    _redact,
    _sha256,
    _status_stop_reason,
    _write_json,
)
from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import ObservationVerifier, Relation, _question_for

REPO_DIR = Path(__file__).resolve().parents[3]
DEFAULT_ROWS_PATH = REPO_DIR / "bench/results/environment-narration/t9h/smoke/e/rows/rows.json"
PROBE_DIR = Path(__file__).with_name("drain_probe")
CASES_PATH = PROBE_DIR / "cases.jsonl"
LOCK_PATH = PROBE_DIR / "cases.lock.json"
DEFAULT_SAMPLES = 10
DEFAULT_MAX_CALLS = 1000
DEFAULT_MAX_USD = 1.0
FIXED_SEED = 1729
UNUSABLE_STOP_AFTER = 3
ACCEPT_ABOVE = 0.65
REJECT_BELOW = 0.35
COST_PER_MILLION_INPUT_TOKENS = 0.042
QUESTION_ARMS = ("J0", "J1", "J2")
CASE_KINDS = ("positive", "negative")
SCENE = "The Lead in the Park"
STARTING_PLACE = "Los Angeles park"
J2_SENTENCE = (
    "Check whether the narration shows the named thing in the scene. "
    "Use its starting place when the narration leaves it there. "
    "Reject a different final place stated by the narration."
)

D_EXPLICIT = (
    "Kristin walks to the storm drain set into the path at the Los Angeles park. "
    "She leans over and looks into the drain. "
    "The park is quiet around her."
)
D_REMEMBERED = (
    "Kristin remembers seeing a storm drain earlier. "
    "She looks around the park, but no storm drain is here. "
    "She keeps walking through the park."
)
D_ELSEWHERE = (
    "Kristin knows that the storm drain is at Michelle's house. "
    "The storm drain is there now, away from the Los Angeles park. "
    "Kristin remains in the park."
)


def _lock_matches(cases: list[dict[str, Any]], cases_path: Path | None = None, lock_path: Path | None = None) -> bool:
    cases_path = CASES_PATH if cases_path is None else cases_path
    lock_path = LOCK_PATH if lock_path is None else lock_path
    return _shared_lock_matches(cases, cases_path, lock_path)


def _rows_source() -> Path:
    configured = os.environ.get("DRAIN_PROBE_ROWS_PATH", "").strip()
    return Path(configured) if configured else DEFAULT_ROWS_PATH


def _load_rows(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ValueError(f"rows.json is missing: {path}") from error
    except json.JSONDecodeError as error:
        raise ValueError(f"rows.json is invalid JSON: {path}") from error
    if not isinstance(document, list):
        raise ValueError("rows.json must contain a list of replicates")
    return [item for item in document if isinstance(item, dict)]


def _replicate_zero_turns(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        raise ValueError("rows.json has no replicate 0")
    turns = rows[0].get("turns")
    if not isinstance(turns, list):
        raise ValueError("replicate 0 has no turns list")
    return [turn for turn in turns if isinstance(turn, dict)]


def _matching_turn(turns: list[dict[str, Any]], player_input: str) -> dict[str, Any]:
    matches = [turn for turn in turns if turn.get("input") == player_input]
    if len(matches) != 1:
        raise ValueError(f"replicate 0 must contain exactly one {player_input!r} turn")
    return matches[0]


def _recorded_narrations(rows: list[dict[str, Any]]) -> tuple[str, str, str, str]:
    turns = _replicate_zero_turns(rows)
    storm_turn = _matching_turn(turns, "inspect the storm drain")
    attempts = storm_turn.get("enforce_attempts")
    if not isinstance(attempts, list) or len(attempts) != 2:
        raise ValueError("inspect the storm drain must have exactly two enforce_attempts entries")
    attempt_narrations = []
    for index, attempt in enumerate(attempts):
        if not isinstance(attempt, dict) or not isinstance(attempt.get("narration"), str):
            raise ValueError(f"storm drain enforce_attempts entry {index} has no narration")
        attempt_narrations.append(attempt["narration"])

    bench_turn = _matching_turn(turns, "inspect the park bench")
    bench_narration = bench_turn.get("narration")
    if not isinstance(bench_narration, str):
        raise ValueError("inspect the park bench committed turn has no narration")
    if "drain" in bench_narration.lower():
        raise ValueError("d-missing narration contains the word drain")
    return attempt_narrations[0], attempt_narrations[1], bench_narration, "r0"


def _case(case_id: str, kind: str, label: str, narration: str, source: str) -> dict[str, Any]:
    return {
        "id": case_id,
        "kind": kind,
        "label": label,
        "narration": narration,
        "relation": {"thing": "storm drain", "place": "Los Angeles park", "holder": None},
        "source": source,
    }


def build_cases(rows_path: Path | str = DEFAULT_ROWS_PATH) -> list[dict[str, Any]]:
    real_one, real_two, missing, source_prefix = _recorded_narrations(_load_rows(Path(rows_path)))
    return [
        _case("d-real-1", "positive", "accept", real_one, f"{source_prefix}:storm-drain:attempt-1"),
        _case("d-real-2", "positive", "accept", real_two, f"{source_prefix}:storm-drain:attempt-2"),
        _case("d-missing", "negative", "reject", missing, f"{source_prefix}:park-bench:committed"),
        _case("d-explicit", "positive", "accept", D_EXPLICIT, "authored"),
        _case("d-remembered", "negative", "reject", D_REMEMBERED, "authored"),
        _case("d-elsewhere", "negative", "reject", D_ELSEWHERE, "authored"),
    ]


def _cases_bytes(cases: list[dict[str, Any]]) -> bytes:
    return "".join(json.dumps(case, ensure_ascii=False, sort_keys=True) + "\n" for case in cases).encode("utf-8")


def _write_cases(cases: list[dict[str, Any]], cases_path: Path | None = None, lock_path: Path | None = None) -> None:
    cases_path = CASES_PATH if cases_path is None else cases_path
    lock_path = LOCK_PATH if lock_path is None else lock_path
    data = _cases_bytes(cases)
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    cases_path.write_bytes(data)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    _write_json(lock_path, {"sha256": _sha256(data), "count": len(cases)})


def _load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    path = CASES_PATH if path is None else path
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ValueError(f"cases.jsonl is missing: {path}") from error
    cases = []
    for line_number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid case JSON on line {line_number}") from error
        if not isinstance(case, dict):
            raise ValueError(f"case on line {line_number} is not an object")
        cases.append(case)
    if not cases:
        raise ValueError(f"cases.jsonl has no cases: {path}")
    return cases


def _j2_question(question: dict[str, object]) -> dict[str, object]:
    instructions = question.get("instructions")
    prefix = "Check whether the narration shows the thing named "
    if not isinstance(instructions, str):
        raise ValueError("J2 could not find the product question sentence")
    start = instructions.find(prefix)
    if start < 0:
        raise ValueError("J2 could not find the product question sentence")
    end = instructions.find(". ", start)
    if end < 0:
        if not instructions.endswith("."):
            raise ValueError("J2 could not find the product question sentence")
        end = len(instructions) - 1
    old_sentence = instructions[start : end + 1]
    if instructions.count(old_sentence) != 1:
        raise ValueError("J2 could not uniquely find the product question sentence")
    updated_instructions = instructions.replace(old_sentence, J2_SENTENCE, 1)
    if updated_instructions == instructions:
        raise ValueError("J2 could not replace the product question sentence")
    updated = dict(question)
    updated["instructions"] = updated_instructions
    return updated


def question_for_arm(relation: Relation, arm: str) -> dict[str, object]:
    if arm not in QUESTION_ARMS:
        raise ValueError(f"unknown arm: {arm}")
    question = _question_for(relation)
    return _j2_question(question) if arm == "J2" else question


def _relation_for_case(case: dict[str, Any]) -> Relation:
    return Relation(**case["relation"])


def _request_payload(case: dict[str, Any], arm: str) -> dict[str, Any]:
    relation = _relation_for_case(case)
    state = {"narration": case["narration"]}
    if arm != "J0":
        state.update({"scene": SCENE, "starting_place": STARTING_PLACE})
    return {"input": {"state": state, "questions": {"relation_0": question_for_arm(relation, arm)}}}


def _ask_for_arm(client: object, arm: str, relation: Relation):
    def ask(state: dict[str, object], questions: dict[str, object]) -> dict | None:
        arm_state = dict(state)
        if arm != "J0":
            arm_state.update({"scene": SCENE, "starting_place": STARTING_PLACE})
        arm_questions = questions
        if arm == "J2":
            arm_questions = {key: question_for_arm(relation, arm) for key in questions}
        return client.ask(arm_state, arm_questions)

    return ask


def _estimate_tokens(cases: list[dict[str, Any]], samples: int) -> float:
    request_chars = sum(
        len(json.dumps(_request_payload(case, arm), ensure_ascii=False, separators=(",", ":")))
        for case in cases
        for arm in QUESTION_ARMS
    )
    return request_chars * samples / 4


def _ceiling(cases: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(cases, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _planned_calls(cases: list[dict[str, Any]], samples: int) -> list[tuple[dict[str, Any], str, int]]:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    order = list(cases)
    random.Random(FIXED_SEED).shuffle(order)
    return [(case, arm, sample) for sample in range(samples) for case in order for arm in QUESTION_ARMS]


def _question_text_hash(relation: Relation, arm: str) -> str:
    text = json.dumps(question_for_arm(relation, arm), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(text.encode("utf-8"))


def run_cases(
    cases: list[dict[str, Any]],
    *,
    samples: int,
    max_calls: int,
    out: Path,
    client: object,
) -> dict[str, Any]:
    calls = _planned_calls(cases, samples)
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": None,
    }
    consecutive_unusable = 0
    for call_index, (case, arm, sample) in enumerate(calls[:max_calls], start=1):
        relation = _relation_for_case(case)
        verifier = ObservationVerifier(
            _ask_for_arm(client, arm, relation), accept_above=ACCEPT_ABOVE, reject_below=REJECT_BELOW
        )
        verifier.begin_turn()
        started = time.perf_counter()
        report = verifier.verify(case["narration"], (relation,))
        latency_ms = (time.perf_counter() - started) * 1000
        verdict = report.verdicts[0]
        row = {
            "call_index": call_index,
            "case_id": case["id"],
            "kind": case["kind"],
            "label": case["label"],
            "arm": arm,
            "sample": sample,
            "verdict": verdict.verdict,
            "score": verdict.score,
            "outcome": report.outcome,
            "failure": report.failure,
            "latency_ms": latency_ms,
            "jev_model": getattr(client, "last_model", None),
            "question_text_hash": _question_text_hash(relation, arm),
        }
        document["rows"].append(row)
        stop_reason = _status_stop_reason(client)
        if stop_reason is None and report.outcome in {"unavailable", "malformed"}:
            consecutive_unusable += 1
            if consecutive_unusable >= UNUSABLE_STOP_AFTER:
                stop_reason = "three_consecutive_unusable"
        elif stop_reason is None:
            consecutive_unusable = 0
        if stop_reason is None and len(document["rows"]) >= max_calls:
            stop_reason = "max_calls"
        if stop_reason is not None:
            document["stop_reason"] = stop_reason
        _write_json(out, document)
        if stop_reason is not None:
            break
    return document


def _error(message: str) -> int:
    print(_redact(f"drain question probe: {message}"), file=sys.stderr)
    return 2


def _print_dry_run(cases: list[dict[str, Any]], samples: int) -> None:
    tokens = _estimate_tokens(cases, samples)
    print(f"case count: {len(cases)}")
    print(f"planned requests: {len(cases) * len(QUESTION_ARMS) * samples}")
    print(f"token estimate: {tokens:.2f}")
    print(f"USD ceiling: ${_ceiling(cases, samples):.6f}")


def _group_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row.get("verdict", "unavailable") for row in rows)
    return {key: counts.get(key, 0) for key in ("accept", "uncertain", "reject", "unavailable")}


def _score_range(rows: list[dict[str, Any]]) -> str:
    scores = [row["score"] for row in rows if isinstance(row.get("score"), (int, float))]
    if not scores:
        return "n/a"
    return f"{min(scores):.2f}-{max(scores):.2f}"


def _report_text(rows: list[dict[str, Any]]) -> tuple[str, bool]:
    lines = ["# Drain question probe report", "", f"Rows rendered: {len(rows)}", ""]
    lines.extend(
        [
            "The positive cases include the two recorded failures; the negative cases test missing, remembered, "
            "and relocated drains.",
            "",
            "## Counts by arm",
            "",
        ]
    )
    for arm in QUESTION_ARMS:
        positive = [row for row in rows if row.get("arm") == arm and row.get("kind") == "positive"]
        negative = [row for row in rows if row.get("arm") == arm and row.get("kind") == "negative"]
        counts = _group_counts(positive)
        negative_accepts = sum(row.get("verdict") == "accept" for row in negative)
        positive_summary = (
            f"- positive accepts/uncertain/rejects: {counts['accept']}/{counts['uncertain']}/{counts['reject']} of 30"
        )
        lines.extend(
            [
                f"### {arm}",
                "",
                positive_summary,
                f"- negative accepts: {negative_accepts} of 30",
                "",
            ]
        )

    lines.extend(
        [
            "## Per-case score ranges",
            "",
            "| Arm | Kind | Case | Score range |",
            "| --- | --- | --- | ---: |",
        ]
    )
    seen_cases = []
    for row in rows:
        key = (row.get("arm"), row.get("kind"), row.get("case_id"))
        if key not in seen_cases:
            seen_cases.append(key)
    for arm, kind, case_id in seen_cases:
        selected = [
            row for row in rows if row.get("arm") == arm and row.get("kind") == kind and row.get("case_id") == case_id
        ]
        lines.append(f"| {arm} | {kind} | {case_id} | {_score_range(selected)} |")

    j0_positive = [row for row in rows if row.get("arm") == "J0" and row.get("kind") == "positive"]
    j0_positive_accepts = sum(row.get("verdict") == "accept" for row in j0_positive)
    lines.extend(["", "## Gate", "", f"J0 positive accepts: {j0_positive_accepts} of 30", ""])
    all_passed = False
    for arm in ("J1", "J2"):
        positive = [row for row in rows if row.get("arm") == arm and row.get("kind") == "positive"]
        negative = [row for row in rows if row.get("arm") == arm and row.get("kind") == "negative"]
        positive_accepts = sum(row.get("verdict") == "accept" for row in positive)
        negative_accepts = sum(row.get("verdict") == "accept" for row in negative)
        g1 = negative_accepts == 0
        g2 = positive_accepts >= 27
        g3 = positive_accepts >= j0_positive_accepts
        passed = g1 and g2 and g3
        all_passed = all_passed or passed
        lines.extend(
            [
                f"- {arm} vs J0 G1: {'PASS' if g1 else 'FAIL'} — negative accepts {negative_accepts} of 30",
                f"- {arm} vs J0 G2: {'PASS' if g2 else 'FAIL'} — positive accepts "
                f"{positive_accepts} of 30 (required at least 27)",
                f"- {arm} vs J0 G3: {'PASS' if g3 else 'FAIL'} — positive accepts "
                f"{positive_accepts}; J0 positive accepts {j0_positive_accepts}",
                f"- {arm} overall: {'PASS' if passed else 'FAIL'}",
                "",
            ]
        )
    return "\n".join(lines), all_passed


def report_rows(rows_path: Path, out: Path) -> int:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    report, passed = _report_text(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact(report), encoding="utf-8")
    return 0 if passed else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-cases", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.build_cases:
            cases = build_cases(_rows_source())
            _write_cases(cases)
            print(f"built {len(cases)} cases at {_redact(str(CASES_PATH))}")
            return 0
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return report_rows(args.rows, args.out)

        cases = _load_cases()
        if args.dry_run:
            if args.samples < 1:
                return _error("--samples must be at least 1")
            _print_dry_run(cases, args.samples)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        if args.samples < 1:
            return _error("--samples must be at least 1")
        calls_planned = len(cases) * len(QUESTION_ARMS) * args.samples
        if calls_planned > args.max_calls:
            return _error(f"planned requests {calls_planned} exceed --max-calls {args.max_calls}")
        ceiling = _ceiling(cases, args.samples)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not _lock_matches(cases, CASES_PATH, LOCK_PATH):
            return _error("run mode requires a matching lock")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        client = JevClient.from_environment()
        document = run_cases(cases, samples=args.samples, max_calls=args.max_calls, out=args.out, client=client)
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

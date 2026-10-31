"""Replay frozen drain narrations against the V0 and J1c relation requests."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration import j1_scope_probe as scope
from scripts.ringer.environment_narration.j1c_wiring_probe import j1c_state
from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import ObservationVerifier, Relation, _question_for

ACCEPT_ABOVE = scope.ACCEPT_ABOVE
REJECT_BELOW = scope.REJECT_BELOW
ARMS = ("V0", "J1c")
CASES_PATH = Path(__file__).with_name("drain_replay") / "cases.jsonl"
CASES_SHA256 = "26e10622abfe7d3e3aa4fa42bf1ad9f6b80a69d795896199f40dd3714264fd62"
COST_PER_MILLION_INPUT_TOKENS = scope.COST_PER_MILLION_INPUT_TOKENS
DEFAULT_MAX_CALLS = 60
DEFAULT_MAX_USD = 0.005
DEFAULT_SAMPLES = 5
FIXED_SEED = scope.FIXED_SEED
UNUSABLE_STOP_AFTER = scope.UNUSABLE_STOP_AFTER

_redact = scope._redact
_status_stop_reason = scope._status_stop_reason
_write_json = scope._write_json

CASE_FIELDS = {
    "id",
    "player_input",
    "narration",
    "location_valid",
    "condition_policy",
    "relation",
    "scene",
    "starting_places",
    "source_file",
    "replicate",
    "turn",
    "turn_index",
    "attempt",
}
RELATION_FIELDS = {"thing", "place", "holder", "scene_level"}
CASE_POLICIES = {"not_problematic", "problematic"}


def _sha256(data: bytes) -> str:
    return scope._sha256(data)


def _load_cases(path: Path | None = None) -> tuple[list[dict[str, Any]], bytes]:
    path = CASES_PATH if path is None else path
    try:
        data = path.read_bytes()
    except FileNotFoundError as error:
        raise ValueError(f"cases file is missing: {path}") from error
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid cases JSON on line {line_number}") from error
        if not isinstance(case, dict):
            raise ValueError(f"case on line {line_number} is not an object")
        cases.append(case)
    if not cases:
        raise ValueError(f"cases file has no cases: {path}")
    return cases, data


def _case_name(case: object, index: int) -> str:
    return case.get("id", f"line {index}") if isinstance(case, dict) else f"line {index}"


def _validation_errors(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        name = _case_name(case, index)
        if set(case) != CASE_FIELDS:
            errors.append(f"{name}: fields must be exactly {sorted(CASE_FIELDS)}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{name}: id must be a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{name}: duplicate id")
        else:
            seen_ids.add(case_id)
        for field in ("player_input", "narration", "source_file", "turn", "attempt"):
            if not isinstance(case.get(field), str) or not case[field]:
                errors.append(f"{name}: {field} must be a non-empty string")
        if case.get("location_valid") is not True and case.get("location_valid") is not False:
            errors.append(f"{name}: location_valid must be boolean")
        if case.get("condition_policy") not in CASE_POLICIES:
            errors.append(f"{name}: condition_policy is unknown")
        if not isinstance(case.get("replicate"), int) or case["replicate"] < 0:
            errors.append(f"{name}: replicate must be a non-negative integer")
        if not isinstance(case.get("turn_index"), int) or case["turn_index"] < 0:
            errors.append(f"{name}: turn_index must be a non-negative integer")
        relation = case.get("relation")
        if not isinstance(relation, dict) or set(relation) != RELATION_FIELDS:
            errors.append(f"{name}: relation fields must be exactly {sorted(RELATION_FIELDS)}")
        else:
            if relation.get("thing") != "storm drain":
                errors.append(f"{name}: relation thing must be storm drain")
            if relation.get("place") != "Los Angeles park":
                errors.append(f"{name}: relation place must be Los Angeles park")
            if relation.get("holder") is not None:
                errors.append(f"{name}: relation holder must be null")
            if relation.get("scene_level") is not True:
                errors.append(f"{name}: relation must be scene-level")
        if case.get("scene") != "Los Angeles park":
            errors.append(f"{name}: scene must be Los Angeles park")
        if case.get("starting_places") != {"storm drain": "Los Angeles park"}:
            errors.append(f"{name}: starting_places does not match the relation")
    if len(cases) != 6:
        errors.append(f"case count must be 6, got {len(cases)}")
    return errors


def _validated_cases(path: Path | None = None) -> tuple[list[dict[str, Any]], bytes]:
    cases, data = _load_cases(path)
    errors = _validation_errors(cases)
    if errors:
        for error in errors:
            print(_redact(error), file=sys.stderr)
        raise ValueError(f"cases validation failed with {len(errors)} problem(s)")
    return cases, data


def _lock_matches(data: bytes, cases: list[dict[str, Any]]) -> bool:
    return len(cases) == 6 and _sha256(data) == CASES_SHA256


def _relation(case: dict[str, Any]) -> Relation:
    return Relation(
        thing=case["relation"]["thing"],
        place=case["relation"]["place"],
        holder=case["relation"]["holder"],
        scene_level=case["relation"]["scene_level"],
    )


def _state(case: dict[str, Any], arm: str) -> dict[str, object]:
    if arm == "V0":
        return {"narration": case["narration"]}
    if arm != "J1c":
        raise ValueError(f"unknown arm: {arm}")
    relation = case["relation"]
    relation_state = [(relation["thing"], relation["place"], relation["scene_level"])]
    return j1c_state(case["narration"], relation_state, case["scene"])


def _payload(case: dict[str, Any], arm: str) -> dict[str, object]:
    relation = _relation(case)
    return {
        "state": _state(case, arm),
        "questions": {"relation_0": _question_for(relation)},
    }


def planned_count(cases: list[dict[str, Any]], samples: int) -> int:
    if samples < 1:
        raise ValueError("sample count must be at least 1")
    return len(cases) * len(ARMS) * samples


def planned_calls(cases: list[dict[str, Any]], samples: int) -> list[dict[str, Any]]:
    if samples < 1:
        raise ValueError("sample count must be at least 1")
    order = list(cases)
    random.Random(FIXED_SEED).shuffle(order)
    return [{"case": case, "arm": arm, "sample": sample} for sample in range(samples) for case in order for arm in ARMS]


def _estimate_tokens(cases: list[dict[str, Any]], samples: int) -> float:
    chars = sum(
        len(json.dumps(_payload(case, arm), ensure_ascii=False, separators=(",", ":")))
        for case in cases
        for arm in ARMS
    )
    return chars * samples / 4


def _ceiling(cases: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(cases, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _ask_for_case(client: object):
    def ask(state: dict[str, object], questions: dict[str, object]) -> dict | None:
        try:
            return client.ask(state, questions)
        except Exception as error:
            status = getattr(client, "last_status", None)
            if not (isinstance(status, int) and (status == 429 or status >= 500)):
                client._drain_replay_error = error
            raise

    return ask


def _row(
    call_index: int,
    planned: dict[str, Any],
    report: object,
    client: object,
    latency_ms: float,
    cases_hash: str,
) -> dict[str, Any]:
    case = planned["case"]
    verdict = report.verdicts[0]
    state = _state(case, planned["arm"])
    return {
        "call_index": call_index,
        "case_id": case["id"],
        "sample": planned["sample"],
        "arm": planned["arm"],
        "location_valid": case["location_valid"],
        "condition_policy": case["condition_policy"],
        "source_file": case["source_file"],
        "replicate": case["replicate"],
        "turn": case["turn"],
        "turn_index": case["turn_index"],
        "attempt": case["attempt"],
        "relation": {
            "thing": verdict.relation.thing,
            "place": verdict.relation.place,
            "holder": verdict.relation.holder,
            "scene_level": verdict.relation.scene_level,
            "verdict": verdict.verdict,
            "score": verdict.score,
        },
        "state_keys": sorted(state),
        "starting_places": state.get("starting_places"),
        "outcome": report.outcome,
        "failure": report.failure,
        "latency_ms": latency_ms,
        "jev_model": getattr(client, "last_model", None),
        "jev_version": getattr(client, "last_version", None),
        "thresholds": {"accept_above": ACCEPT_ABOVE, "reject_below": REJECT_BELOW},
        "cases_sha256": cases_hash,
    }


def _stop_reason(client: object) -> str | None:
    status = getattr(client, "last_status", None)
    if status == 402:
        return "quota_error"
    if status in {401, 403}:
        return "auth_error"
    return _status_stop_reason(client)


def run_cases(
    cases: list[dict[str, Any]],
    *,
    samples: int,
    max_calls: int,
    out: Path,
    client: object,
    cases_hash: str,
) -> dict[str, Any]:
    calls = planned_calls(cases, samples)
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "samples": samples,
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": "incomplete",
        "cases_sha256": cases_hash,
    }
    _write_json(out, document)
    consecutive_unusable = 0
    try:
        for call_index, planned in enumerate(calls[:max_calls], start=1):
            verifier = ObservationVerifier(
                _ask_for_case(client),
                accept_above=ACCEPT_ABOVE,
                reject_below=REJECT_BELOW,
                scene_state=planned["arm"] == "J1c",
            )
            verifier.begin_turn()
            started = time.perf_counter()
            report = verifier.verify(
                planned["case"]["narration"],
                (_relation(planned["case"]),),
                scene=planned["case"]["scene"],
            )
            probe_error = getattr(client, "_drain_replay_error", None)
            if probe_error is not None:
                delattr(client, "_drain_replay_error")
                raise probe_error
            latency_ms = (time.perf_counter() - started) * 1000
            document["rows"].append(_row(call_index, planned, report, client, latency_ms, cases_hash))
            stop_reason = _stop_reason(client)
            if stop_reason is None and report.outcome in {"unavailable", "malformed"}:
                consecutive_unusable += 1
                if consecutive_unusable >= UNUSABLE_STOP_AFTER:
                    stop_reason = "three_consecutive_unusable"
            elif stop_reason is None:
                consecutive_unusable = 0
            if stop_reason is None and len(document["rows"]) >= max_calls and len(calls) > max_calls:
                stop_reason = "max_calls"
            if stop_reason is None and len(document["rows"]) == len(calls):
                document["stop_reason"] = None
            elif stop_reason is not None:
                document["stop_reason"] = stop_reason
            _write_json(out, document)
            if stop_reason is not None:
                break
        if len(document["rows"]) == len(calls):
            document["stop_reason"] = None
            _write_json(out, document)
        return document
    except Exception:
        document["stop_reason"] = "incomplete"
        _write_json(out, document)
        raise


def _case_rows(rows: list[dict[str, Any]], case_id: str, arm: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("case_id") == case_id and row.get("arm") == arm]


def _accepted(rows: list[dict[str, Any]]) -> int:
    return sum(row.get("relation", {}).get("verdict") == "accept" for row in rows)


def _report_text(document: dict[str, Any], cases: list[dict[str, Any]]) -> tuple[str, bool]:
    rows = document["rows"]
    samples = document.get("samples", DEFAULT_SAMPLES)
    complete = document.get("stop_reason") is None and len(rows) == document.get("calls_planned")
    lines = [
        "# T9h drain replay report",
        "",
        f"Rows rendered: {len(rows)}",
        f"Run completeness: {'complete' if complete else 'partial'}",
        "",
        "## J1c pass rules",
        "",
    ]
    passed = complete
    for case in cases:
        case_id = case["id"]
        j1c_rows = _case_rows(rows, case_id, "J1c")
        accepts = _accepted(j1c_rows)
        if case["condition_policy"] == "problematic":
            lines.append(f"- {case_id}: location accepted / condition not judged — J1c {accepts}/{samples}")
            continue
        if case["location_valid"]:
            gate = accepts >= 4 and len(j1c_rows) == samples
            rule = "at least 4 of 5" if samples == 5 else f"at least 4 of {samples}"
        else:
            gate = accepts == 0 and len(j1c_rows) == samples
            rule = "0 of 5" if samples == 5 else f"0 of {samples}"
        passed = passed and gate
        status = "PASS" if gate else "FAIL"
        label = "location-valid" if case["location_valid"] else "location-invalid"
        lines.append(f"- {case_id} ({label}): {status} — J1c accepts {accepts}/{samples}; rule {rule}")
    lines.extend(["", "## V0 report only", ""])
    for case in cases:
        v0_rows = _case_rows(rows, case["id"], "V0")
        lines.append(f"- {case['id']}: V0 accepts {_accepted(v0_rows)}/{samples}")
    lines.extend(["", "## Run status", "", f"- stop_reason: {document.get('stop_reason')}"])
    if not complete:
        lines.append("- PASS rules are not evaluated as complete evidence because the run is partial.")
    lines.extend(["", f"## Overall: {'PASS' if passed else 'FAIL'}"])
    return "\n".join(lines), passed


def report_rows(rows_path: Path, out: Path) -> int:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    cases, cases_data = _validated_cases()
    if document.get("cases_sha256") != _sha256(cases_data):
        raise ValueError("rows file does not match the frozen cases")
    report, passed = _report_text(document, cases)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact(report), encoding="utf-8")
    return 0 if passed else 1


def _print_dry_run(cases: list[dict[str, Any]], samples: int) -> None:
    planned = planned_count(cases, samples)
    print(f"case count: {len(cases)}")
    print(f"planned calls: {planned} = {len(cases)} cases x 2 arms x {samples} samples")
    print(f"token estimate: {_estimate_tokens(cases, samples):.2f}")
    print(f"USD ceiling: ${_ceiling(cases, samples):.6f}")


def _error(message: str) -> int:
    print(_redact(f"drain replay probe: {message}"), file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
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
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return report_rows(args.rows, args.out)
        cases, cases_data = _validated_cases()
        if args.validate:
            print(f"case count: {len(cases)}")
            matching = _lock_matches(cases_data, cases)
            print(f"cases lock: {'matching' if matching else 'mismatch'}")
            return 0 if matching else 1
        if args.samples < 1:
            return _error("sample count must be at least 1")
        if not _lock_matches(cases_data, cases):
            return _error("mode requires a matching cases lock")
        if args.dry_run:
            planned = planned_count(cases, args.samples)
            ceiling = _ceiling(cases, args.samples)
            if planned > args.max_calls:
                return _error(f"planned calls {planned} exceed --max-calls {args.max_calls}")
            if ceiling > args.max_usd:
                return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
            _print_dry_run(cases, args.samples)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        planned = planned_count(cases, args.samples)
        if planned > args.max_calls:
            return _error(f"planned calls {planned} exceed --max-calls {args.max_calls}")
        ceiling = _ceiling(cases, args.samples)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if args.out.exists():
            return _error(f"rows already exist at {args.out}")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        document = run_cases(
            cases,
            samples=args.samples,
            max_calls=args.max_calls,
            out=args.out,
            client=JevClient.from_environment(),
            cases_hash=_sha256(cases_data),
        )
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        if args.validate:
            print(_redact(f"drain replay probe: {error}"), file=sys.stderr)
            return 1
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

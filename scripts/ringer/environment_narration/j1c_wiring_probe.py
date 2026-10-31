"""Probe product-form scene state and mixed observation batches."""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time
from collections import defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration import j1_scope_probe as scope
from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import ObservationVerifier, Relation

ACCEPT_ABOVE = scope.ACCEPT_ABOVE
ARMS = ("V0", "J1c")
CASES_PATH = Path(__file__).with_name("j1_scope") / "cases.jsonl"
LOCK_PATH = Path(__file__).with_name("j1_scope") / "lock.json"
COST_PER_MILLION_INPUT_TOKENS = scope.COST_PER_MILLION_INPUT_TOKENS
DEFAULT_MAX_CALLS = 440
DEFAULT_MAX_USD = 0.02
DEFAULT_SAMPLES = 5
FIXED_SEED = scope.FIXED_SEED
QUESTION_VERSION = scope.QUESTION_VERSION
REJECT_BELOW = scope.REJECT_BELOW
UNUSABLE_STOP_AFTER = scope.UNUSABLE_STOP_AFTER
_validated_corpus = scope._validated_corpus

_redact = scope._redact
_percentile = scope._percentile
_status_stop_reason = scope._status_stop_reason
_write_json = scope._write_json


def label(place: str) -> str:
    value = place[4:] if place.casefold().startswith("the ") else place
    return value[:1].upper() + value[1:]


def j1c_state(narration: str, relations: list[tuple[str, str, bool]], scene: str) -> dict[str, object]:
    starting_places = {thing: place for thing, place, scene_level in relations if scene_level}
    if not starting_places:
        return {"narration": narration}
    return {"narration": narration, "scene": scene, "starting_places": starting_places}


def _relation(case: dict[str, Any], relation_place: str, relation_label: str) -> dict[str, Any]:
    return {
        "thing": case["relation"]["thing"],
        "place": relation_place,
        "holder": case["relation"]["holder"],
        "scene_level": case["group"] == "scene_level",
        "label": relation_label,
    }


def _case_map(cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {case["id"]: case for case in cases}


def _required_cases(case_map: dict[str, dict[str, Any]], ids: list[str]) -> list[dict[str, Any]]:
    missing = [case_id for case_id in ids if case_id not in case_map]
    if missing:
        raise ValueError(f"referenced case id is missing: {', '.join(missing)}")
    return [case_map[case_id] for case_id in ids]


def _request(
    request_id: str,
    narration: str,
    scene_place: str,
    relations: list[dict[str, Any]],
    *,
    guard_rejects: bool = True,
) -> dict[str, Any]:
    if guard_rejects:
        for relation in relations:
            if relation["label"] == "reject" and relation["thing"].casefold() in narration.casefold():
                raise ValueError(f"reject-labelled thing occurs in narration: {relation['thing']}")
    return {
        "request_id": request_id,
        "narration": narration,
        "scene": label(scene_place),
        "relations": relations,
    }


def build_sets(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_map = _case_map(cases)
    scene_cases = [case for case in cases if case["group"] == "scene_level"]
    set_a = [
        _request(
            case["id"],
            case["narration"],
            case["scene_place"],
            [_relation(case, label(case["scene_place"]), case["label"])],
            guard_rejects=False,
        )
        for case in scene_cases
    ]
    set_b: list[dict[str, Any]] = []
    for number in range(1, 7):
        first, sixth = _required_cases(case_map, [f"f-{number}-01", f"f-{number}-06"])
        set_b.append(
            _request(
                f"m-{number}-1",
                first["narration"] + " " + sixth["narration"],
                first["scene_place"],
                [
                    _relation(first, label(first["scene_place"]), "accept"),
                    _relation(sixth, sixth["relation"]["place"], "accept"),
                ],
            )
        )
    for number in range(1, 4):
        second, tenth = _required_cases(case_map, [f"f-{number}-02", f"f-{number}-10"])
        set_b.append(
            _request(
                f"m-{number}-2",
                second["narration"],
                second["scene_place"],
                [
                    _relation(second, label(second["scene_place"]), "accept"),
                    _relation(tenth, tenth["relation"]["place"], "reject"),
                ],
            )
        )
    for number in range(4, 7):
        seventh, fifth = _required_cases(case_map, [f"f-{number}-07", f"f-{number}-05"])
        set_b.append(
            _request(
                f"m-{number}-3",
                seventh["narration"],
                seventh["scene_place"],
                [
                    _relation(seventh, seventh["relation"]["place"], "accept"),
                    _relation(fifth, label(fifth["scene_place"]), "reject"),
                ],
            )
        )
    return set_a, set_b


def planned_count(set_a: list[dict[str, Any]], set_b: list[dict[str, Any]], samples: int) -> int:
    if samples < 1:
        raise ValueError("sample count must be at least 1")
    return (len(set_a) + len(set_b)) * len(ARMS) * samples


def planned_calls(set_a: list[dict[str, Any]], set_b: list[dict[str, Any]], *, samples: int) -> list[dict[str, Any]]:
    if samples < 1:
        raise ValueError("sample count must be at least 1")
    calls = []
    for set_name, requests in (("A", set_a), ("B", set_b)):
        order = list(requests)
        random.Random(FIXED_SEED).shuffle(order)
        for sample in range(samples):
            for request in order:
                for arm in ARMS:
                    calls.append({"set": set_name, "request": request, "arm": arm, "sample": sample})
    return calls


def _payload(request: dict[str, Any], arm: str) -> dict[str, Any]:
    relations = tuple(Relation(item["thing"], item["place"], item["holder"]) for item in request["relations"])
    questions = {f"relation_{index}": scope.screen._question_for(relation) for index, relation in enumerate(relations)}
    relation_state = [(item["thing"], item["place"], item["scene_level"]) for item in request["relations"]]
    state = {"narration": request["narration"]}
    if arm == "J1c":
        state = j1c_state(request["narration"], relation_state, request["scene"])
    return {"state": state, "questions": questions}


def _ask_for_request(client: object, request: dict[str, Any], arm: str):
    def ask(_state: dict[str, object], _questions: dict[str, object]) -> dict | None:
        payload = _payload(request, arm)
        try:
            return client.ask(payload["state"], payload["questions"])
        except Exception as error:
            status = getattr(client, "last_status", None)
            if not (isinstance(status, int) and (status == 429 or status >= 500)):
                client._j1c_probe_error = error
            raise

    return ask


def _row(
    call_index: int,
    planned: dict[str, Any],
    report: object,
    client: object,
    latency_ms: float,
    cases_hash: str,
    corpus_hash: str,
) -> dict[str, Any]:
    request = planned["request"]
    return {
        "call_index": call_index,
        "set": planned["set"],
        "request_id": request["request_id"],
        "sample": planned["sample"],
        "arm": planned["arm"],
        "scene": request["scene"],
        "relations": [
            {
                "thing": item["thing"],
                "label": item["label"],
                "scene_level": item["scene_level"],
                "verdict": verdict.verdict,
                "score": verdict.score,
            }
            for item, verdict in zip(request["relations"], report.verdicts, strict=True)
        ],
        "j1c_state_differed": _payload(request, "V0")["state"] != _payload(request, "J1c")["state"],
        "outcome": report.outcome,
        "failure": report.failure,
        "latency_ms": latency_ms,
        "jev_model": getattr(client, "last_model", None),
        "jev_version": getattr(client, "last_version", None),
        "question_version": QUESTION_VERSION,
        "thresholds": {"accept_above": ACCEPT_ABOVE, "reject_below": REJECT_BELOW},
        "cases_sha256": cases_hash,
        "corpus_combined_hash": corpus_hash,
    }


def run_requests(
    set_a: list[dict[str, Any]],
    set_b: list[dict[str, Any]],
    *,
    samples: int,
    max_calls: int,
    out: Path,
    client: object,
    cases_hash: str,
    corpus_hash: str,
) -> dict[str, Any]:
    calls = planned_calls(set_a, set_b, samples=samples)
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": "incomplete",
        "cases_sha256": cases_hash,
        "corpus_combined_hash": corpus_hash,
    }
    _write_json(out, document)
    consecutive_unusable = 0
    try:
        for call_index, planned in enumerate(calls[:max_calls], start=1):
            request = planned["request"]
            relations = tuple(Relation(item["thing"], item["place"], item["holder"]) for item in request["relations"])
            verifier = ObservationVerifier(
                _ask_for_request(client, request, planned["arm"]),
                accept_above=ACCEPT_ABOVE,
                reject_below=REJECT_BELOW,
            )
            verifier.begin_turn()
            started = time.perf_counter()
            report = verifier.verify(request["narration"], relations)
            probe_error = getattr(client, "_j1c_probe_error", None)
            if probe_error is not None:
                delattr(client, "_j1c_probe_error")
                raise probe_error
            latency_ms = (time.perf_counter() - started) * 1000
            document["rows"].append(_row(call_index, planned, report, client, latency_ms, cases_hash, corpus_hash))
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
        if len(document["rows"]) == len(calls):
            document["stop_reason"] = None
            _write_json(out, document)
        return document
    except Exception:
        document["stop_reason"] = "incomplete"
        _write_json(out, document)
        raise


def _records(rows: list[dict[str, Any]], *, set_name: str | None = None, arm: str | None = None):
    return [
        (row, relation)
        for row in rows
        if (set_name is None or row.get("set") == set_name) and (arm is None or row.get("arm") == arm)
        for relation in row.get("relations", [])
        if isinstance(relation, dict)
    ]


def _rate(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)" if denominator else "0/0 (0.0%)"


def _gate_lines(rows: list[dict[str, Any]]) -> tuple[list[str], bool]:
    j1c_a = _records(rows, set_name="A", arm="J1c")
    v0_a = _records(rows, set_name="A", arm="V0")
    j1c_b = _records(rows, set_name="B", arm="J1c")
    v0_b = _records(rows, set_name="B", arm="V0")
    a1_rows = [record for record in j1c_a if record[1].get("label") == "reject"]
    a2_rows = [record for record in j1c_a if record[1].get("label") == "accept"]
    v0_a2_rows = [record for record in v0_a if record[1].get("label") == "accept"]
    b1_rows = [record for record in j1c_b if record[1].get("label") == "reject"]
    b2_rows = [record for record in j1c_b if record[1].get("label") == "accept"]
    v0_b3 = [record for record in v0_b if record[1].get("label") == "accept" and not record[1].get("scene_level")]
    j1c_b3 = [record for record in j1c_b if record[1].get("label") == "accept" and not record[1].get("scene_level")]
    a1_accepts = sum(relation.get("verdict") == "accept" for _row, relation in a1_rows)
    a2_accepts = sum(relation.get("verdict") == "accept" for _row, relation in a2_rows)
    v0_a2_accepts = sum(relation.get("verdict") == "accept" for _row, relation in v0_a2_rows)
    b1_accepts = sum(relation.get("verdict") == "accept" for _row, relation in b1_rows)
    b2_accepts = sum(relation.get("verdict") == "accept" for _row, relation in b2_rows)
    v0_b3_accepts = sum(relation.get("verdict") == "accept" for _row, relation in v0_b3)
    j1c_b3_accepts = sum(relation.get("verdict") == "accept" for _row, relation in j1c_b3)
    a1 = len(a1_rows) == 90 and a1_accepts == 0
    a2 = len(a2_rows) == 60 and a2_accepts >= 54 and a2_accepts >= v0_a2_accepts
    b1 = len(b1_rows) == 30 and b1_accepts == 0
    b2 = len(b2_rows) == 90 and b2_accepts >= 80
    b3 = len(j1c_b3) == 45 and j1c_b3_accepts >= v0_b3_accepts - 2
    lines = [
        "## Gates",
        "",
        f"- A1: {'PASS' if a1 else 'FAIL'} — J1c negative accepts {a1_accepts}/{len(a1_rows)}",
        f"- A2: {'PASS' if a2 else 'FAIL'} — V0 {_rate(v0_a2_accepts, len(v0_a2_rows))}; "
        f"J1c {_rate(a2_accepts, len(a2_rows))}",
        f"- B1: {'PASS' if b1 else 'FAIL'} — J1c reject accepts {b1_accepts}/{len(b1_rows)}",
        f"- B2: {'PASS' if b2 else 'FAIL'} — J1c accepts {_rate(b2_accepts, len(b2_rows))}",
        f"- B3: {'PASS' if b3 else 'FAIL'} — V0 {v0_b3_accepts}/{len(v0_b3)}; J1c {j1c_b3_accepts}/{len(j1c_b3)}",
    ]
    return lines, a1 and a2 and b1 and b2 and b3


def _report_text(rows: list[dict[str, Any]]) -> tuple[str, bool]:
    lines = ["# J1c wiring report", "", f"Rows rendered: {len(rows)}", ""]
    for set_name in ("A", "B"):
        for arm in ARMS:
            selected = [row for row in rows if row.get("set") == set_name and row.get("arm") == arm]
            latencies = [row["latency_ms"] for row in selected if isinstance(row.get("latency_ms"), (int, float))]
            disagreements = 0
            comparisons = 0
            by_request: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in selected:
                by_request[str(row.get("request_id"))].append(row)
            for request_rows in by_request.values():
                for left, right in combinations(request_rows, 2):
                    for left_relation, right_relation in zip(
                        left.get("relations", []), right.get("relations", []), strict=False
                    ):
                        comparisons += 1
                        disagreements += left_relation.get("verdict") != right_relation.get("verdict")
            p50 = _percentile(latencies, 0.5)
            p95 = _percentile(latencies, 0.95)
            models = sorted({str(row.get("jev_model")) for row in selected if row.get("jev_model") is not None})
            versions = sorted({str(row.get("jev_version")) for row in selected if row.get("jev_version") is not None})
            lines.extend(
                [
                    f"## {set_name} / {arm}",
                    "",
                    f"- sample-to-sample disagreement: {_rate(disagreements, comparisons)}",
                    f"- latency p50/p95: {p50:.2f}/{p95:.2f} ms" if p50 is not None else "- latency p50/p95: n/a",
                    f"- model/version: {', '.join(models) or 'n/a'} / {', '.join(versions) or 'n/a'}",
                ]
            )
    lines.extend(["", "## Reject-labelled non-reject samples", ""])
    for row, relation in _records(rows):
        if relation.get("label") == "reject" and relation.get("verdict") != "reject":
            lines.append(f"- {row.get('request_id')} {row.get('arm')} score={relation.get('score')}")
    lines.extend(["", "## Per-relation score ranges", ""])
    grouped: dict[tuple[str, str, int], list[float]] = defaultdict(list)
    for row in rows:
        for index, relation in enumerate(row.get("relations", [])):
            if isinstance(relation, dict) and isinstance(relation.get("score"), (int, float)):
                grouped[(str(row.get("request_id")), str(row.get("arm")), index)].append(relation["score"])
    for (request_id, arm, index), scores in sorted(grouped.items()):
        lines.append(f"- {request_id} {arm} relation_{index}: {min(scores):.2f}-{max(scores):.2f}")
    changed = {row.get("request_id") for row in rows if row.get("j1c_state_differed")}
    lines.extend(["", f"Requests whose J1c state differed from V0: {len(changed)}", ""])
    gate_lines, passed = _gate_lines(rows)
    lines.extend(gate_lines)
    lines.extend(["", f"## Overall: {'PASS' if passed else 'FAIL'}"])
    return "\n".join(lines), passed


def report_rows(rows_path: Path, out: Path) -> int:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    report, passed = _report_text(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact(report), encoding="utf-8")
    return 0 if passed else 1


def _estimate_tokens(set_a: list[dict[str, Any]], set_b: list[dict[str, Any]], samples: int) -> float:
    chars = sum(
        len(json.dumps(_payload(request, arm), ensure_ascii=False, separators=(",", ":")))
        for request in [*set_a, *set_b]
        for arm in ARMS
    )
    return chars * samples / 4


def _ceiling(set_a: list[dict[str, Any]], set_b: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(set_a, set_b, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _lock_matches(corpus: dict[str, Any], cases_data: bytes, case_count: int) -> bool:
    return scope._lock_matches(corpus, cases_data, case_count)


def _set_errors(set_a: list[dict[str, Any]], set_b: list[dict[str, Any]]) -> list[str]:
    errors = []
    accept_count = sum(relation["label"] == "accept" for request in set_b for relation in request["relations"])
    reject_count = sum(relation["label"] == "reject" for request in set_b for relation in request["relations"])
    if len(set_a) != 30:
        errors.append(f"Set A must contain 30 requests, found {len(set_a)}")
    if len(set_b) != 12:
        errors.append(f"Set B must contain 12 requests, found {len(set_b)}")
    if accept_count != 18 or reject_count != 6:
        errors.append(
            f"Set B relations must contain 18 accept and 6 reject labels, found {accept_count} and {reject_count}"
        )
    return errors


def _print_validate(set_a: list[dict[str, Any]], set_b: list[dict[str, Any]], lock_matches: bool) -> None:
    accepts = sum(relation["label"] == "accept" for request in set_b for relation in request["relations"])
    rejects = sum(relation["label"] == "reject" for request in set_b for relation in request["relations"])
    print(f"scope lock: {'matching' if lock_matches else 'mismatch'}")
    print(f"Set A: {len(set_a)} requests")
    print(f"Set B: {len(set_b)} requests")
    print(f"Set B relations: {accepts} accept, {rejects} reject")


def _print_dry_run(set_a: list[dict[str, Any]], set_b: list[dict[str, Any]], samples: int) -> None:
    planned = planned_count(set_a, set_b, samples)
    print(f"Set A: {len(set_a)} requests")
    print(f"Set B: {len(set_b)} requests")
    print(f"planned requests: ({len(set_a)} + {len(set_b)}) x 2 arms x {samples} = {planned}")
    print(f"token estimate: {_estimate_tokens(set_a, set_b, samples):.2f}")
    print(f"USD ceiling: ${_ceiling(set_a, set_b, samples):.6f}")


def _error(message: str) -> int:
    print(_redact(f"j1c wiring probe: {message}"), file=sys.stderr)
    return 2


def _report_error(message: str) -> int:
    print(_redact(f"j1c wiring probe: {message}"), file=sys.stderr)
    return 1


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
            corpus = _validated_corpus()
            cases, cases_data = scope._validated_cases(CASES_PATH)
            if not _lock_matches(corpus, cases_data, len(cases)):
                return _report_error("report mode requires a matching lock")
            if args.rows is None or args.out is None:
                return _report_error("--report requires --rows and --out")
            return report_rows(args.rows, args.out)
        corpus = _validated_corpus()
        cases, cases_data = scope._validated_cases(CASES_PATH)
        lock_matches = _lock_matches(corpus, cases_data, len(cases))
        if not lock_matches:
            if args.validate or args.dry_run:
                print("scope lock: mismatch")
                return 1
            return _error("run mode requires a matching lock")
        set_a, set_b = build_sets(cases)
        set_errors = _set_errors(set_a, set_b)
        if set_errors:
            for error in set_errors:
                print(_redact(error), file=sys.stderr)
            if args.validate:
                return 1
            return _error("derived request sets failed validation")
        if args.validate:
            _print_validate(set_a, set_b, lock_matches)
            return 0
        if args.samples < 1:
            return _error("sample count must be at least 1")
        if args.dry_run:
            _print_dry_run(set_a, set_b, args.samples)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        planned = planned_count(set_a, set_b, args.samples)
        if planned > args.max_calls:
            return _error(f"planned requests {planned} exceed --max-calls {args.max_calls}")
        ceiling = _ceiling(set_a, set_b, args.samples)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        document = run_requests(
            set_a,
            set_b,
            samples=args.samples,
            max_calls=args.max_calls,
            out=args.out,
            client=JevClient.from_environment(),
            cases_hash=scope._sha256(cases_data),
            corpus_hash=corpus["combined"],
        )
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        if args.report:
            return _report_error(str(error))
        if args.validate:
            print(_redact(f"j1c wiring probe: {error}"), file=sys.stderr)
            return 1
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

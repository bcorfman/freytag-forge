"""Probe whether omitting a duplicated holder place improves verifier wording."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from scripts.ringer.environment_narration.verifier_calibration import _load_corpus
from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import ObservationVerifier, Relation, _question_for

REPO_DIR = Path(__file__).resolve().parents[3]
DEFAULT_ROWS_PATH = REPO_DIR / "bench/results/environment-narration/shadow-sample/full/rows/rows.json"
PROBE_DIR = Path(__file__).with_name("holder_probe")
CASES_PATH = PROBE_DIR / "cases.jsonl"
LOCK_PATH = PROBE_DIR / "cases.lock.json"
WORLD_PATH = REPO_DIR / "data/stories/continuity-initiative/world.yaml"
DEFAULT_SAMPLES = 2
DEFAULT_MAX_CALLS = 1000
DEFAULT_MAX_USD = 1.0
FIXED_SEED = 1729
UNUSABLE_STOP_AFTER = 3
ACCEPT_ABOVE = 0.65
REJECT_BELOW = 0.35
COST_PER_MILLION_INPUT_TOKENS = 0.042
QUESTION_ARMS = ("full_both", "short_both", "short_held_only")
CASE_KINDS = ("absent_thing", "positive_held", "wrong_holder")


def _credential_values() -> tuple[str, ...]:
    value = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip()
    return (value,) if value else ()


def _redact(value: str) -> str:
    for secret in _credential_values():
        value = value.replace(secret, "[REDACTED]")
    return value


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(_redact(text), encoding="utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _relation_document(relation: Relation) -> dict[str, str | None]:
    return {"thing": relation.thing, "place": relation.place, "holder": relation.holder}


def held_only_relation(relation: Relation) -> Relation:
    """Drop a duplicated place only for a relation held by that same place."""
    if relation.place is not None and relation.place == relation.holder:
        return Relation(thing=relation.thing, place=None, holder=relation.holder)
    return relation


def question_for_arm(relation: Relation, arm: str) -> dict[str, object]:
    if arm not in QUESTION_ARMS:
        raise ValueError(f"unknown arm: {arm}")
    selected = held_only_relation(relation) if arm == "short_held_only" else relation
    return _question_for(selected)


def _rows_source() -> Path:
    configured = os.environ.get("HOLDER_PROBE_ROWS_PATH", "").strip()
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


def _turn_records(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    holder_records: list[dict[str, Any]] = []
    examine_turns: list[dict[str, Any]] = []
    for replicate_index, replicate in enumerate(rows):
        turns = replicate.get("turns")
        if not isinstance(turns, list):
            continue
        for turn_index, turn in enumerate(turns):
            if not isinstance(turn, dict) or turn.get("error") is not None:
                continue
            turn_id = f"r{replicate_index}t{turn_index}"
            if turn.get("input") == "examine my laptop":
                examine_turns.append({"turn_id": turn_id, "turn": turn})
            relations = turn.get("observation_relations")
            if not isinstance(relations, list):
                continue
            for relation in relations:
                if not isinstance(relation, dict) or not relation.get("holder"):
                    continue
                holder_records.append({"turn_id": turn_id, "turn": turn, "relation": relation})
    return holder_records, examine_turns


def _short_labels(world_path: Path | str = WORLD_PATH) -> dict[str, str]:
    document = yaml.safe_load(Path(world_path).read_text(encoding="utf-8"))
    if not isinstance(document, dict) or not isinstance(document.get("npcs"), list):
        raise ValueError("world.yaml must contain an npcs list")
    labels: dict[str, str] = {}
    for npc in document["npcs"]:
        if not isinstance(npc, dict) or not isinstance(npc.get("name"), str):
            continue
        aliases = npc.get("aliases") or []
        if not isinstance(aliases, list):
            aliases = []
        names = [alias for alias in aliases if isinstance(alias, str)]
        names.append(npc["name"])
        label = min(names, key=len)
        for name in names:
            labels[name] = label
    return labels


def _short_relation(relation: Relation, labels: dict[str, str]) -> Relation:
    def replace(value: str | None) -> str | None:
        return labels.get(value, value) if isinstance(value, str) else value

    return Relation(
        thing=replace(relation.thing),
        place=replace(relation.place),
        holder=replace(relation.holder),
    )


def _case(
    case_id: str,
    kind: str,
    label: str,
    narration: str,
    relation: Relation,
    source_turn: str,
    short_labels: dict[str, str],
) -> dict[str, Any]:
    return {
        "id": case_id,
        "kind": kind,
        "label": label,
        "narration": narration,
        "relation": _relation_document(relation),
        "relation_short": _relation_document(_short_relation(relation, short_labels)),
        "source_turn": source_turn,
    }


def build_cases(rows_path: Path | str = DEFAULT_ROWS_PATH, world_path: Path | str = WORLD_PATH) -> list[dict[str, Any]]:
    """Build the frozen 25-case holder probe corpus from shadow rows."""
    rows = _load_rows(Path(rows_path))
    short_labels = _short_labels(world_path)
    holder_records, examine_turns = _turn_records(rows)
    if len(holder_records) != 10:
        raise ValueError(f"rows.json yielded {len(holder_records)} holder relations; expected exactly 10")
    if len(examine_turns) != 5:
        raise ValueError(f"rows.json yielded {len(examine_turns)} laptop-examine turns; expected exactly 5")

    cases: list[dict[str, Any]] = []
    for record in holder_records:
        turn = record["turn"]
        relation_data = record["relation"]
        relation = Relation(
            thing=relation_data.get("thing"),
            place=relation_data.get("place"),
            holder=relation_data.get("holder"),
        )
        turn_id = record["turn_id"]
        narration = turn.get("narration")
        cases.append(_case(f"h-p-{turn_id}", "positive_held", "accept", narration, relation, turn_id, short_labels))
        wrong = Relation(thing=relation.thing, place="Michelle McGehee", holder="Michelle McGehee")
        cases.append(_case(f"h-w-{turn_id}", "wrong_holder", "reject", narration, wrong, turn_id, short_labels))

    for record in examine_turns:
        turn_id = record["turn_id"]
        relation = Relation(
            thing="Michelle's memory card",
            place="Kristin Schweitzer",
            holder="Kristin Schweitzer",
        )
        cases.append(
            _case(
                f"h-a-{turn_id}",
                "absent_thing",
                "reject",
                record["turn"].get("narration"),
                relation,
                turn_id,
                short_labels,
            )
        )
    cases.sort(key=lambda item: (item["source_turn"], item["kind"]))
    return cases


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


def _lock_matches(cases: list[dict[str, Any]], cases_path: Path | None = None, lock_path: Path | None = None) -> bool:
    cases_path = CASES_PATH if cases_path is None else cases_path
    lock_path = LOCK_PATH if lock_path is None else lock_path
    try:
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
        data = cases_path.read_bytes()
    except (OSError, json.JSONDecodeError):
        return False
    return lock == {"sha256": _sha256(data), "count": len(cases)}


def _request_payload(case: dict[str, Any], arm: str) -> dict[str, Any]:
    relation_data = case["relation"] if arm == "full_both" else case["relation_short"]
    relation = Relation(**relation_data)
    return {
        "input": {
            "state": {"narration": case["narration"]},
            "questions": {"relation_0": question_for_arm(relation, arm)},
        }
    }


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
    calls = []
    for sample in range(samples):
        for case in order:
            for arm in QUESTION_ARMS:
                calls.append((case, arm, sample))
    return calls


def _question_text_hash(relation: Relation, arm: str) -> str:
    question = question_for_arm(relation, arm)
    text = json.dumps(question, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return _sha256(text.encode("utf-8"))


def _relation_for_arm(case: dict[str, Any], arm: str) -> Relation:
    relation_data = case["relation"] if arm == "full_both" else case["relation_short"]
    return Relation(**relation_data)


def _status_stop_reason(client: object) -> str | None:
    status = getattr(client, "last_status", None)
    if not isinstance(status, int):
        return None
    if status == 429:
        return "http_429"
    if status >= 500:
        return f"http_{status}"
    return None


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
        relation = _relation_for_arm(case, arm)
        selected = held_only_relation(relation) if arm == "short_held_only" else relation
        verifier = ObservationVerifier(client.ask, accept_above=ACCEPT_ABOVE, reject_below=REJECT_BELOW)
        verifier.begin_turn()
        started = time.perf_counter()
        report = verifier.verify(case["narration"], (selected,))
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
    print(_redact(f"holder wording probe: {message}"), file=sys.stderr)
    return 2


def _check_corpus() -> int:
    corpus = _load_corpus()
    examined = 0
    changed = 0
    for case in corpus["cases"]:
        for relation_data in case.get("relations", []):
            relation = Relation(
                thing=relation_data["thing"],
                place=relation_data.get("place"),
                holder=relation_data.get("holder"),
            )
            examined += 1
            if question_for_arm(relation, "full_both") != question_for_arm(relation, "short_held_only"):
                changed += 1
    print(f"changed questions: {changed}")
    print(f"relations examined: {examined}")
    return 1 if changed else 0


def _print_dry_run(cases: list[dict[str, Any]], samples: int) -> None:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    tokens = _estimate_tokens(cases, samples)
    print(f"case count: {len(cases)}")
    print(f"planned requests: {len(cases) * len(QUESTION_ARMS) * samples}")
    print(f"token estimate: {tokens:.2f}")
    print(f"USD ceiling: ${_ceiling(cases, samples):.6f}")


def _group_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = Counter(row.get("verdict", "unavailable") for row in rows)
    return {key: counts.get(key, 0) for key in ("accept", "uncertain", "reject", "unavailable")}


def _report_text(rows: list[dict[str, Any]]) -> tuple[str, bool]:
    lines = ["# Holder wording probe report", "", f"Rows rendered: {len(rows)}", ""]
    lines.extend(
        [
            "The 10 positive cases are the ones that exposed the defect, so passing shows the rewording "
            "fixes known failures, not that it generalizes.",
            "",
            "## Row scores",
            "",
            "| Arm | Kind | Case | Sample | Verdict | Score |",
            "| --- | --- | --- | ---: | --- | ---: |",
        ]
    )
    for row in rows:
        lines.append(
            f"| {row.get('arm')} | {row.get('kind')} | {row.get('case_id')} | {row.get('sample')} | "
            f"{row.get('verdict')} | {row.get('score')} |"
        )
    lines.extend(["", "## Counts by arm and kind", ""])
    for arm in QUESTION_ARMS:
        lines.extend(
            [
                f"### {arm}",
                "",
                "| Kind | Accept | Uncertain | Reject | Unavailable |",
                "| --- | ---: | ---: | ---: | ---: |",
            ]
        )
        for kind in CASE_KINDS:
            counts = _group_counts([row for row in rows if row.get("arm") == arm and row.get("kind") == kind])
            lines.append(
                f"| {kind} | {counts['accept']} | {counts['uncertain']} | "
                f"{counts['reject']} | {counts['unavailable']} |"
            )
        lines.append("")

    full_positive = [row for row in rows if row.get("arm") == "full_both" and row.get("kind") == "positive_held"]
    full_negative = [
        row for row in rows if row.get("arm") == "full_both" and row.get("kind") in {"wrong_holder", "absent_thing"}
    ]
    full_accepts = sum(row.get("verdict") == "accept" for row in full_positive)
    full_negative_accepts = sum(row.get("verdict") == "accept" for row in full_negative)
    lines.extend(
        [
            "## Before (full_both arm) numbers",
            "",
            f"- positive_held accepts: {full_accepts} of {len(full_positive)}",
            f"- negative accepts: {full_negative_accepts} of {len(full_negative)}",
            "",
            "short_both passing means no wording change is needed (the simpler fix).",
            "",
            "## GATE",
            "",
        ]
    )
    all_passed = True
    for arm in ("short_both", "short_held_only"):
        positive = [row for row in rows if row.get("arm") == arm and row.get("kind") == "positive_held"]
        negative = [
            row for row in rows if row.get("arm") == arm and row.get("kind") in {"wrong_holder", "absent_thing"}
        ]
        positive_accepts = sum(row.get("verdict") == "accept" for row in positive)
        negative_accepts = sum(row.get("verdict") == "accept" for row in negative)
        g1 = positive_accepts >= 18
        g2 = negative_accepts == 0
        g3 = positive_accepts >= full_accepts
        all_passed = all_passed and g1 and g2 and g3
        lines.extend(
            [
                f"- {arm} G1: {'PASS' if g1 else 'FAIL'} — positive accepts "
                f"{positive_accepts} of {len(positive)} (required at least 18 of 20)",
                f"- {arm} G2: {'PASS' if g2 else 'FAIL'} — negative accepts "
                f"{negative_accepts} of {len(negative)} (required zero of 30)",
                f"- {arm} G3: {'PASS' if g3 else 'FAIL'} — positive accepts "
                f"{positive_accepts}; full_both positive accepts {full_accepts}",
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
    modes.add_argument("--check-corpus", action="store_true")
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
        if args.check_corpus:
            return _check_corpus()
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return report_rows(args.rows, args.out)

        cases = _load_cases()
        if args.dry_run:
            _print_dry_run(cases, args.samples)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        calls_planned = len(cases) * len(QUESTION_ARMS) * args.samples
        if calls_planned > args.max_calls:
            return _error(f"planned requests {calls_planned} exceed --max-calls {args.max_calls}")
        ceiling = _ceiling(cases, args.samples)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not _lock_matches(cases):
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

"""Screen J1 context only for relations at a scene's own place."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration import j1_screen_probe as screen
from scripts.ringer.environment_narration.j1_screen_probe import (
    ACCEPT_ABOVE,
    ARMS,
    COST_PER_MILLION_INPUT_TOKENS,
    FIXED_SEED,
    QUESTION_VERSION,
    REJECT_BELOW,
    UNUSABLE_STOP_AFTER,
    _percentile,
    _redact,
    _status_stop_reason,
)
from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import ObservationVerifier, Relation

_validated_corpus = screen._validated_corpus

CASES_PATH = Path(__file__).with_name("j1_scope") / "cases.jsonl"
LOCK_PATH = Path(__file__).with_name("j1_scope") / "lock.json"
DEFAULT_CARRIED_ROWS = Path("bench/results/environment-narration/j1-screen-rows.json")
DEFAULT_SAMPLES = 5
DEFAULT_MAX_CALLS = 640
DEFAULT_MAX_USD = 0.03
GROUPS = {"scene_level", "specific_place"}
KINDS = {"positive", "negative"}
NEGATIVE_TYPES = {"missing", "remembered", "elsewhere", "lookalike"}
CASE_FIELDS = {
    "id",
    "story",
    "scene",
    "scene_place",
    "group",
    "kind",
    "negative_type",
    "contrast",
    "label",
    "narration",
    "relation",
    "note",
}
RELATION_FIELDS = {"thing", "place", "holder"}


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = _redact(json.dumps(document, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            temporary.write(text)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.replace(temporary_path, path)
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


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


def _place_forms(place: str) -> set[str]:
    lower = place.casefold()
    forms = {lower}
    if lower.startswith("the "):
        forms.add(lower[4:])
    else:
        forms.add(f"the {lower}")
    return forms


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
        for field in ("story", "scene", "scene_place", "narration", "note"):
            if not isinstance(case.get(field), str) or not case[field]:
                errors.append(f"{name}: {field} must be a non-empty string")
        group = case.get("group")
        kind = case.get("kind")
        label = case.get("label")
        negative_type = case.get("negative_type")
        contrast = case.get("contrast")
        if group not in GROUPS:
            errors.append(f"{name}: group must be scene_level or specific_place")
        if kind not in KINDS:
            errors.append(f"{name}: kind must be positive or negative")
        if (kind == "positive" and label != "accept") or (kind == "negative" and label != "reject"):
            errors.append(f"{name}: kind and label do not match")
        if kind == "positive" and negative_type is not None:
            errors.append(f"{name}: positive case must have no negative_type")
        if kind == "negative" and negative_type not in NEGATIVE_TYPES:
            errors.append(f"{name}: negative case has an unknown negative_type")
        if negative_type == "lookalike" and not isinstance(contrast, bool):
            errors.append(f"{name}: lookalike contrast must be boolean")
        if negative_type != "lookalike" and contrast is not None:
            errors.append(f"{name}: contrast is only allowed on lookalikes")
        relation = case.get("relation")
        if not isinstance(relation, dict) or set(relation) != RELATION_FIELDS:
            errors.append(f"{name}: relation fields must be exactly {sorted(RELATION_FIELDS)}")
            relation = None
        else:
            if not isinstance(relation.get("thing"), str) or not relation["thing"]:
                errors.append(f"{name}: relation thing must be a non-empty string")
            if not isinstance(relation.get("place"), str) or not relation["place"]:
                errors.append(f"{name}: relation place must be a non-empty string")
            if relation.get("holder") is not None:
                errors.append(f"{name}: relation holder must be null")
        if isinstance(relation, dict) and group in GROUPS and isinstance(case.get("scene_place"), str):
            same_place = relation.get("place") == case["scene_place"]
            if (group == "scene_level") != same_place:
                errors.append(f"{name}: group does not match relation place and scene_place")
        if (
            group == "scene_level"
            and kind == "positive"
            and isinstance(case.get("scene_place"), str)
            and isinstance(case.get("narration"), str)
            and any(form in case["narration"].casefold() for form in _place_forms(case["scene_place"]))
        ):
            errors.append(f"{name}: scene-level positive narration names scene_place")
        if (
            negative_type == "missing"
            and isinstance(relation, dict)
            and isinstance(relation.get("thing"), str)
            and isinstance(case.get("narration"), str)
            and relation["thing"].casefold() in case["narration"].casefold()
        ):
            errors.append(f"{name}: missing narration contains the thing")
    return errors


def _validated_cases(path: Path | None = None) -> tuple[list[dict[str, Any]], bytes]:
    cases, data = _load_cases(path)
    errors = _validation_errors(cases)
    if errors:
        for error in errors:
            print(_redact(error), file=sys.stderr)
        raise ValueError(f"cases validation failed with {len(errors)} problem(s)")
    return cases, data


def _print_case_counts(cases: list[dict[str, Any]]) -> None:
    for field in ("group", "kind", "negative_type"):
        counts = Counter(str(case[field]) for case in cases)
        print(f"counts by {field}:")
        for key in sorted(counts):
            print(f"  {key}: {counts[key]}")


def j1c_arm(case: dict[str, Any]) -> str:
    relation = case["relation"]
    return "J1m" if relation["holder"] is None and relation["place"] == case["scene_place"] else "V0"


def _request_payload(case: dict[str, Any], arm: str, set_name: str) -> dict[str, Any]:
    if set_name in {"scope", "heldout"}:
        return screen._request_payload(case, arm, "heldout")
    if set_name in {"regression", "corpus"}:
        return screen._request_payload(case, arm, "corpus")
    raise ValueError(f"unknown case set: {set_name}")


def _relation_for_case(case: dict[str, Any], set_name: str) -> Relation:
    if set_name == "regression":
        return screen._relation_objects(case)[0]
    relation = case["relation"]
    return Relation(thing=relation["thing"], place=relation["place"], holder=relation["holder"])


def _relations_for_case(case: dict[str, Any], set_name: str) -> tuple[Relation, ...]:
    if set_name == "regression":
        return screen._relation_objects(case)
    return (_relation_for_case(case, set_name),)


def _regression_cases(corpus: dict[str, Any]) -> list[dict[str, Any]]:
    selected = [case for case in corpus["cases"] if case.get("id") in {"a-022", "d-009"}]
    if len(selected) != 2:
        raise ValueError("corpus must contain regression ids a-022 and d-009")
    return selected


def _planned_count(scope_count: int, regression_count: int, samples: int) -> int:
    if samples < 1:
        raise ValueError("sample count must be at least 1")
    return (scope_count + regression_count) * len(ARMS) * samples


def _planned_calls(
    scope: list[dict[str, Any]], regression: list[dict[str, Any]], *, samples: int
) -> list[dict[str, Any]]:
    if samples < 1:
        raise ValueError("sample count must be at least 1")
    planned: list[dict[str, Any]] = []
    for set_name, cases in (("scope", scope), ("regression", regression)):
        order = list(cases)
        import random

        random.Random(FIXED_SEED).shuffle(order)
        for sample in range(samples):
            for case in order:
                for arm in ARMS:
                    planned.append({"set": set_name, "case": case, "arm": arm, "sample": sample})
    return planned


def _estimate_tokens(scope: list[dict[str, Any]], regression: list[dict[str, Any]], samples: int) -> float:
    chars = sum(
        len(json.dumps(_request_payload(case, arm, set_name), ensure_ascii=False, separators=(",", ":")))
        for set_name, cases in (("scope", scope), ("regression", regression))
        for case in cases
        for arm in ARMS
    )
    return chars * samples / 4


def _ceiling(scope: list[dict[str, Any]], regression: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(scope, regression, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _lock_document(corpus: dict[str, Any], cases_data: bytes, case_count: int) -> dict[str, Any]:
    return {
        "cases_sha256": _sha256(cases_data),
        "case_count": case_count,
        "corpus_combined_hash": corpus["combined"],
    }


def _lock_matches(corpus: dict[str, Any], cases_data: bytes, case_count: int) -> bool:
    try:
        document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return document == _lock_document(corpus, cases_data, case_count)


def _corpus_lock_matches(corpus: dict[str, Any]) -> bool:
    return screen._corpus_lock_matches(corpus)


def _ask_for_case(client: object, case: dict[str, Any], arm: str, set_name: str):
    def ask(_state: dict[str, object], questions: dict[str, object]) -> dict | None:
        state = _request_payload(case, arm, set_name)["input"]["state"]
        try:
            return client.ask(state, questions)
        except Exception as error:
            status = getattr(client, "last_status", None)
            if not (isinstance(status, int) and (status == 429 or status >= 500)):
                client._scope_probe_error = error
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
    case = planned["case"]
    set_name = planned["set"]
    relations = case["relations"] if set_name == "regression" else [case["relation"]]
    row = {
        "call_index": call_index,
        "set": set_name,
        "case_id": case["id"],
        "sample": planned["sample"],
        "arm": planned["arm"],
        "story": case.get("story", case.get("scene")),
        "scene": case.get("scene", case.get("story")),
        "scene_place": case.get("scene_place"),
        "group": case.get("group"),
        "negative_type": case.get("negative_type"),
        "relations": [
            {
                "thing": verdict.relation.thing,
                "label": relations[index]["label"] if set_name == "regression" else case["label"],
                "verdict": verdict.verdict,
                "score": verdict.score,
            }
            for index, verdict in enumerate(report.verdicts)
        ],
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
    return row


def run_cases(
    scope: list[dict[str, Any]],
    regression: list[dict[str, Any]],
    *,
    samples: int,
    max_calls: int,
    out: Path,
    client: object,
    cases_hash: str,
    corpus_hash: str,
) -> dict[str, Any]:
    calls = _planned_calls(scope, regression, samples=samples)
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
            relations = _relations_for_case(planned["case"], planned["set"])
            verifier = ObservationVerifier(
                _ask_for_case(client, planned["case"], planned["arm"], planned["set"]),
                accept_above=ACCEPT_ABOVE,
                reject_below=REJECT_BELOW,
            )
            verifier.begin_turn()
            started = time.perf_counter()
            report = verifier.verify(planned["case"]["narration"], relations)
            probe_error = getattr(client, "_scope_probe_error", None)
            if probe_error is not None:
                delattr(client, "_scope_probe_error")
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
            if stop_reason is None and len(document["rows"]) == len(calls):
                stop_reason = None
            elif stop_reason is not None:
                document["stop_reason"] = stop_reason
            _write_json(out, document)
            if stop_reason is not None:
                break
        if len(document["rows"]) == len(calls):
            document["stop_reason"] = None
            _write_json(out, document)
        elif document["stop_reason"] == "incomplete":
            _write_json(out, document)
        return document
    except Exception:
        document["stop_reason"] = "incomplete"
        _write_json(out, document)
        raise


def _records(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    return [(row, relation) for row in rows for relation in row.get("relations", []) if isinstance(relation, dict)]


def _scope_arm_rows(rows: list[dict[str, Any]], arm: str) -> list[dict[str, Any]]:
    return [row for row in rows if row.get("set") == "scope" and row.get("arm") == arm]


def _j1c_records(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    records = []
    for row in rows:
        if row.get("set") != "scope":
            continue
        arm = "J1m" if row.get("group") == "scene_level" else "V0"
        if row.get("arm") == arm:
            records.extend((row, relation) for relation in row.get("relations", []) if isinstance(relation, dict))
    return records


def _count(records: list[tuple[dict[str, Any], dict[str, Any]]], **fields: Any) -> int:
    return sum(all(relation.get(key) == value for key, value in fields.items()) for _row, relation in records)


def _score_range(rows: list[dict[str, Any]]) -> str:
    scores = [relation["score"] for _row, relation in _records(rows) if isinstance(relation.get("score"), (int, float))]
    return "n/a" if not scores else f"{min(scores):.2f}-{max(scores):.2f}"


def _rate(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)" if denominator else "0/0 (0.0%)"


def _scope_gate_lines(rows: list[dict[str, Any]]) -> tuple[list[str], bool]:
    j1c = _j1c_records(rows)
    v0 = [(row, relation) for row, relation in _records(_scope_arm_rows(rows, "V0"))]
    negatives = [(row, relation) for row, relation in j1c if relation.get("label") == "reject"]
    scene_positive = [
        (row, relation)
        for row, relation in j1c
        if row.get("group") == "scene_level" and relation.get("label") == "accept"
    ]
    specific_positive = [
        (row, relation)
        for row, relation in j1c
        if row.get("group") == "specific_place" and relation.get("label") == "accept"
    ]
    v0_scene_positive = [
        (row, relation)
        for row, relation in v0
        if row.get("group") == "scene_level" and relation.get("label") == "accept"
    ]
    f1_accepts = sum(relation.get("verdict") == "accept" for _row, relation in negatives)
    f2_accepts = sum(relation.get("verdict") == "accept" for _row, relation in scene_positive)
    f2_v0_accepts = sum(relation.get("verdict") == "accept" for _row, relation in v0_scene_positive)
    f3_accepts = sum(relation.get("verdict") == "accept" for _row, relation in specific_positive)
    v0_negative_accepts = _count(
        [(row, relation) for row, relation in v0 if relation.get("label") == "reject"], verdict="accept"
    )
    v0_specific_positive = [
        (row, relation)
        for row, relation in v0
        if row.get("group") == "specific_place" and relation.get("label") == "accept"
    ]
    v0_specific_accepts = _count(v0_specific_positive, verdict="accept")
    f1 = len(negatives) == 180 and f1_accepts == 0
    f2 = len(scene_positive) == 60 and f2_accepts >= 54 and f2_accepts >= f2_v0_accepts
    f3 = len(specific_positive) == 60 and f3_accepts >= 54
    lines = [
        "## Gates",
        "",
        f"- F1 negative accepts: V0 {v0_negative_accepts}; J1c {f1_accepts} — {'PASS' if f1 else 'FAIL'}",
        f"- F2 scene-level positive accepts: V0 {_rate(f2_v0_accepts, len(v0_scene_positive))}; "
        f"J1c {_rate(f2_accepts, len(scene_positive))} — {'PASS' if f2 else 'FAIL'}",
        f"- F3 specific-place positive accepts: V0 {_rate(v0_specific_accepts, len(v0_specific_positive))}; "
        f"J1c {_rate(f3_accepts, len(specific_positive))} — {'PASS' if f3 else 'FAIL'}",
    ]
    return lines, f1 and f2 and f3


def _carried_lines(rows: list[dict[str, Any]], carried_path: Path) -> tuple[list[str], bool]:
    if not carried_path.exists():
        return ["- carried gates: rows file missing — FAIL"], False
    carried_document = json.loads(carried_path.read_text(encoding="utf-8"))
    carried_rows = carried_document.get("rows")
    if not isinstance(carried_rows, list):
        return ["- carried gates: rows file missing — FAIL"], False
    carried_v0 = [row for row in carried_rows if row.get("arm") == "V0"]
    metrics = screen._metrics(carried_v0, "corpus")
    c1 = len(metrics["false_accepts"]) == 0
    false_rate = len(metrics["false_rejects"]) / metrics["accept"] if metrics["accept"] else 1
    strict_rate = len(metrics["strict_failures"]) / metrics["accept"] if metrics["accept"] else 1
    c2 = false_rate <= 0.05 and strict_rate <= 0.05
    carried_models = {str(row.get("jev_model")) for row in carried_rows if row.get("jev_model") is not None}
    fresh_models = {
        str(row.get("jev_model")) for row in rows if row.get("set") == "scope" and row.get("jev_model") is not None
    }
    model_ok = carried_models == fresh_models
    lines = [
        f"- carried C1 corpus V0 false accepts: {len(metrics['false_accepts'])} — {'PASS' if c1 else 'FAIL'}",
        f"- carried C2 corpus V0 false rejects: {_rate(len(metrics['false_rejects']), metrics['accept'])}; "
        f"strict failures: {_rate(len(metrics['strict_failures']), metrics['accept'])} — {'PASS' if c2 else 'FAIL'}",
    ]
    if not model_ok:
        lines.append("- carried gates void: Jev model changed — FAIL")
    else:
        lines.append("- carried Jev model: matching")
    return lines, c1 and c2 and model_ok


def _report_text(rows: list[dict[str, Any]], carried_path: Path) -> tuple[str, bool]:
    lines = ["# J1c scope report", "", f"Rows rendered: {len(rows)}", "", "## Metrics", ""]
    for arm in ARMS:
        selected = _scope_arm_rows(rows, arm)
        latencies = [float(row["latency_ms"]) for row in selected if isinstance(row.get("latency_ms"), (int, float))]
        models = sorted({str(row.get("jev_model")) for row in selected})
        versions = sorted({str(row.get("jev_version", row.get("question_version"))) for row in selected})
        disagreements = 0
        comparisons = 0
        by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in selected:
            by_case[str(row.get("case_id"))].append(row)
        for case_rows in by_case.values():
            for left, right in combinations(case_rows, 2):
                comparisons += 1
                disagreements += left.get("relations", [{}])[0].get("verdict") != right.get("relations", [{}])[0].get(
                    "verdict"
                )
        p50 = _percentile(latencies, 0.5) or 0
        p95 = _percentile(latencies, 0.95) or 0
        lines.extend(
            [
                f"### scope / {arm}",
                "",
                f"- sample-to-sample disagreement: {_rate(disagreements, comparisons)}; "
                f"latency p50/p95: {p50:.2f}/{p95:.2f} ms",
                f"- model/version: {', '.join(models) or 'n/a'} / {', '.join(versions) or 'n/a'}",
                "",
            ]
        )
    lines.extend(["## Negative near-misses", ""])
    for group in sorted(GROUPS):
        for negative_type in sorted(NEGATIVE_TYPES):
            selected = [
                (row, relation)
                for row, relation in _j1c_records(rows)
                if row.get("group") == group
                and row.get("negative_type") == negative_type
                and relation.get("verdict") != "reject"
            ]
            for row, relation in selected:
                lines.append(f"- {group}/{negative_type}: {row.get('case_id')} score={relation.get('score')}")
    lines.extend(["", "## Mechanism check", ""])
    lookalike = [
        (row, relation)
        for row, relation in _records(_scope_arm_rows(rows, "J1m"))
        if row.get("group") == "specific_place" and row.get("negative_type") == "lookalike"
    ]
    v0_lookalike = [
        (row, relation)
        for row, relation in _records(_scope_arm_rows(rows, "V0"))
        if row.get("group") == "specific_place" and row.get("negative_type") == "lookalike"
    ]
    j1_accepts = sum(relation.get("verdict") == "accept" for _row, relation in lookalike)
    v0_accepts = sum(relation.get("verdict") == "accept" for _row, relation in v0_lookalike)
    j1_scores = [
        relation.get("score") for _row, relation in lookalike if isinstance(relation.get("score"), (int, float))
    ]
    v0_scores = [
        relation.get("score") for _row, relation in v0_lookalike if isinstance(relation.get("score"), (int, float))
    ]
    j1_mean = sum(j1_scores) / len(j1_scores) if j1_scores else 0
    v0_mean = sum(v0_scores) / len(v0_scores) if v0_scores else 0
    lines.append(
        f"- specific-place lookalikes: J1m accepts {j1_accepts}, mean score {j1_mean:.3f}; "
        f"V0 accepts {v0_accepts}, mean score {v0_mean:.3f}"
    )
    lines.append(f"- J1m accepted at least one: {'yes' if j1_accepts else 'no'}")
    lines.extend(["", "## Regression", ""])
    for case_id in ("a-022", "d-009"):
        for arm in ARMS:
            selected = [
                row
                for row in rows
                if row.get("set") == "regression" and row.get("case_id") == case_id and row.get("arm") == arm
            ]
            lines.append(f"- {case_id} {arm}: score range {_score_range(selected)}")
    gate_lines, scope_passed = _scope_gate_lines(rows)
    carried_lines, carried_passed = _carried_lines(rows, carried_path)
    lines.extend(
        [
            "",
            *gate_lines,
            "",
            "## Carried gates",
            "",
            *carried_lines,
            "",
            f"## Overall: {'PASS' if scope_passed and carried_passed else 'FAIL'}",
        ]
    )
    return "\n".join(lines), scope_passed and carried_passed


def report_rows(rows_path: Path, out: Path, carried_rows: Path | None = None) -> int:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    report, passed = _report_text(rows, DEFAULT_CARRIED_ROWS if carried_rows is None else carried_rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact(report), encoding="utf-8")
    return 0 if passed else 1


def _print_dry_run(scope: list[dict[str, Any]], regression: list[dict[str, Any]], samples: int) -> None:
    planned = _planned_count(len(scope), len(regression), samples)
    print(f"case count: {len(scope)}")
    print("regression case count 2")
    print(
        f"planned requests: {len(scope)} fresh cases x 2 arms x {samples} + "
        f"2 regression cases x 2 arms x {samples} = {planned}"
    )
    print(f"token estimate: {_estimate_tokens(scope, regression, samples):.2f}")
    print(f"USD ceiling: ${_ceiling(scope, regression, samples):.6f}")


def _error(message: str) -> int:
    print(_redact(f"j1 scope probe: {message}"), file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--lock", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--carried-rows", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return report_rows(args.rows, args.out, args.carried_rows)
        corpus = _validated_corpus()
        corpus_lock = _corpus_lock_matches(corpus)
        if args.validate or args.lock:
            cases, cases_data = _validated_cases()
            _print_case_counts(cases)
            print(f"case count: {len(cases)}")
            print(f"corpus lock: {'matching' if corpus_lock else 'mismatch'}")
            regression = _regression_cases(corpus)
            print(f"regression ids: {', '.join(case['id'] for case in regression)}")
            if not corpus_lock:
                return 1
            if args.validate:
                return 0
            _write_json(LOCK_PATH, _lock_document(corpus, cases_data, len(cases)))
            print(f"lock: {_redact(str(LOCK_PATH))}")
            return 0
        cases, cases_data = _validated_cases()
        regression = _regression_cases(corpus)
        if args.samples < 1:
            return _error("sample count must be at least 1")
        if args.dry_run:
            _print_dry_run(cases, regression, args.samples)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        planned = _planned_count(len(cases), len(regression), args.samples)
        if planned > args.max_calls:
            return _error(f"planned requests {planned} exceed --max-calls {args.max_calls}")
        ceiling = _ceiling(cases, regression, args.samples)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not _lock_matches(corpus, cases_data, len(cases)):
            return _error("run mode requires a matching lock")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        document = run_cases(
            cases,
            regression,
            samples=args.samples,
            max_calls=args.max_calls,
            out=args.out,
            client=JevClient.from_environment(),
            cases_hash=_sha256(cases_data),
            corpus_hash=corpus["combined"],
        )
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        if args.validate:
            print(_redact(f"j1 scope probe: {error}"), file=sys.stderr)
            return 1
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

"""Screen batched verifier requests with scene and starting-place state."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import sys
import tempfile
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration.verifier_calibration import (
    _lock_matches as _calibration_lock_matches,
)
from scripts.ringer.environment_narration.verifier_calibration import (
    _redact,
    _relation_objects,
    _status_stop_reason,
    _validated_corpus,
)
from scripts.ringer.environment_narration.verifier_calibration import (
    _request_payload as _corpus_request_payload,
)
from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import QUESTION_VERSION, ObservationVerifier, Relation, _question_for

CORPUS_COMBINED_HASH = "1f18f4b41778876b7c5066a1a3d75e9db910d075e8c1ee337ab5b79b0641dc52"
J1_SCREEN_DIR = Path(__file__).with_name("j1_screen")
HELDOUT_PATH = J1_SCREEN_DIR / "heldout.jsonl"
LOCK_PATH = J1_SCREEN_DIR / "lock.json"
ARMS = ("V0", "J1m")
DEFAULT_SAMPLES_CORPUS = 2
DEFAULT_SAMPLES_HELDOUT = 5
DEFAULT_MAX_CALLS = 1300
DEFAULT_MAX_USD = 0.05
FIXED_SEED = 1729
UNUSABLE_STOP_AFTER = 3
ACCEPT_ABOVE = 0.65
REJECT_BELOW = 0.35
COST_PER_MILLION_INPUT_TOKENS = 0.042
HELDOUT_FIELDS = {
    "id",
    "story",
    "scene",
    "kind",
    "negative_type",
    "label",
    "narration",
    "relation",
    "note",
}
RELATION_FIELDS = {"thing", "place", "holder"}
NEGATIVE_TYPES = {"missing", "remembered", "elsewhere", "lookalike"}


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


def _load_heldout(path: Path | None = None) -> tuple[list[dict[str, Any]], bytes]:
    path = HELDOUT_PATH if path is None else path
    try:
        data = path.read_bytes()
    except FileNotFoundError as error:
        raise ValueError(f"held-out file is missing: {path}") from error
    cases: list[dict[str, Any]] = []
    for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            case = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"invalid held-out JSON on line {line_number}") from error
        if not isinstance(case, dict):
            raise ValueError(f"held-out record on line {line_number} is not an object")
        cases.append(case)
    if not cases:
        raise ValueError(f"held-out file has no cases: {path}")
    return cases, data


def _heldout_errors(cases: list[dict[str, Any]]) -> list[str]:
    errors = []
    seen_ids: set[str] = set()
    for index, case in enumerate(cases, start=1):
        case_name = case.get("id", f"line {index}") if isinstance(case, dict) else f"line {index}"
        if not isinstance(case, dict):
            errors.append(f"{case_name}: record must be an object")
            continue
        if set(case) != HELDOUT_FIELDS:
            errors.append(f"{case_name}: fields must be exactly {sorted(HELDOUT_FIELDS)}")
        case_id = case.get("id")
        if not isinstance(case_id, str) or not case_id:
            errors.append(f"{case_name}: id must be a non-empty string")
        elif case_id in seen_ids:
            errors.append(f"{case_name}: duplicate id")
        else:
            seen_ids.add(case_id)
        for field in ("story", "scene", "narration", "note"):
            if not isinstance(case.get(field), str) or not case[field]:
                errors.append(f"{case_name}: {field} must be a non-empty string")
        if case.get("kind") not in {"positive", "negative"}:
            errors.append(f"{case_name}: kind must be positive or negative")
        relation = case.get("relation")
        if not isinstance(relation, dict) or set(relation) != RELATION_FIELDS:
            errors.append(f"{case_name}: relation fields must be exactly {sorted(RELATION_FIELDS)}")
        else:
            if not isinstance(relation.get("thing"), str) or not relation["thing"]:
                errors.append(f"{case_name}: relation thing must be a non-empty string")
            if not isinstance(relation.get("place"), str) or not relation["place"]:
                errors.append(f"{case_name}: relation place must be a non-empty string")
            if relation.get("holder") is not None:
                errors.append(f"{case_name}: held-out relation holder must be null")
        label = case.get("label")
        negative_type = case.get("negative_type")
        if label == "accept" and negative_type is not None:
            errors.append(f"{case_name}: positive case must have no negative_type")
        elif label == "reject" and negative_type not in NEGATIVE_TYPES:
            errors.append(f"{case_name}: negative case has an unknown negative_type")
        elif label not in {"accept", "reject"}:
            errors.append(f"{case_name}: label must be accept or reject")
        if case.get("kind") == "positive" and label != "accept":
            errors.append(f"{case_name}: positive kind must have accept label")
        if case.get("kind") == "negative" and label != "reject":
            errors.append(f"{case_name}: negative kind must have reject label")
    return errors


def _validated_heldout(path: Path | None = None) -> tuple[list[dict[str, Any]], bytes]:
    cases, data = _load_heldout(path)
    errors = _heldout_errors(cases)
    if errors:
        for error in errors:
            print(_redact(error), file=sys.stderr)
        raise ValueError(f"held-out validation failed with {len(errors)} problem(s)")
    return cases, data


def _relation_for_case(case: dict[str, Any], set_name: str) -> Relation:
    if set_name == "corpus":
        return _relation_objects(case)[0]
    relation = case["relation"]
    return Relation(thing=relation["thing"], place=relation["place"], holder=relation["holder"])


def _relations_for_case(case: dict[str, Any], set_name: str) -> tuple[Relation, ...]:
    if set_name == "corpus":
        return _relation_objects(case)
    return (_relation_for_case(case, set_name),)


def _request_payload(case: dict[str, Any], arm: str, set_name: str) -> dict[str, Any]:
    if arm not in ARMS:
        raise ValueError(f"unknown arm: {arm}")
    if set_name == "corpus":
        payload = _corpus_request_payload(case)
        scene = case["story"]
        relations = _relation_objects(case)
    elif set_name == "heldout":
        relation = _relation_for_case(case, set_name)
        payload = {
            "input": {"state": {"narration": case["narration"]}, "questions": {"relation_0": _question_for(relation)}}
        }
        scene = case["scene"]
        relations = (relation,)
    else:
        raise ValueError(f"unknown case set: {set_name}")
    if arm == "J1m":
        starting_places = {
            relation.thing: relation.place
            for relation in relations
            if relation.holder is None and relation.place is not None
        }
        payload["input"]["state"] = {
            "narration": case["narration"],
            "scene": scene,
            "starting_places": starting_places,
        }
    return payload


def _planned_count(corpus_count: int, heldout_count: int, samples_corpus: int, samples_heldout: int) -> int:
    return corpus_count * len(ARMS) * samples_corpus + heldout_count * len(ARMS) * samples_heldout


def _planned_calls(
    corpus: list[dict[str, Any]], heldout: list[dict[str, Any]], *, samples_corpus: int, samples_heldout: int
) -> list[dict[str, Any]]:
    if samples_corpus < 1 or samples_heldout < 1:
        raise ValueError("sample counts must be at least 1")
    planned = []
    for set_name, cases, samples in (("corpus", corpus, samples_corpus), ("heldout", heldout, samples_heldout)):
        order = list(cases)
        random.Random(FIXED_SEED).shuffle(order)
        for sample in range(samples):
            for case in order:
                for arm in ARMS:
                    planned.append({"set": set_name, "case": case, "arm": arm, "sample": sample})
    return planned


def _estimate_tokens(
    corpus: list[dict[str, Any]], heldout: list[dict[str, Any]], samples_corpus: int, samples_heldout: int
) -> float:
    chars = (
        sum(
            len(json.dumps(_request_payload(case, arm, "corpus"), ensure_ascii=False, separators=(",", ":")))
            for case in corpus
            for arm in ARMS
        )
        * samples_corpus
    )
    chars += (
        sum(
            len(json.dumps(_request_payload(case, arm, "heldout"), ensure_ascii=False, separators=(",", ":")))
            for case in heldout
            for arm in ARMS
        )
        * samples_heldout
    )
    return chars / 4


def _ceiling(
    corpus: list[dict[str, Any]], heldout: list[dict[str, Any]], samples_corpus: int, samples_heldout: int
) -> float:
    return (
        _estimate_tokens(corpus, heldout, samples_corpus, samples_heldout)
        / 1_000_000
        * COST_PER_MILLION_INPUT_TOKENS
        * 1.5
    )


def _lock_document(corpus: dict[str, Any], heldout_data: bytes, heldout_count: int) -> dict[str, Any]:
    return {
        "corpus_combined_hash": corpus["combined"],
        "corpus_cases": len(corpus["cases"]),
        "corpus_relations": corpus["relation_count"],
        "heldout_sha256": _sha256(heldout_data),
        "heldout_cases": heldout_count,
    }


def _lock_matches(corpus: dict[str, Any], heldout_data: bytes, heldout_count: int) -> bool:
    try:
        document = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return document == _lock_document(corpus, heldout_data, heldout_count)


def _corpus_lock_matches(corpus: dict[str, Any]) -> bool:
    return corpus.get("combined") == CORPUS_COMBINED_HASH and _calibration_lock_matches(corpus)


def _ask_for_case(client: object, case: dict[str, Any], arm: str, set_name: str):
    def ask(_state: dict[str, object], questions: dict[str, object]) -> dict | None:
        state = _request_payload(case, arm, set_name)["input"]["state"]
        try:
            return client.ask(state, questions)
        except Exception as error:
            status = getattr(client, "last_status", None)
            if not (isinstance(status, int) and (status == 429 or status >= 500)):
                client._j1_probe_error = error
            raise

    return ask


def _row(
    call_index: int,
    planned: dict[str, Any],
    report: object,
    client: object,
    latency_ms: float,
    corpus_hash: str,
    heldout_hash: str,
) -> dict[str, Any]:
    case = planned["case"]
    set_name = planned["set"]
    relations = case["relations"] if set_name == "corpus" else [case["relation"]]
    return {
        "call_index": call_index,
        "set": set_name,
        "case_id": case["id"],
        "sample": planned["sample"],
        "arm": planned["arm"],
        "story": case.get("story", case.get("scene")),
        "category": case.get("category"),
        "negative_type": case.get("negative_type"),
        "relations": [
            {
                "thing": verdict.relation.thing,
                "label": relations[index]["label"] if set_name == "corpus" else case["label"],
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
        "corpus_combined_hash": corpus_hash,
        "heldout_sha256": heldout_hash,
    }


def run_cases(
    corpus: list[dict[str, Any]],
    heldout: list[dict[str, Any]],
    *,
    samples_corpus: int,
    samples_heldout: int,
    max_calls: int,
    out: Path,
    client: object,
    corpus_hash: str,
    heldout_hash: str,
) -> dict[str, Any]:
    calls = _planned_calls(corpus, heldout, samples_corpus=samples_corpus, samples_heldout=samples_heldout)
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": "incomplete",
        "corpus_combined_hash": corpus_hash,
        "heldout_sha256": heldout_hash,
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
            probe_error = getattr(client, "_j1_probe_error", None)
            if probe_error is not None:
                delattr(client, "_j1_probe_error")
                raise probe_error
            latency_ms = (time.perf_counter() - started) * 1000
            document["rows"].append(_row(call_index, planned, report, client, latency_ms, corpus_hash, heldout_hash))
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


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _records(rows: list[dict[str, Any]], set_name: str | None = None) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    records = []
    for row in rows:
        if set_name is not None and row.get("set") != set_name:
            continue
        for relation in row.get("relations", []):
            if isinstance(relation, dict):
                records.append((row, relation))
    return records


def _metrics(rows: list[dict[str, Any]], set_name: str) -> dict[str, Any]:
    records = _records(rows, set_name)
    required = [(row, relation) for row, relation in records if row.get("category") != "invention_unreported"]
    accept_count = sum(relation.get("label") == "accept" for _row, relation in required)
    reject_count = sum(relation.get("label") == "reject" for _row, relation in required)
    false_accepts = [
        (row, relation)
        for row, relation in records
        if relation.get("label") == "reject" and relation.get("verdict") == "accept"
    ]
    false_rejects = [
        (row, relation)
        for row, relation in required
        if relation.get("label") == "accept" and relation.get("verdict") == "reject"
    ]
    strict_failures = [
        (row, relation)
        for row, relation in required
        if relation.get("label") == "accept" and relation.get("verdict") != "accept"
    ]
    latencies = [float(row["latency_ms"]) for row in rows if isinstance(row.get("latency_ms"), (int, float))]
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[str(row.get("case_id"))].append(row)
    disagreements = 0
    comparisons = 0
    for case_rows in by_case.values():
        for left, right in combinations(case_rows, 2):
            for left_relation, right_relation in zip(
                left.get("relations", []), right.get("relations", []), strict=False
            ):
                comparisons += 1
                disagreements += left_relation.get("verdict") != right_relation.get("verdict")
    return {
        "records": len(records),
        "accept": accept_count,
        "reject": reject_count,
        "false_accepts": false_accepts,
        "false_rejects": false_rejects,
        "strict_failures": strict_failures,
        "disagreements": disagreements,
        "comparisons": comparisons,
        "p50": _percentile(latencies, 0.50),
        "p95": _percentile(latencies, 0.95),
    }


def _score_range(rows: list[dict[str, Any]]) -> str:
    scores = [relation["score"] for _row, relation in _records(rows) if isinstance(relation.get("score"), (int, float))]
    return "n/a" if not scores else f"{min(scores):.2f}-{max(scores):.2f}"


def _rate(numerator: int, denominator: int) -> str:
    return f"{numerator}/{denominator} ({100 * numerator / denominator:.1f}%)" if denominator else "0/0 (0.0%)"


def _gate_lines(rows: list[dict[str, Any]]) -> tuple[list[str], bool]:
    lines = ["## Gates", ""]
    corpus_v0 = _metrics([row for row in rows if row.get("arm") == "V0"], "corpus")
    corpus_j1 = _metrics([row for row in rows if row.get("arm") == "J1m"], "corpus")
    heldout_v0 = _records([row for row in rows if row.get("arm") == "V0"], "heldout")
    heldout_j1 = _records([row for row in rows if row.get("arm") == "J1m"], "heldout")
    c1 = len(corpus_j1["false_accepts"]) == 0
    c2_false = len(corpus_j1["false_rejects"]) / corpus_j1["accept"] if corpus_j1["accept"] else 1
    c2_strict = len(corpus_j1["strict_failures"]) / corpus_j1["accept"] if corpus_j1["accept"] else 1
    c2 = c2_false <= 0.05 and c2_strict <= 0.05
    j1_negative = [relation for _row, relation in heldout_j1 if relation.get("label") == "reject"]
    j1_positive = [relation for _row, relation in heldout_j1 if relation.get("label") == "accept"]
    v0_positive = [relation for _row, relation in heldout_v0 if relation.get("label") == "accept"]
    j1_negative_accepts = sum(relation.get("verdict") == "accept" for relation in j1_negative)
    j1_positive_accepts = sum(relation.get("verdict") == "accept" for relation in j1_positive)
    v0_positive_accepts = sum(relation.get("verdict") == "accept" for relation in v0_positive)
    h1 = j1_negative_accepts == 0
    h2 = (
        bool(j1_positive)
        and j1_positive_accepts * 100 >= len(j1_positive) * 90
        and j1_positive_accepts >= v0_positive_accepts
    )
    v0_negative_accepts = sum(
        relation.get("verdict") == "accept" for _row, relation in heldout_v0 if relation.get("label") == "reject"
    )
    c1_line = (
        f"- C1 corpus false accepts: V0 {len(corpus_v0['false_accepts'])}; "
        f"J1m {len(corpus_j1['false_accepts'])} — {'PASS' if c1 else 'FAIL'}"
    )
    c2_line = (
        f"- C2 corpus false rejects: V0 {_rate(len(corpus_v0['false_rejects']), corpus_v0['accept'])}; "
        f"J1m {_rate(len(corpus_j1['false_rejects']), corpus_j1['accept'])}; "
        f"strict J1m {_rate(len(corpus_j1['strict_failures']), corpus_j1['accept'])} — "
        f"{'PASS' if c2 else 'FAIL'}"
    )
    h1_line = (
        f"- H1 held-out negative accepts: V0 {v0_negative_accepts}; "
        f"J1m {j1_negative_accepts} — {'PASS' if h1 else 'FAIL'}"
    )
    h2_line = (
        f"- H2 held-out positive accepts: V0 {v0_positive_accepts}/{len(v0_positive)}; "
        f"J1m {j1_positive_accepts}/{len(j1_positive)} — {'PASS' if h2 else 'FAIL'}"
    )
    lines.extend(
        [
            c1_line,
            c2_line,
            h1_line,
            h2_line,
            f"- J1m overall: {'PASS' if c1 and c2 and h1 and h2 else 'FAIL'}",
            "",
        ]
    )
    return lines, c1 and c2 and h1 and h2


def _report_text(rows: list[dict[str, Any]]) -> tuple[str, bool]:
    lines = ["# J1m screen report", "", f"Rows rendered: {len(rows)}", "", "## Metrics", ""]
    for set_name in ("corpus", "heldout"):
        for arm in ARMS:
            selected = [row for row in rows if row.get("set") == set_name and row.get("arm") == arm]
            metric = _metrics(selected, set_name)
            disagreement = _rate(metric["disagreements"], metric["comparisons"])
            p50 = "n/a" if metric["p50"] is None else f"{metric['p50']:.2f}"
            p95 = "n/a" if metric["p95"] is None else f"{metric['p95']:.2f}"
            models = sorted({str(row.get("jev_model")) for row in selected})
            versions = sorted({str(row.get("question_version", row.get("jev_version"))) for row in selected})
            lines.extend(
                [
                    f"### {set_name} / {arm}",
                    "",
                    f"- relations: {metric['records']}; accept labels: {metric['accept']}; "
                    f"reject labels: {metric['reject']}",
                    f"- false accepts: {len(metric['false_accepts'])}; "
                    f"false rejects: {len(metric['false_rejects'])}; "
                    f"strict failures: {len(metric['strict_failures'])}",
                    f"- sample-to-sample disagreement: {disagreement}; latency p50/p95: {p50}/{p95} ms",
                    f"- model/version: {', '.join(models) or 'n/a'} / {', '.join(versions) or 'n/a'}",
                    "",
                ]
            )
            if set_name == "corpus":
                for field in ("category", "story"):
                    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
                    for row in selected:
                        groups[str(row.get(field))].append(row)
                    lines.append(f"#### {field} rows")
                    lines.append("")
                    for group, group_rows in sorted(groups.items()):
                        group_metric = _metrics(group_rows, set_name)
                        lines.append(
                            f"- {group}: false accepts {len(group_metric['false_accepts'])}; "
                            f"false rejects {len(group_metric['false_rejects'])}; "
                            f"strict failures {len(group_metric['strict_failures'])}"
                        )
                    lines.append("")
    lines.extend(["## Held-out negative types and case score ranges", ""])
    for negative_type in sorted(NEGATIVE_TYPES):
        selected = [row for row in rows if row.get("set") == "heldout" and row.get("negative_type") == negative_type]
        accepts = sum(
            relation.get("verdict") == "accept"
            for _row, relation in _records(selected)
            if relation.get("label") == "reject"
        )
        lines.append(f"- {negative_type}: negative accepts {accepts}; score range {_score_range(selected)}")
    lines.extend(["", "### Held-out verdict counts", ""])
    for arm in ARMS:
        selected = [row for row in rows if row.get("set") == "heldout" and row.get("arm") == arm]
        positive_counts = Counter(
            relation.get("verdict") for _row, relation in _records(selected) if relation.get("label") == "accept"
        )
        negative_accepts = sum(
            relation.get("verdict") == "accept"
            for _row, relation in _records(selected)
            if relation.get("label") == "reject"
        )
        lines.append(
            f"- {arm}: positive accept/uncertain/reject "
            f"{positive_counts['accept']}/{positive_counts['uncertain']}/{positive_counts['reject']}; "
            f"negative accepts {negative_accepts}"
        )
    lines.extend(["", "## False rows", ""])
    for row, relation in [
        item
        for item in _records(rows, "corpus")
        if item[1].get("label") == "reject" and item[1].get("verdict") == "accept"
    ]:
        lines.append(
            f"- false accept: {row.get('arm')} {row.get('case_id')} "
            f"relation {relation.get('thing')} score={relation.get('score')}"
        )
    for row, relation in [
        item
        for item in _records(rows, "corpus")
        if item[1].get("label") == "accept" and item[1].get("verdict") == "reject"
    ]:
        lines.append(
            f"- false reject: {row.get('arm')} {row.get('case_id')} "
            f"relation {relation.get('thing')} score={relation.get('score')}"
        )
    lines.extend(["", "## Held-out case score ranges", ""])
    seen: set[tuple[str, str]] = set()
    for row in rows:
        key = (str(row.get("arm")), str(row.get("case_id")))
        if row.get("set") == "heldout" and key not in seen:
            seen.add(key)
            selected = [
                item
                for item in rows
                if item.get("set") == "heldout" and item.get("arm") == key[0] and item.get("case_id") == key[1]
            ]
            lines.append(f"- {key[0]} {key[1]}: {_score_range(selected)}")
    gate_lines, passed = _gate_lines(rows)
    lines.extend(["", *gate_lines])
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


def _print_dry_run(
    corpus: dict[str, Any], heldout: list[dict[str, Any]], samples_corpus: int, samples_heldout: int
) -> None:
    print(f"corpus case count: {len(corpus['cases'])}")
    print(f"held-out case count: {len(heldout)}")
    print(
        f"planned requests: corpus {len(corpus['cases'])} x 2 arms x {samples_corpus} + "
        f"held-out {len(heldout)} x 2 arms x {samples_heldout} = "
        f"{_planned_count(len(corpus['cases']), len(heldout), samples_corpus, samples_heldout)}"
    )
    print(f"token estimate: {_estimate_tokens(corpus['cases'], heldout, samples_corpus, samples_heldout):.2f}")
    print(f"USD ceiling: ${_ceiling(corpus['cases'], heldout, samples_corpus, samples_heldout):.6f}")


def _error(message: str) -> int:
    print(_redact(f"j1 screen probe: {message}"), file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--lock", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--samples-corpus", type=int, default=DEFAULT_SAMPLES_CORPUS)
    parser.add_argument("--samples-heldout", type=int, default=DEFAULT_SAMPLES_HELDOUT)
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
        corpus = _validated_corpus()
        if args.validate or args.lock:
            corpus_lock = _corpus_lock_matches(corpus)
            print(f"corpus case count: {len(corpus['cases'])}")
            print(f"corpus relation count: {corpus['relation_count']}")
            print(f"corpus lock: {'matching' if corpus_lock else 'mismatch'}")
            try:
                heldout, heldout_data = _validated_heldout()
            except ValueError as error:
                if args.validate and "missing" in str(error):
                    print("held-out case count: unavailable")
                    return 0 if corpus_lock else 1
                raise
            print(f"held-out case count: {len(heldout)}")
            if args.validate:
                return 0 if corpus_lock else 1
            if not corpus_lock:
                return _error("--lock requires a matching corpus lock")
            _write_json(LOCK_PATH, _lock_document(corpus, heldout_data, len(heldout)))
            print(f"lock: {_redact(str(LOCK_PATH))}")
            return 0
        heldout, heldout_data = _validated_heldout()
        if args.samples_corpus < 1 or args.samples_heldout < 1:
            return _error("sample counts must be at least 1")
        if args.dry_run:
            _print_dry_run(corpus, heldout, args.samples_corpus, args.samples_heldout)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        calls_planned = _planned_count(len(corpus["cases"]), len(heldout), args.samples_corpus, args.samples_heldout)
        if calls_planned > args.max_calls:
            return _error(f"planned requests {calls_planned} exceed --max-calls {args.max_calls}")
        ceiling = _ceiling(corpus["cases"], heldout, args.samples_corpus, args.samples_heldout)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not _lock_matches(corpus, heldout_data, len(heldout)):
            return _error("run mode requires a matching lock")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        client = JevClient.from_environment()
        document = run_cases(
            corpus["cases"],
            heldout,
            samples_corpus=args.samples_corpus,
            samples_heldout=args.samples_heldout,
            max_calls=args.max_calls,
            out=args.out,
            client=client,
            corpus_hash=corpus["combined"],
            heldout_hash=_sha256(heldout_data),
        )
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        if args.validate:
            print(_redact(f"j1 screen probe: {error}"), file=sys.stderr)
            return 1
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

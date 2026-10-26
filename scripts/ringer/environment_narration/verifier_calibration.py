"""Offline-first calibration harness for the environment observation verifier."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import sys
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from storygame.runtime.jev import JevClient
from storygame.runtime.observation_verifier import (
    QUESTION_VERSION,
    ObservationVerifier,
    Relation,
    _question_for,
)

CORPUS_DIR = Path(__file__).with_name("verifier_corpus")
LOCK_NAME = "corpus.lock.json"
MIN_CASES = 200
DEFAULT_SAMPLES = 2
DEFAULT_MAX_CALLS = 1000
DEFAULT_MAX_USD = 1.0
FIXED_SEED = 1729
UNUSABLE_STOP_AFTER = 3
ACCEPT_ABOVE = 0.65
REJECT_BELOW = 0.35
COST_PER_MILLION_INPUT_TOKENS = 0.042
KNOWN_CATEGORIES = (
    "positive_plain",
    "positive_paraphrase",
    "negated",
    "hypothetical_or_remembered",
    "wrong_holder",
    "wrong_place",
    "not_mentioned",
    "lookalike_substitute",
    "invention_unreported",
    "multi_mixed",
)
CASE_FIELDS = {
    "id",
    "story",
    "category",
    "narration",
    "relations",
    "undetectable_invention",
    "note",
}
RELATION_FIELDS = {"thing", "place", "holder", "label"}


class CorpusValidationError(ValueError):
    """Raised after all corpus problems have been printed."""


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


def _load_corpus() -> dict[str, Any]:
    files = sorted(CORPUS_DIR.glob("cases-*.jsonl"))
    if not files:
        raise ValueError(f"no corpus files found in {CORPUS_DIR}")
    cases: list[dict[str, Any]] = []
    file_hashes: dict[str, str] = {}
    file_lines: dict[str, list[tuple[int, object]]] = {}
    combined = hashlib.sha256()
    for path in files:
        data = path.read_bytes()
        file_hashes[path.name] = _sha256(data)
        combined.update(data)
        parsed: list[tuple[int, object]] = []
        for line_number, line in enumerate(data.decode("utf-8").splitlines(), start=1):
            if not line.strip():
                parsed.append((line_number, None))
                continue
            try:
                parsed.append((line_number, json.loads(line)))
            except json.JSONDecodeError as error:
                parsed.append((line_number, f"invalid JSON: {error.msg}"))
        file_lines[path.name] = parsed
        cases.extend(value for _line_number, value in parsed if isinstance(value, dict))
    return {
        "cases": cases,
        "file_hashes": file_hashes,
        "file_lines": file_lines,
        "combined": combined.hexdigest(),
        "files": [path.name for path in files],
    }


def _case_label(case: object, filename: str, line_number: int) -> str:
    if isinstance(case, dict) and isinstance(case.get("id"), str) and case["id"]:
        return case["id"]
    return f"{filename}:{line_number}"


def _validation_errors(corpus: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    seen_ids: set[str] = set()
    category_counts: Counter[str] = Counter()
    story_counts: Counter[str] = Counter()
    label_counts: Counter[str] = Counter()
    relation_count = 0
    for filename, entries in corpus["file_lines"].items():
        for line_number, case in entries:
            case_id = _case_label(case, filename, line_number)
            if not isinstance(case, dict):
                errors.append(f"{case_id}: record must be an object")
                continue
            current_id = case.get("id")
            if not isinstance(current_id, str) or not current_id:
                errors.append(f"{case_id}: id must be a non-empty string")
            elif current_id in seen_ids:
                errors.append(f"{current_id}: duplicate id")
            else:
                seen_ids.add(current_id)
            if set(case) != CASE_FIELDS:
                errors.append(f"{case_id}: fields must be exactly {sorted(CASE_FIELDS)}")
            for field in ("story", "category", "narration", "note"):
                if not isinstance(case.get(field), str):
                    errors.append(f"{case_id}: {field} must be a string")
            category = case.get("category")
            if category not in KNOWN_CATEGORIES:
                errors.append(f"{case_id}: unknown category {category!r}")
            elif isinstance(category, str):
                category_counts[category] += 1
            story = case.get("story")
            if isinstance(story, str):
                story_counts[story] += 1
            invention = case.get("undetectable_invention")
            if not isinstance(invention, bool):
                errors.append(f"{case_id}: undetectable_invention must be boolean")
            elif invention is not (category == "invention_unreported"):
                errors.append(f"{case_id}: undetectable_invention does not match category")

            relations = case.get("relations")
            if not isinstance(relations, list) or not relations:
                errors.append(f"{case_id}: relations must be a non-empty list")
                continue
            for relation_index, relation in enumerate(relations):
                relation_id = f"{case_id} relation {relation_index}"
                if not isinstance(relation, dict):
                    errors.append(f"{relation_id}: relation must be an object")
                    continue
                if set(relation) != RELATION_FIELDS:
                    errors.append(f"{relation_id}: fields must be exactly {sorted(RELATION_FIELDS)}")
                thing = relation.get("thing")
                if not isinstance(thing, str) or not thing:
                    errors.append(f"{relation_id}: thing must be a non-empty string")
                place = relation.get("place")
                holder = relation.get("holder")
                for field, value in (("place", place), ("holder", holder)):
                    if value is not None and (not isinstance(value, str) or not value):
                        errors.append(f"{relation_id}: {field} must be a non-empty string or null")
                if place is not None and holder is not None:
                    errors.append(f"{relation_id}: place and holder cannot both be set")
                label = relation.get("label")
                if label not in {"accept", "reject"}:
                    errors.append(f"{relation_id}: label must be accept or reject")
                else:
                    label_counts[label] += 1
                relation_count += 1
    if len(seen_ids) < MIN_CASES:
        errors.append(f"corpus: {len(seen_ids)} cases is below minimum {MIN_CASES}")
    if relation_count == 0:
        errors.append("corpus: no relations found")
    else:
        reject_share = label_counts["reject"] / relation_count
        if not 0.45 <= reject_share <= 0.55:
            errors.append(f"corpus: reject relation share {reject_share:.3f} is outside 45-55%")
    corpus["category_counts"] = category_counts
    corpus["story_counts"] = story_counts
    corpus["label_counts"] = label_counts
    corpus["relation_count"] = relation_count
    return errors


def _validated_corpus() -> dict[str, Any]:
    corpus = _load_corpus()
    errors = _validation_errors(corpus)
    if errors:
        for error in errors:
            print(_redact(error), file=sys.stderr)
        raise CorpusValidationError(f"corpus validation failed with {len(errors)} problem(s)")
    return corpus


def _lock_path() -> Path:
    return CORPUS_DIR / LOCK_NAME


def _lock_document(corpus: dict[str, Any]) -> dict[str, Any]:
    relation_count = corpus.get("relation_count")
    if relation_count is None:
        relation_count = sum(len(case.get("relations", [])) for case in corpus["cases"])
    return {
        "files": dict(sorted(corpus["file_hashes"].items())),
        "combined": corpus["combined"],
        "cases": len(corpus["cases"]),
        "relations": relation_count,
    }


def _lock_matches(corpus: dict[str, Any]) -> bool:
    try:
        document = json.loads(_lock_path().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    return document == _lock_document(corpus)


def _print_validation_summary(corpus: dict[str, Any]) -> None:
    print(f"cases: {len(corpus['cases'])}")
    print(f"relations: {corpus['relation_count']}")
    print("counts by category:")
    for key in sorted(corpus["category_counts"]):
        print(f"  {key}: {corpus['category_counts'][key]}")
    print("counts by story:")
    for key in sorted(corpus["story_counts"]):
        print(f"  {key}: {corpus['story_counts'][key]}")
    print("counts by label:")
    for key in sorted(corpus["label_counts"]):
        print(f"  {key}: {corpus['label_counts'][key]}")
    print("per-file SHA-256:")
    for key, value in sorted(corpus["file_hashes"].items()):
        print(f"  {key}: {value}")
    print(f"combined SHA-256: {corpus['combined']}")


def _relation_objects(case: dict[str, Any]) -> tuple[Relation, ...]:
    return tuple(
        Relation(thing=item["thing"], place=item["place"], holder=item["holder"]) for item in case["relations"]
    )


def _request_payload(case: dict[str, Any]) -> dict[str, Any]:
    questions = {f"relation_{index}": _question_for(relation) for index, relation in enumerate(_relation_objects(case))}
    return {"input": {"state": {"narration": case["narration"]}, "questions": questions}}


def _estimate_tokens(cases: list[dict[str, Any]], samples: int) -> float:
    request_chars = sum(
        len(json.dumps(_request_payload(case), ensure_ascii=False, separators=(",", ":"))) for case in cases
    )
    return request_chars * samples / 4


def _print_dry_run(corpus: dict[str, Any], samples: int) -> None:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    cases = corpus["cases"]
    planned = len(cases) * samples
    tokens = _estimate_tokens(cases, samples)
    ceiling = tokens / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5
    print(f"cases: {len(cases)}")
    print(f"relations: {corpus['relation_count']}")
    print(f"planned requests: {planned}")
    print(f"token estimate: {tokens:.2f}")
    print(f"USD ceiling: ${ceiling:.6f}")
    print("cases and relations:")
    for case in cases:
        print(f"  {case['id']}: {len(case['relations'])} relation(s)")


def _planned_calls(cases: list[dict[str, Any]], samples: int) -> list[tuple[int, dict[str, Any], int]]:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    order = list(cases)
    random.Random(FIXED_SEED).shuffle(order)
    calls: list[tuple[int, dict[str, Any], int]] = []
    call_index = 1
    for sample in range(samples):
        for case in order:
            calls.append((call_index, case, sample))
            call_index += 1
    return calls


def _status_stop_reason(client: object) -> str | None:
    status = getattr(client, "last_status", None)
    if not isinstance(status, int):
        return None
    if status == 429:
        return "http_429"
    if status >= 500:
        return f"http_{status}"
    return None


def _run(corpus: dict[str, Any], samples: int, max_calls: int, out: Path) -> dict[str, Any]:
    client = JevClient.from_environment()
    calls = _planned_calls(corpus["cases"], samples)
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": None,
        "corpus_combined_hash": corpus["combined"],
    }
    consecutive_unusable = 0
    for call_index, case, sample in calls[:max_calls]:
        verifier = ObservationVerifier(client.ask, accept_above=ACCEPT_ABOVE, reject_below=REJECT_BELOW)
        verifier.begin_turn()
        started = time.perf_counter()
        report = verifier.verify(case["narration"], _relation_objects(case))
        measured_latency_ms = (time.perf_counter() - started) * 1000
        row = {
            "call_index": call_index,
            "case_id": case["id"],
            "sample": sample,
            "story": case["story"],
            "category": case["category"],
            "undetectable_invention": case["undetectable_invention"],
            "narration_chars": len(case["narration"]),
            "relations": [
                {
                    "thing": verdict.relation.thing,
                    "label": case["relations"][index]["label"],
                    "verdict": verdict.verdict,
                    "score": verdict.score,
                }
                for index, verdict in enumerate(report.verdicts)
            ],
            "outcome": report.outcome,
            "failure": report.failure,
            "latency_ms": measured_latency_ms,
            "jev_model": getattr(client, "last_model", None),
            "thresholds": {"accept_above": ACCEPT_ABOVE, "reject_below": REJECT_BELOW},
            "question_version": QUESTION_VERSION,
            "corpus_combined_hash": corpus["combined"],
        }
        document["rows"].append(row)
        stop_reason = None
        status_reason = _status_stop_reason(client)
        if status_reason is not None:
            stop_reason = status_reason
        elif report.outcome in {"unavailable", "malformed"}:
            consecutive_unusable += 1
            if consecutive_unusable >= UNUSABLE_STOP_AFTER:
                stop_reason = "three_consecutive_unusable"
        else:
            consecutive_unusable = 0
        if stop_reason is None and len(document["rows"]) >= max_calls:
            stop_reason = "max_calls"
        if stop_reason is not None:
            document["stop_reason"] = stop_reason
        _write_json(out, document)
        if stop_reason is not None:
            break
    return document


def _percentile(values: list[float], percentile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * percentile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _rate(numerator: int, denominator: int) -> str:
    percentage = 100 * numerator / denominator if denominator else 0
    return f"{numerator} / {denominator} ({percentage:.1f}%)"


def _wilson_upper(successes: int, trials: int) -> float:
    if not trials:
        return 0.0
    z = 1.959963984540054
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = proportion + z * z / (2 * trials)
    spread = z * math.sqrt(proportion * (1 - proportion) / trials + z * z / (4 * trials * trials))
    return (center + spread) / denominator


def _row_records(rows: list[dict[str, Any]]) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    records = []
    for row in rows:
        for relation in row.get("relations", []):
            if isinstance(relation, dict):
                records.append((row, relation))
    return records


def _disagreement(rows: list[dict[str, Any]]) -> tuple[int, int]:
    by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_case[str(row.get("case_id"))].append(row)
    disagreements = 0
    comparisons = 0
    for case_rows in by_case.values():
        for left, right in combinations(case_rows, 2):
            left_relations = left.get("relations", [])
            right_relations = right.get("relations", [])
            for index in range(min(len(left_relations), len(right_relations))):
                comparisons += 1
                if left_relations[index].get("verdict") != right_relations[index].get("verdict"):
                    disagreements += 1
    return disagreements, comparisons


def _metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    records = _row_records(rows)
    count = Counter()
    for _row, relation in records:
        label = relation.get("label")
        verdict = relation.get("verdict")
        count[("label", label)] += 1
        count[("verdict", verdict)] += 1
        count[("split", verdict, label)] += 1
    false_accepts = sum(
        relation.get("label") == "reject" and relation.get("verdict") == "accept" for _row, relation in records
    )
    false_rejects = sum(
        relation.get("label") == "accept" and relation.get("verdict") == "reject" for _row, relation in records
    )
    strict_failures = sum(
        relation.get("label") == "accept" and relation.get("verdict") != "accept" for _row, relation in records
    )
    disagreement, comparisons = _disagreement(rows)
    latencies = [float(row["latency_ms"]) for row in rows if isinstance(row.get("latency_ms"), (int, float))]
    return {
        "records": len(records),
        "label_accept": count[("label", "accept")],
        "label_reject": count[("label", "reject")],
        "verdict_accept": count[("verdict", "accept")],
        "verdict_reject": count[("verdict", "reject")],
        "uncertain": count[("verdict", "uncertain")],
        "unavailable": count[("verdict", "unavailable")],
        "uncertain_accept": count[("split", "uncertain", "accept")],
        "uncertain_reject": count[("split", "uncertain", "reject")],
        "unavailable_accept": count[("split", "unavailable", "accept")],
        "unavailable_reject": count[("split", "unavailable", "reject")],
        "false_accepts": false_accepts,
        "false_rejects": false_rejects,
        "strict_failures": strict_failures,
        "disagreement": disagreement,
        "comparisons": comparisons,
        "p50": _percentile(latencies, 0.50),
        "p95": _percentile(latencies, 0.95),
        "wilson": _wilson_upper(false_accepts, count[("label", "reject")]),
    }


def _group_rows(rows: list[dict[str, Any]], field: str) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row.get(field)
        grouped["unknown" if value is None else str(value)].append(row)
    return dict(sorted(grouped.items()))


def _metric_table(rows: list[dict[str, Any]], title: str) -> list[str]:
    groups = {"overall": rows} if title == "overall" else _group_rows(rows, title)
    lines = [
        f"### {title}",
        "",
        "| Group | Relations | Label A | Label R | Verdict A | Verdict R | Uncertain | Unavailable | "
        "Uncertain A/R | Unavailable A/R | False accepts | False rejects | Strict A-label failures | "
        "Disagreement | Latency p50/p95 ms | Wilson FA upper |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | "
        "---: | ---: | ---: | ---: | ---: |",
    ]
    for group, group_rows in groups.items():
        metric = _metrics(group_rows)
        disagreement = _rate(metric["disagreement"], metric["comparisons"])
        p50 = "n/a" if metric["p50"] is None else f"{metric['p50']:.2f}"
        p95 = "n/a" if metric["p95"] is None else f"{metric['p95']:.2f}"
        lines.append(
            f"| {group} | {metric['records']} | {metric['label_accept']} | {metric['label_reject']} | "
            f"{metric['verdict_accept']} | {metric['verdict_reject']} | {metric['uncertain']} | "
            f"{metric['unavailable']} | "
            f"{metric['uncertain_accept']}/{metric['uncertain_reject']} | "
            f"{metric['unavailable_accept']}/{metric['unavailable_reject']} | "
            f"{metric['false_accepts']} | {metric['false_rejects']} | {metric['strict_failures']} | {disagreement} | "
            f"{p50}/{p95} | {metric['wilson']:.3f} ({metric['wilson'] * 100:.1f}%) |"
        )
    lines.append("")
    return lines


def _false_rows(
    rows: list[dict[str, Any]], label: str, verdict: str
) -> list[tuple[dict[str, Any], dict[str, Any], int]]:
    matches = []
    for row in rows:
        for index, relation in enumerate(row.get("relations", []), start=1):
            if relation.get("label") == label and relation.get("verdict") == verdict:
                matches.append((row, relation, index))
    return matches


def _threshold_sweep(rows: list[dict[str, Any]]) -> list[str]:
    lines = [
        "## POST-HOC threshold sweep",
        "",
        "not the gate; do not tune and re-score on the same corpus",
        "",
        "| accept_above | reject_below | Required false accepts | Required plain false rejects | "
        "Required strict accept-label failures |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    required = [row for row in rows if row.get("category") != "invention_unreported"]
    for accept_above in (0.5, 0.6, 0.65, 0.7, 0.8, 0.9):
        reject_below = 1 - accept_above
        swept_rows = []
        for row in required:
            copied = dict(row)
            copied["relations"] = []
            for relation in row.get("relations", []):
                copied_relation = dict(relation)
                score = relation.get("score")
                if isinstance(score, (int, float)) and not isinstance(score, bool):
                    if score > accept_above:
                        copied_relation["verdict"] = "accept"
                    elif score < reject_below:
                        copied_relation["verdict"] = "reject"
                    else:
                        copied_relation["verdict"] = "uncertain"
                copied["relations"].append(copied_relation)
            swept_rows.append(copied)
        metric = _metrics(swept_rows)
        lines.append(
            f"| {accept_above:.2f} | {reject_below:.2f} | {metric['false_accepts']} | "
            f"{metric['false_rejects']} | {metric['strict_failures']} |"
        )
    lines.append("")
    return lines


def _report(rows_path: Path, out: Path) -> None:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    lines = ["# Observation verifier calibration report", "", f"Rows rendered: {len(rows)}", "", "## Row results", ""]
    for row in rows:
        lines.extend(
            [
                f"### Call {row.get('call_index')} — {row.get('case_id')}",
                "",
                f"- Category: {row.get('category')}; sample: {row.get('sample')}; outcome: {row.get('outcome')}",
                f"- Model: {row.get('jev_model')}; latency: {row.get('latency_ms')} ms",
            ]
        )
        for index, relation in enumerate(row.get("relations", []), start=1):
            lines.append(
                f"- Relation {index} ({relation.get('thing')}): label={relation.get('label')}, "
                f"verdict={relation.get('verdict')}, score={relation.get('score')}"
            )
        lines.append("")

    lines.extend(
        [
            "## Summary tables",
            "",
            "The sample is limited; the Wilson value is a 95% upper bound for the false-accept rate over "
            "reject-labelled relations.",
            "",
        ]
    )
    for title in ("category", "story", "jev_model", "overall"):
        lines.extend(_metric_table(rows, title))

    false_accepts = _false_rows(rows, "reject", "accept")
    false_rejects = _false_rows(rows, "accept", "reject")
    lines.extend([f"## FALSE ACCEPTS ({len(false_accepts)})", "", f"Count: {len(false_accepts)}", ""])
    if false_accepts:
        for row, relation, index in false_accepts:
            lines.append(
                f"- {row.get('case_id')} ({row.get('category')}), relation {index} "
                f"{relation.get('thing')}, score={relation.get('score')}"
            )
    else:
        lines.append("- None")
    lines.extend(["", f"## FALSE REJECTS ({len(false_rejects)})", "", f"Count: {len(false_rejects)}", ""])
    if false_rejects:
        for row, relation, index in false_rejects:
            lines.append(
                f"- {row.get('case_id')} ({row.get('category')}), relation {index} "
                f"{relation.get('thing')}, score={relation.get('score')}"
            )
    else:
        lines.append("- None")
    lines.append("")

    all_metric = _metrics(rows)
    lines.extend(
        [
            "## UNCERTAIN AND UNAVAILABLE",
            "",
            f"- Uncertain: {all_metric['uncertain']} "
            f"(accept-labelled {all_metric['uncertain_accept']}; reject-labelled {all_metric['uncertain_reject']})",
            f"- Unavailable: {all_metric['unavailable']} "
            f"(accept-labelled {all_metric['unavailable_accept']}; reject-labelled {all_metric['unavailable_reject']})",
            "",
        ]
    )

    invention_rows = [row for row in rows if row.get("category") == "invention_unreported"]
    lines.extend(
        [
            "## Invention-unreported cases",
            "",
            "Unreported inventions are not detected by this verifier; these rows only confirm the required relation.",
            "",
        ]
    )
    if invention_rows:
        for row in invention_rows:
            lines.append(f"- {row.get('case_id')}: {row.get('outcome')}")
    else:
        lines.append("- None")
    lines.append("")

    required_rows = [row for row in rows if row.get("category") != "invention_unreported"]
    required_metric = _metrics(required_rows)
    false_accept_gate = required_metric["false_accepts"] == 0
    false_reject_rate = (
        required_metric["false_rejects"] / required_metric["label_accept"] if required_metric["label_accept"] else 0
    )
    strict_rate = (
        required_metric["strict_failures"] / required_metric["label_accept"] if required_metric["label_accept"] else 0
    )
    lines.extend(
        [
            "## GATE",
            "",
            "The gate is evaluated at the thresholds recorded in the rows.",
            "",
            f"- zero observed false accepts on required relations: {'PASS' if false_accept_gate else 'FAIL'}",
            f"- false rejects at most 5% of accept-labelled relations: "
            f"{'PASS' if false_reject_rate <= 0.05 else 'FAIL'} "
            f"(plain false-reject rate: {false_reject_rate:.1%}; strict accept-label failure rate: {strict_rate:.1%})",
            "",
        ]
    )
    lines.extend(_threshold_sweep(rows))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact("\n".join(lines)), encoding="utf-8")


def _error(message: str) -> int:
    print(_redact(f"verifier calibration: {message}"), file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--validate-corpus", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--lock", action="store_true")
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
            _report(args.rows, args.out)
            print(f"report: {_redact(str(args.out))}")
            return 0

        corpus = _validated_corpus()
        if args.validate_corpus:
            _print_validation_summary(corpus)
            if args.lock:
                _write_json(_lock_path(), _lock_document(corpus))
                print(f"lock: {_redact(str(_lock_path()))}")
            return 0

        if not args.run:
            _print_dry_run(corpus, args.samples)
            return 0
        if args.lock:
            return _error("--lock is only valid with --validate-corpus")
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        if args.max_calls < 1:
            return _error("--max-calls must be at least 1")
        calls_planned = len(corpus["cases"]) * args.samples
        if calls_planned > args.max_calls:
            return _error(f"planned requests {calls_planned} exceed --max-calls {args.max_calls}")
        ceiling = _estimate_tokens(corpus["cases"], args.samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not _lock_matches(corpus):
            return _error("run mode requires a matching corpus lock")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        document = _run(corpus, args.samples, args.max_calls, args.out)
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except CorpusValidationError:
        return 1 if args.validate_corpus else 2
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

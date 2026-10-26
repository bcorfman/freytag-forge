"""Offline prompt builder and confirmed direct narrator defect probe."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import math
import os
import random
import statistics
import sys
from pathlib import Path
from typing import Any

from scripts.ringer.environment_narration.smoke_direct import (
    VARIANTS,
    _call,
    _redact,
    _stop_reason,
    _write_json,
)

REPO_DIR = Path(__file__).resolve().parents[3]
DEFAULT_ROWS_SOURCE = REPO_DIR / "bench/results/environment-narration/shadow-sample/full/rows/rows.json"
DEFAULT_PROBE_DIR = Path(__file__).with_name("defect_probe")
EXPECTED_SOURCE_SHA256 = "aaca5776240d1a347bc21c7c61c609ffa7be3f3ffc8f757b591ff3702e4a447b"
VARIANT_LABEL = "llama-3.3-70b-default-temp"
FIXED_SEED = 1729
COMPLETION_TOKENS = 150
INPUT_PRICE = 0.293
OUTPUT_PRICE = 2.253
UNUSABLE_STOP_AFTER = 3

ARMS: tuple[dict[str, Any], ...] = (
    {"id": "A0", "defect": "A", "prompt_id": "PA", "edits": ()},
    {
        "id": "A1",
        "defect": "A",
        "prompt_id": "PA",
        "edits": ({"op": "delete", "prefix": "- Dr. Michelle McGehee may say this aloud:"},),
    },
    {
        "id": "A2",
        "defect": "A",
        "prompt_id": "PA",
        "edits": (
            {"op": "delete", "prefix": "- Dr. Michelle McGehee may say this aloud:"},
            {"op": "delete", "prefix": "- Show these in your reply:"},
        ),
    },
    {
        "id": "A3",
        "defect": "A",
        "prompt_id": "PA",
        "edits": (
            {"op": "delete", "prefix": "- Dr. Michelle McGehee may say this aloud:"},
            {"op": "add", "line": "- Nothing else is under the drawer. Searching under the drawer finds nothing more."},
        ),
    },
    {"id": "B0", "defect": "B", "prompt_id": "PB", "edits": ()},
    {
        "id": "B1",
        "defect": "B",
        "prompt_id": "PB",
        "edits": ({"op": "delete", "prefix": "- What presses on Kristin now:"},),
    },
    {
        "id": "B2",
        "defect": "B",
        "prompt_id": "PB",
        "edits": (
            {
                "op": "add",
                "line": "- Nothing is left in or under the passenger seat. Searching the passenger seat finds nothing.",
            },
        ),
    },
    {
        "id": "B3",
        "defect": "B",
        "prompt_id": "PB",
        "edits": (
            {"op": "delete", "prefix": "- What presses on Kristin now:"},
            {
                "op": "add",
                "line": "- Nothing is left in or under the passenger seat. Searching the passenger seat finds nothing.",
            },
        ),
    },
)


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _error(message: str) -> int:
    print(f"environment narration defect probe: {_redact(message)}", file=sys.stderr)
    return 2


def _prompt_paths(probe_dir: Path) -> tuple[Path, Path]:
    return probe_dir / "prompts.json", probe_dir / "prompts.lock.json"


def _line_content(line: str) -> str:
    if line.endswith("\r\n"):
        return line[:-2]
    if line.endswith(("\n", "\r")):
        return line[:-1]
    return line


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith(("\n", "\r")):
        return line[-1]
    return ""


def _apply_edit(text: str, edit: dict[str, str], arm_id: str) -> str:
    lines = text.splitlines(keepends=True)
    operation = edit.get("op")
    if operation == "delete":
        prefix = edit.get("prefix", "")
        matches = [index for index, line in enumerate(lines) if _line_content(line).startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"{arm_id}: delete prefix {prefix!r} matched {len(matches)} lines; expected exactly one")
        del lines[matches[0]]
        return "".join(lines)
    if operation == "add":
        matches = [index for index, line in enumerate(lines) if _line_content(line) == "CONSTRAINTS:"]
        if len(matches) != 1:
            raise ValueError(f"{arm_id}: add requires exactly one CONSTRAINTS: line; found {len(matches)}")
        index = matches[0]
        ending = _line_ending(lines[index]) or "\n"
        if not _line_ending(lines[index]):
            lines[index] = f"{lines[index]}{ending}"
        lines.insert(index + 1, f"{edit.get('line', '')}{ending}")
        return "".join(lines)
    raise ValueError(f"{arm_id}: unknown edit operation {operation!r}")


def _arm_user(control: str, arm: dict[str, Any]) -> str:
    result = control
    for edit in arm["edits"]:
        result = _apply_edit(result, edit, arm["id"])
    return result


def _unified_diff(prompt_id: str, arm_id: str, control: str, user: str) -> str:
    lines = difflib.unified_diff(
        control.splitlines(keepends=True),
        user.splitlines(keepends=True),
        fromfile=f"{prompt_id} control",
        tofile=f"{arm_id} user",
        lineterm="\n",
    )
    return "".join(lines)


def _load_source(path: Path, expected_sha256: str) -> tuple[list[dict[str, Any]], str]:
    data = path.read_bytes()
    actual = _sha256(data)
    if actual != expected_sha256:
        raise ValueError(f"source sha256 mismatch for {path}: expected {expected_sha256}, got {actual}")
    document = json.loads(data.decode("utf-8"))
    if not isinstance(document, list) or not document or not isinstance(document[0], dict):
        raise ValueError("rows source must be a non-empty list with replicate 0 first")
    return document, actual


def _extract_prompt(replicate: dict[str, Any], turn_index: int, input_text: str, prompt_id: str) -> dict[str, Any]:
    turns = replicate.get("turns")
    if not isinstance(turns, list):
        raise ValueError(f"{prompt_id}: replicate 0 has no turns list")
    matches = [
        turn
        for turn in turns
        if isinstance(turn, dict) and turn.get("turn_index") == turn_index and turn.get("input") == input_text
    ]
    if len(matches) != 1:
        raise ValueError(f"{prompt_id}: expected exactly one turn_index {turn_index} with input {input_text!r}")
    prompts = matches[0].get("prompts")
    if not isinstance(prompts, list):
        raise ValueError(f"{prompt_id}: selected turn has no prompts list")
    selected = next(
        (
            prompt
            for prompt in prompts
            if isinstance(prompt, dict)
            and isinstance(prompt.get("system"), str)
            and prompt["system"].startswith("You are the narrator")
        ),
        None,
    )
    if not isinstance(selected, dict) or not isinstance(selected.get("user"), str):
        raise ValueError(f"{prompt_id}: selected turn has no narrator prompt with user text")
    return {"system": selected["system"], "user": selected["user"], "turn_index": turn_index, "input": input_text}


def build_prompts(
    rows_source: Path, expected_sha256: str = EXPECTED_SOURCE_SHA256, probe_dir: Path = DEFAULT_PROBE_DIR
) -> dict[str, Any]:
    rows, actual_sha256 = _load_source(rows_source, expected_sha256)
    extracted = {
        "PA": _extract_prompt(rows[0], 3, "feel under the drawer", "PA"),
        "PB": _extract_prompt(rows[0], 8, "inspect the passenger seat", "PB"),
    }
    controls = {"PA": extracted["PA"]["user"], "PB": extracted["PB"]["user"]}
    arm_documents: list[dict[str, Any]] = []
    for arm in ARMS:
        control = controls[arm["prompt_id"]]
        user = _arm_user(control, arm)
        arm_documents.append(
            {
                "id": arm["id"],
                "defect": arm["defect"],
                "prompt_id": arm["prompt_id"],
                "edits": list(arm["edits"]),
                "system": extracted[arm["prompt_id"]]["system"],
                "user": user,
                "diff": _unified_diff(arm["prompt_id"], arm["id"], control, user),
            }
        )
    document = {"arms": arm_documents, "prompts": extracted, "source_sha256": actual_sha256}
    prompts_path, lock_path = _prompt_paths(probe_dir)
    _write_json(prompts_path, document)
    _write_json(lock_path, {"sha256": _sha256(prompts_path.read_bytes()), "count": len(arm_documents)})
    return document


def _load_frozen(probe_dir: Path) -> dict[str, Any]:
    prompts_path, lock_path = _prompt_paths(probe_dir)
    try:
        data = prompts_path.read_bytes()
        document = json.loads(data.decode("utf-8"))
        lock = json.loads(lock_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"prompt lock or prompts file is missing or invalid in {probe_dir}") from error
    arms = document.get("arms") if isinstance(document, dict) else None
    if not isinstance(arms, list):
        raise ValueError("prompts.json has no arms list")
    expected = {"sha256": _sha256(data), "count": len(arms)}
    if lock != expected:
        raise ValueError("prompt lock mismatch")
    return document


def _arm_documents(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    arms = document.get("arms")
    if not isinstance(arms, list):
        raise ValueError("prompts.json has no arms list")
    result = {arm.get("id"): arm for arm in arms if isinstance(arm, dict) and isinstance(arm.get("id"), str)}
    if len(result) != len(ARMS):
        raise ValueError("prompts.json does not contain the eight expected arms")
    return result


def _selected_arm_ids(stage: int, requested: tuple[str, ...]) -> tuple[str, ...]:
    known = {arm["id"]: arm for arm in ARMS}
    if stage == 1:
        if requested:
            raise ValueError("--arms is only valid for stage 2")
        return tuple(arm["id"] for arm in ARMS)
    if not requested:
        raise ValueError("stage 2 requires --arms with one or more non-control candidates")
    candidates: list[str] = []
    for arm_id in requested:
        arm = known.get(arm_id)
        if arm is None:
            raise ValueError(f"unknown arm {arm_id}")
        if arm_id.endswith("0"):
            raise ValueError("stage 2 --arms cannot contain a control arm")
        if arm_id not in candidates:
            candidates.append(arm_id)
    selected: list[str] = []
    for candidate in candidates:
        defect = known[candidate]["defect"]
        control = f"{defect}0"
        if control not in selected:
            selected.append(control)
        selected.append(candidate)
    return tuple(selected)


def planned_calls(document: dict[str, Any], stage: int, requested: tuple[str, ...] = ()) -> list[dict[str, Any]]:
    if stage not in (1, 2):
        raise ValueError("stage must be 1 or 2")
    arms = _arm_documents(document)
    selected = _selected_arm_ids(stage, requested)
    samples = range(10) if stage == 1 else range(10, 25)
    slots = [(arm_id, sample) for arm_id in selected for sample in samples]
    random.Random(FIXED_SEED).shuffle(slots)
    calls: list[dict[str, Any]] = []
    profile = next(profile for profile in VARIANTS if profile["label"] == VARIANT_LABEL)
    for call_index, (arm_id, sample) in enumerate(slots, start=1):
        arm = arms[arm_id]
        calls.append(
            {
                "call_index": call_index,
                "variant": VARIANT_LABEL,
                "model": profile["model_id"],
                "start": arm["prompt_id"],
                "context": arm_id,
                "sample": sample,
                "system": arm["system"],
                "user": arm["user"],
            }
        )
    return calls


def _estimated_call_usd(call: dict[str, Any]) -> float:
    prompt_tokens = (len(call["system"]) + len(call["user"])) / 4
    return (prompt_tokens * INPUT_PRICE + COMPLETION_TOKENS * OUTPUT_PRICE) / 1_000_000


def _print_plan(document: dict[str, Any], stage: int, requested: tuple[str, ...]) -> None:
    calls = planned_calls(document, stage, requested)
    counts: dict[str, int] = {}
    for call in calls:
        counts[call["context"]] = counts.get(call["context"], 0) + 1
    print(f"calls per arm: {', '.join(f'{arm}={count}' for arm, count in counts.items())}")
    print(f"total calls: {len(calls)} calls")
    print(f"estimated USD: ${sum(_estimated_call_usd(call) for call in calls):.6f}")
    for arm_id in counts:
        print(f"\n{arm_id} diff:")
        arm = _arm_documents(document)[arm_id]
        print(arm["diff"], end="" if arm["diff"].endswith("\n") else "\n")


def _credentials() -> tuple[str, str]:
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "").strip()
    token = os.environ.get("CLOUDFLARE_AI_TOKEN", "").strip() or os.environ.get("CF_API_TOKEN", "").strip()
    return account, token


def _run(
    document: dict[str, Any],
    stage: int,
    requested: tuple[str, ...],
    max_usd: float,
    account: str,
    token: str,
    out: Path,
) -> dict[str, Any]:
    result: dict[str, Any] = {"schema": 1, "stage": stage, "rows": [], "stop_reason": None}
    consecutive_unusable = 0
    spent = 0.0
    for call in planned_calls(document, stage, requested):
        row = _call(account, token, call)
        result["rows"].append(row)
        _write_json(out, result)
        stop_reason = _stop_reason(row)
        if stop_reason is not None:
            result["stop_reason"] = stop_reason
            _write_json(out, result)
            break
        if not row.get("usable", False):
            consecutive_unusable += 1
            if consecutive_unusable >= UNUSABLE_STOP_AFTER:
                result["stop_reason"] = "UNUSABLE"
                _write_json(out, result)
                break
        else:
            consecutive_unusable = 0
        actual_cost = row.get("actual_cost_usd")
        if isinstance(actual_cost, (int, float)) and not isinstance(actual_cost, bool):
            spent += float(actual_cost)
        if spent > max_usd:
            result["stop_reason"] = "BUDGET"
            _write_json(out, result)
            break
    return result


def _load_rows_document(path: Path) -> list[dict[str, Any]]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid rows file {path}") from error
    rows = document.get("rows") if isinstance(document, dict) else document
    if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
        raise ValueError(f"rows file {path} has no rows list")
    return rows


def _sheet(rows_paths: list[Path], out: Path, key_path: Path) -> None:
    entries: list[tuple[Path, dict[str, Any]]] = []
    for path in rows_paths:
        entries.extend((path, row) for row in _load_rows_document(path))
    random.Random(FIXED_SEED).shuffle(entries)
    key: dict[str, Any] = {}
    sections: list[str] = ["# Blind narration sheet", ""]
    for number, (source, row) in enumerate(entries, start=1):
        ident = f"r{number:02d}"
        arm = str(row.get("context", ""))
        reply = row.get("narration") or row.get("final_text") or "(no text)"
        if not isinstance(reply, str):
            reply = str(reply)
        key[ident] = {
            "arm": arm,
            "sample": row.get("sample"),
            "call_index": row.get("call_index"),
            "source": str(source),
        }
        sections.extend([f"## {ident} — {arm[:1]}", "", reply, ""])
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact("\n".join(sections)), encoding="utf-8")
    _write_json(key_path, key)
    print(f"key sha256: {_sha256(key_path.read_bytes())}")


def _wilson_upper(fails: int, n: int) -> float:
    if n == 0:
        return 0.0
    z = 1.959963984540054
    proportion = fails / n
    denominator = 1 + z * z / n
    center = proportion + z * z / (2 * n)
    spread = z * math.sqrt(proportion * (1 - proportion) / n + z * z / (4 * n * n))
    return (center + spread) / denominator


def _row_valid(row: dict[str, Any], repaired: bool) -> bool | None:
    names = ("repaired_json_valid", "repair_usable") if repaired else ("strict_json_valid", "usable")
    for name in names:
        if isinstance(row.get(name), bool):
            return row[name]
    return None


def _report(rows_paths: list[Path], key_path: Path, labels_path: Path, out: Path) -> None:
    try:
        key = json.loads(key_path.read_text(encoding="utf-8"))
        labels = json.loads(labels_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("key or labels file is missing or invalid") from error
    if not isinstance(key, dict) or not isinstance(labels, dict):
        raise ValueError("key and labels must be JSON objects")
    missing = [ident for ident in key if ident not in labels]
    extra = [ident for ident in labels if ident not in key]
    if missing:
        raise ValueError(f"labels missing id {missing[0]}")
    if extra:
        raise ValueError(f"label id {extra[0]} is not in the key")
    row_by_source_call: dict[tuple[str, Any], dict[str, Any]] = {}
    for path in rows_paths:
        for row in _load_rows_document(path):
            row_by_source_call[(str(path), row.get("call_index"))] = row
    groups: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = {}
    for ident, item in key.items():
        if not isinstance(item, dict):
            raise ValueError(f"key entry {ident} is invalid")
        label = labels[ident]
        if (
            not isinstance(label, dict)
            or label.get("verdict") not in {"pass", "fail", "unusable"}
            or not isinstance(label.get("note"), str)
        ):
            raise ValueError(f"label {ident} is invalid")
        row = row_by_source_call.get((str(item.get("source")), item.get("call_index")))
        if row is None:
            raise ValueError(f"key entry {ident} has no matching row")
        groups.setdefault(str(item.get("arm")), []).append((row, label))
    lines = ["# Defect probe report", ""]
    metrics: dict[str, dict[str, Any]] = {}
    for arm_id in [arm["id"] for arm in ARMS]:
        records = groups.get(arm_id, [])
        fails = sum(label["verdict"] == "fail" for _row, label in records)
        unusable = sum(label["verdict"] == "unusable" for _row, label in records)
        passes = sum(label["verdict"] == "pass" for _row, label in records)
        latencies = [row["latency_ms"] for row, _label in records if isinstance(row.get("latency_ms"), (int, float))]
        costs = [
            row["actual_cost_usd"] for row, _label in records if isinstance(row.get("actual_cost_usd"), (int, float))
        ]
        strict = [_row_valid(row, False) for row, _label in records]
        repaired = [_row_valid(row, True) for row, _label in records]
        metrics[arm_id] = {"n": len(records), "fails": fails, "passes": passes, "unusable": unusable}
        line = (
            f"{arm_id}: n={len(records)}, fails={fails}, passes={passes}, "
            f"unusable={unusable}, "
            f"Wilson 95% upper failure={_wilson_upper(fails, len(records)):.3f}"
        )
        if any(value is not None for value in strict):
            strict_total = len([value for value in strict if value is not None])
            line += f", strict JSON valid={sum(value is True for value in strict)}/{strict_total}"
        if any(value is not None for value in repaired):
            repaired_total = len([value for value in repaired if value is not None])
            line += f", repaired JSON valid={sum(value is True for value in repaired)}/{repaired_total}"
        if latencies:
            line += f", latency median={statistics.median(latencies):.3f} ms, max={max(latencies):.3f} ms"
        if costs:
            line += f", actual cost=${sum(costs):.6f}"
        lines.append(line)
    for defect in ("A", "B"):
        control_id = f"{defect}0"
        control = metrics[control_id]
        n = control["n"]
        threshold = 0.3 if n == 10 else 0.25 if n == 25 else None
        reproduced = threshold is not None and n > 0 and control["fails"] / n >= threshold
        if n == 10:
            if not reproduced:
                lines.append(f"{defect}: not reproduced")
            else:
                candidate = next(
                    (
                        arm["id"]
                        for arm in ARMS
                        if arm["defect"] == defect
                        and arm["id"] != control_id
                        and metrics[arm["id"]]["n"] == 10
                        and metrics[arm["id"]]["fails"] <= 1
                    ),
                    None,
                )
                lines.append(f"{defect}: candidate {candidate}" if candidate else f"{defect}: no advancing candidate")
        elif n == 25:
            for arm in ARMS:
                if arm["defect"] == defect and metrics[arm["id"]]["n"] == 25:
                    passed = reproduced and metrics[arm["id"]]["fails"] <= 1
                    lines.append(f"{arm['id']} stage 2 gate: {'PASS' if passed else 'FAIL'}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact("\n".join(lines) + "\n"), encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-prompts", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--sheet", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--rows-source", type=Path, default=DEFAULT_ROWS_SOURCE)
    parser.add_argument("--source-sha256", default=EXPECTED_SOURCE_SHA256)
    parser.add_argument("--probe-dir", type=Path, default=DEFAULT_PROBE_DIR)
    parser.add_argument("--stage", type=int, choices=(1, 2))
    parser.add_argument("--arms")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-usd", type=float)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--rows", type=Path, action="append")
    parser.add_argument("--key", type=Path)
    parser.add_argument("--labels", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.build_prompts:
            build_prompts(args.rows_source, args.source_sha256, args.probe_dir)
            print(f"built prompts at {_redact(str(args.probe_dir))}")
            return 0
        if args.sheet:
            if not args.rows or args.out is None or args.key is None:
                return _error("--sheet requires --rows, --out, and --key")
            _sheet(args.rows, args.out, args.key)
            return 0
        if args.report:
            if not args.rows or args.key is None or args.labels is None or args.out is None:
                return _error("--report requires --rows, --key, --labels, and --out")
            _report(args.rows, args.key, args.labels, args.out)
            return 0
        if args.stage is None:
            return _error("--dry-run and --run require --stage 1 or 2")
        requested = tuple(part.strip() for part in args.arms.split(",") if part.strip()) if args.arms else ()
        document = _load_frozen(args.probe_dir)
        calls = planned_calls(document, args.stage, requested)
        if args.dry_run:
            _print_plan(document, args.stage, requested)
            return 0
        if not args.confirm:
            return _error("--run requires --confirm")
        if args.max_usd is None:
            return _error("--run requires --max-usd")
        if args.max_calls is None:
            return _error("--run requires --max-calls")
        if args.max_calls < len(calls):
            return _error(f"planned calls {len(calls)} exceed --max-calls {args.max_calls}")
        estimate = sum(_estimated_call_usd(call) for call in calls)
        if estimate > args.max_usd:
            return _error(f"estimated USD ${estimate:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if args.out is None:
            return _error("--run requires --out")
        account, token = _credentials()
        if not account or not token:
            return _error("--run requires CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_AI_TOKEN or CF_API_TOKEN")
        result = _run(document, args.stage, requested, args.max_usd, account, token, args.out)
        print(f"{len(result['rows'])} rows written to {_redact(str(args.out))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

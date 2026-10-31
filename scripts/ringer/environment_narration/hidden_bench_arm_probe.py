"""Build and run the T9h hidden-bench diagnostic arm probe."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from itertools import zip_longest
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
STATES = ("opening", "inspect", "find")
ARMS = ("base", "B", "C")
CAPTURE_ARMS = ("base", "B")
SAMPLES = 10
PLANNED_CALLS = 30
DEFAULT_MAX_CALLS = PLANNED_CALLS
DEFAULT_MAX_USD = 0.03
OLD_DETAILS = "**Details:** ordinary park bench; damaged grounds; service path; checkpoints; emergency patrols"
NEW_DETAILS = (
    "**Details:** The park bench is fixed in place.; damaged grounds; service path; checkpoints; emergency patrols"
)
NEW_DETAILS_SENTENCE = "The park bench is fixed in place."
REMOVED_LINE = "- Brandon Corfman may say this aloud: I won't tell you that. Keep your voice down; patrols are nearby."
DELIVERY_TEXT = (
    "Kristin reaches beneath the park bench. She retrieves a transit token, a handwritten number sequence and "
    "Michelle's photograph. She keeps all three with her."
)
CLUE_NAMES = ("Transit token", "handwritten number sequence", "Michelle's photograph")
SHUFFLE_SEED = 731904
LABEL_RUBRICS = {
    "attempted_lift_of_bench": "Kristin tries or proposes to lift or move the bench or seat.",
    "completed_lift_of_bench": "The lift or move happened.",
    "final_bench_place_changed": "The bench ends up somewhere else.",
    "route_or_face_or_identity_revealed": (
        "The transport route, photograph face or contents, or follower identity is revealed."
    ),
    "premature_brandon_naming": "Brandon is named or present before the player earned him.",
    "extra_object_invented": "An object beyond the three declared clues is invented.",
    "meta_narration": "The narrator talks about the story, game, or what will be revealed.",
    "unsolicited_brandon_dialogue": "Brandon speaks, warns, or recalls speech without being addressed.",
    "conveys_three_objects_and_keeping": (
        "Narrator and appended engine text together show all three objects and keeping them."
    ),
}
LABEL_NAMES = tuple(LABEL_RUBRICS)
_MISSING = object()


def _prose_module() -> Any:
    path = Path(__file__).with_name("hidden_bench_prose_probe.py")
    specification = importlib.util.spec_from_file_location("hidden_bench_prose_probe", path)
    if specification is None or specification.loader is None:
        raise RuntimeError("could not load the prose probe")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _write_json(path: Path, document: object) -> None:
    _prose_module()._write_json(path, document)


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _line_ending(line: str) -> str:
    if line.endswith("\r\n"):
        return "\r\n"
    if line.endswith("\n") or line.endswith("\r"):
        return line[-1]
    return ""


def _replace_exact_line(path: Path, old: str, new: str) -> None:
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == old]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {old!r} line in {path}, found {len(matches)}")
    index = matches[0]
    lines[index] = new + _line_ending(lines[index])
    path.write_text("".join(lines), encoding="utf-8")


def _remove_exact_line(text: str, target: str) -> str:
    lines = text.splitlines(keepends=True)
    matches = [index for index, line in enumerate(lines) if line.rstrip("\r\n") == target]
    if len(matches) != 1:
        raise ValueError(f"expected exactly one matching line, found {len(matches)}")
    del lines[matches[0]]
    return "".join(lines)


def _remove_line_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(payload)
    matches = []
    for field in ("system", "user"):
        lines = result[field].splitlines(keepends=True)
        matches.extend((field, index) for index, line in enumerate(lines) if line.rstrip("\r\n") == REMOVED_LINE)
    if len(matches) != 1:
        raise ValueError(f"expected exactly one Brandon line in payload, found {len(matches)}")
    field, index = matches[0]
    lines = result[field].splitlines(keepends=True)
    del lines[index]
    result[field] = "".join(lines)
    result["id"] = "C-" + str(result["state"])
    result["arm"] = "C"
    return result


def _candidate_b(destination: Path) -> Path:
    candidate = destination / "B"
    shutil.copytree(PACKAGE_ROOT, candidate)
    _replace_exact_line(candidate / "plot.md", OLD_DETAILS, NEW_DETAILS)
    return candidate


def _package_files(root: Path) -> dict[Path, Path]:
    return {path.relative_to(root): path for path in root.rglob("*") if path.is_file()}


def _package_difference_errors(base: Path, candidate: Path) -> list[str]:
    base_files = _package_files(base)
    candidate_files = _package_files(candidate)
    errors: list[str] = []
    if set(base_files) != set(candidate_files):
        missing = sorted(set(base_files) - set(candidate_files))
        extra = sorted(set(candidate_files) - set(base_files))
        errors.append(f"package file sets differ; missing={missing}, extra={extra}")
        return errors
    differing_files = []
    for relative in sorted(base_files):
        if base_files[relative].read_bytes() != candidate_files[relative].read_bytes():
            differing_files.append(relative)
    if differing_files != [Path("plot.md")]:
        errors.append(f"arm B differs outside exactly plot.md: {differing_files}")
        return errors
    base_lines = base_files[Path("plot.md")].read_text(encoding="utf-8").splitlines(keepends=True)
    candidate_lines = candidate_files[Path("plot.md")].read_text(encoding="utf-8").splitlines(keepends=True)
    differences = [
        (index, left, right)
        for index, (left, right) in enumerate(zip_longest(base_lines, candidate_lines, fillvalue=_MISSING))
        if left != right
    ]
    if len(differences) != 1:
        errors.append(f"plot.md has {len(differences)} changed lines, expected one")
    elif differences[0][1].rstrip("\r\n") != OLD_DETAILS or differences[0][2].rstrip("\r\n") != NEW_DETAILS:
        errors.append("plot.md changed line is not the registered Details replacement")
    return errors


def _rename_capture(payloads: list[dict[str, Any]], arm: str) -> list[dict[str, Any]]:
    renamed = []
    for payload in payloads:
        item = copy.deepcopy(payload)
        state = "inspect" if item["state"] == "prefind" else item["state"]
        item["state"] = state
        item["id"] = f"{arm}-{state}"
        item["arm"] = arm
        renamed.append(item)
    return renamed


def _capture_package(package_root: Path, arm: str) -> list[dict[str, Any]]:
    prose = _prose_module()
    return _rename_capture(prose._capture_package(package_root, arm), arm)


def _sort_payloads(payloads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(payloads, key=lambda item: (STATES.index(item["state"]), ARMS.index(item["arm"])))


def capture_payloads() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="t9h-hidden-arm-") as temporary:
        candidate = _candidate_b(Path(temporary))
        base_payloads = _capture_package(PACKAGE_ROOT, "base")
        candidate_payloads = _capture_package(candidate, "B")
    payloads = [*base_payloads, *candidate_payloads]
    base_by_state = {item["state"]: item for item in base_payloads}
    payloads.extend(_remove_line_from_payload(base_by_state[state]) for state in ("inspect", "find"))
    return {"schema": 1, "stage": "t9h-hidden-arm", "payloads": _sort_payloads(payloads)}


def _payload_material(payload: dict[str, Any]) -> str:
    return f"{payload.get('system', '')}\n{payload.get('user', '')}"


def _segment_texts(payload: dict[str, Any]) -> list[str]:
    segments = payload.get("composed_segments", [])
    if not isinstance(segments, list):
        return []
    return [str(segment.get("text", "")) for segment in segments if isinstance(segment, dict)]


def _payload_signature(payload: dict[str, Any]) -> str:
    return json.dumps(
        {field: payload.get(field) for field in ("system", "user", "composed_segments")},
        sort_keys=True,
        ensure_ascii=False,
    )


def _payloads_by_id(document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    payloads = document.get("payloads")
    if not isinstance(payloads, list):
        raise ValueError("capture document has no payloads list")
    result = {}
    for payload in payloads:
        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str):
            raise ValueError("capture document contains an invalid payload")
        if payload["id"] in result:
            raise ValueError(f"duplicate payload id {payload['id']}")
        result[payload["id"]] = payload
    return result


def validate_document(
    document: dict[str, Any], base_package: Path = PACKAGE_ROOT, candidate: Path | None = None
) -> list[str]:
    errors: list[str] = []
    try:
        payloads = _payloads_by_id(document)
    except ValueError as error:
        return [str(error)]
    expected_ids = {
        "base-opening",
        "base-inspect",
        "base-find",
        "B-opening",
        "B-inspect",
        "B-find",
        "C-inspect",
        "C-find",
    }
    if set(payloads) != expected_ids:
        errors.append(f"payload ids differ from expected set: {sorted(payloads)}")
        return errors
    if candidate is not None:
        errors.extend(_package_difference_errors(base_package, candidate))
    for arm in ("base", "B"):
        for state in ("opening", "inspect"):
            material = _payload_material(payloads[f"{arm}-{state}"]).casefold()
            for clue in CLUE_NAMES:
                if clue.casefold() in material:
                    errors.append(f"{arm}-{state} contains hidden clue name {clue!r}")
    for arm in ARMS:
        payload = payloads[f"{arm}-find"]
        material = _payload_material(payload)
        if DELIVERY_TEXT not in material:
            errors.append(f"{arm}-find request does not contain the delivery sentence")
        if DELIVERY_TEXT not in _segment_texts(payload):
            errors.append(f"{arm}-find composed segments do not contain the delivery sentence")
    base_find = payloads["base-find"]
    candidate_find = payloads["B-find"]
    if _payload_signature(base_find) == _payload_signature(candidate_find):
        errors.append("B-find payload is identical to base-find")
    if NEW_DETAILS_SENTENCE not in _payload_material(candidate_find) or NEW_DETAILS_SENTENCE in _payload_material(
        base_find
    ):
        errors.append("B-find Details sentence presence is incorrect")
    for state in ("inspect", "find"):
        base_payload = payloads[f"base-{state}"]
        candidate_payload = payloads[f"C-{state}"]
        try:
            system_has_line = REMOVED_LINE in base_payload["system"].splitlines()
            user_has_line = REMOVED_LINE in base_payload["user"].splitlines()
            if system_has_line and user_has_line:
                raise ValueError("Brandon line appears in both system and user text")
            if system_has_line:
                expected_system = _remove_exact_line(base_payload["system"], REMOVED_LINE)
                expected_user = base_payload["user"]
            elif user_has_line:
                expected_system = base_payload["system"]
                expected_user = _remove_exact_line(base_payload["user"], REMOVED_LINE)
            else:
                raise ValueError("Brandon line is absent")
        except ValueError as error:
            errors.append(f"base-{state} Brandon-line check failed: {error}")
            continue
        if candidate_payload.get("system") != expected_system or candidate_payload.get("user") != expected_user:
            errors.append(f"C-{state} is not base-{state} with exactly the Brandon line removed")
        if candidate_payload.get("composed_segments") != base_payload.get("composed_segments"):
            errors.append(f"C-{state} changed composed segments")
    return errors


def _capture_and_validate() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="t9h-hidden-arm-validate-") as temporary:
        candidate = _candidate_b(Path(temporary))
        document = capture_payloads()
        errors = validate_document(document, candidate=candidate)
    if errors:
        raise ValueError("; ".join(errors))
    return document


def _planned(document: dict[str, Any]) -> list[dict[str, Any]]:
    payloads = _payloads_by_id(document)
    calls = []
    for arm in ARMS:
        payload = payloads[f"{arm}-find"]
        for sample in range(1, SAMPLES + 1):
            calls.append({"payload": payload, "sample": sample})
    return calls


def _token_estimate(document: dict[str, Any]) -> float:
    prose = _prose_module()
    payloads = _payloads_by_id(document)
    find_payloads = [payloads[f"{arm}-find"] for arm in ARMS]
    return prose._token_estimate({"payloads": find_payloads})


def _usd_ceiling(document: dict[str, Any]) -> float:
    prose = _prose_module()
    payloads = _payloads_by_id(document)
    find_payloads = [payloads[f"{arm}-find"] for arm in ARMS]
    return prose._usd_ceiling({"payloads": find_payloads})


def run_rows(document: dict[str, Any], *, max_calls: int, max_usd: float, out: Path) -> dict[str, Any]:
    if out.exists():
        raise ValueError(f"output file already exists: {out}")
    if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
        raise ValueError("run mode requires CLOUDFLARE_WORKER_URL")
    if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
        raise ValueError("run mode requires CLOUDFLARE_WORKER_TOKEN")
    calls = _planned(document)
    if len(calls) > max_calls:
        raise ValueError(f"planned calls {len(calls)} exceed --max-calls {max_calls}")
    ceiling = _usd_ceiling(document)
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.state import RuntimeState
    from storygame.story_package.loader import load_story_package

    package = load_story_package(PACKAGE_ROOT)
    rows_document: dict[str, Any] = {
        "schema": 1,
        "stage": "t9h-hidden-arm",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": "incomplete",
    }
    _write_json(out, rows_document)
    prose = _prose_module()
    for index, call in enumerate(calls[:max_calls], start=1):
        payload = call["payload"]
        provider = CloudflareTurnProvider(
            worker_url=os.environ["CLOUDFLARE_WORKER_URL"].strip(),
            token=os.environ["CLOUDFLARE_WORKER_TOKEN"].strip(),
            state=RuntimeState.bootstrap(package),
        )
        request = {
            "system": payload["system"],
            "user": payload["user"],
            "max_tokens": 1024,
            "response_format": {"type": "json_object"},
        }
        try:
            response = provider._request(request)
        except Exception as error:
            rows_document["stop_reason"] = prose._stop_reason(error)
            _write_json(out, rows_document)
            return rows_document
        response_text = (
            response if isinstance(response, str) else json.dumps(response, ensure_ascii=False, sort_keys=True)
        )
        rows_document["rows"].append(
            {
                "call_index": index,
                "payload_id": payload["id"],
                "arm": payload["arm"],
                "state": payload["state"],
                "sample": call["sample"],
                "response_text": response_text,
                "model_segment_count": payload["model_segment_count"],
                "composed_segments": copy.deepcopy(payload["composed_segments"]),
            }
        )
        _write_json(out, rows_document)
    if len(rows_document["rows"]) == len(calls):
        rows_document["stop_reason"] = None
    else:
        rows_document["stop_reason"] = "max_calls"
    _write_json(out, rows_document)
    return rows_document


def write_label_freeze(labels_path: Path) -> Path:
    return _prose_module().write_label_freeze(labels_path)


def _engine_segments(row: dict[str, Any]) -> list[dict[str, str]]:
    prose = _prose_module()
    try:
        from storygame.story_package.loader import load_story_package

        package = load_story_package(PACKAGE_ROOT)
        segments, composable = prose._inferred_delivery(package, str(row.get("state")), str(row["response_text"]))
        if composable:
            return segments
    except (TypeError, ValueError, json.JSONDecodeError, KeyError):
        pass
    composed = row.get("composed_segments", [])
    if not isinstance(composed, list):
        return []
    typed_segments: list[dict[str, str]] = []
    for segment in composed:
        if not isinstance(segment, dict):
            return []
        kind = segment.get("kind")
        text = segment.get("text")
        if not isinstance(kind, str) or not isinstance(text, str):
            return []
        typed_segments.append({"kind": kind, "text": text})
    model_segment_count = row.get("model_segment_count", 1)
    if (
        not isinstance(model_segment_count, int)
        or isinstance(model_segment_count, bool)
        or model_segment_count < 0
        or model_segment_count > len(typed_segments)
    ):
        return []
    return typed_segments[model_segment_count:]


def sheets(rows_path: Path, output: Path) -> None:
    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    indexed = list(enumerate(rows, start=1))
    import random

    random.Random(SHUFFLE_SEED).shuffle(indexed)
    output.mkdir(parents=True, exist_ok=True)
    sheet_lines = ["# Diagnostic sheet", "", f"Shuffle seed: {SHUFFLE_SEED}", ""]
    key: dict[str, Any] = {}
    labels: dict[str, Any] = {}
    for display_index, (row_index, row) in enumerate(indexed, start=1):
        opaque_id = f"sample-{display_index:03d}"
        key[opaque_id] = {
            "row_index": row_index,
            "payload_id": row.get("payload_id"),
            "state": row.get("state"),
            "arm": row.get("arm"),
            "sample": row.get("sample"),
        }
        labels[opaque_id] = {name: None for name in LABEL_NAMES}
        sheet_lines.extend(
            [
                f"## {opaque_id}",
                "",
                f"State: {row.get('state', '(unknown)')}",
                f"Sample: {row.get('sample', '(unknown)')}",
                "",
                "Narrator:",
                str(row.get("response_text", "(none)")),
                "",
                "Engine (appended by the game):",
            ]
        )
        engine_segments = _engine_segments(row)
        sheet_lines.extend(str(segment.get("text", "")) for segment in engine_segments if isinstance(segment, dict))
        if not engine_segments:
            sheet_lines.append("(none)")
        sheet_lines.append("")
    (output / "blind_sheet.md").write_text("\n".join(sheet_lines), encoding="utf-8")
    _write_json(output / "blind_key.json", key)
    labels_path = output / "labels_template.json"
    _write_json(labels_path, labels)
    write_label_freeze(labels_path)


def assert_blind_key_bijection(rows: list[dict[str, Any]], key: dict[str, Any]) -> None:
    _prose_module().assert_blind_key_bijection(rows, key)


def _join_labels(rows: list[dict[str, Any]], labels_path: Path) -> list[dict[str, Any]]:
    key_path = labels_path.parent / "blind_key.json"
    if not key_path.is_file():
        raise ValueError("blind_key.json is required beside the labels file")
    key = _read_json(key_path)
    labels = _read_json(labels_path)
    if not isinstance(key, dict) or not isinstance(labels, dict):
        raise ValueError("labels and blind key must be JSON objects")
    assert_blind_key_bijection(rows, key)
    joined = []
    by_index = {index: row for index, row in enumerate(rows, start=1)}
    for opaque_id, entry in key.items():
        if not isinstance(entry, dict) or not isinstance(labels.get(opaque_id), dict):
            raise ValueError(f"missing labels for {opaque_id}")
        for name in LABEL_NAMES:
            if not isinstance(labels[opaque_id].get(name), bool):
                raise ValueError(f"label {name} for {opaque_id} is not a bool")
        row = by_index[entry["row_index"]]
        joined.append({"row": row, "labels": labels[opaque_id]})
    return joined


def report(rows_path: Path, labels_path: Path, output: Path) -> str:
    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    prose = _prose_module()
    if prose._sha256(labels_path) != prose._freeze_hash(labels_path):
        raise ValueError("labels sha256 does not match the frozen labels hash")
    joined = _join_labels(rows, labels_path)
    lines = [
        "Diagnostic screen, 10 samples per arm. Counts only; proves no general rate.",
        "",
        "# T9h hidden-bench arm report",
        "",
    ]
    for arm in ARMS:
        arm_rows = [item for item in joined if item["row"].get("arm") == arm and item["row"].get("state") == "find"]
        lines.append(f"## Arm {arm}")
        lines.append("")
        for name in LABEL_NAMES:
            count = sum(item["labels"][name] for item in arm_rows)
            lines.append(f"{name}: {count} true of {len(arm_rows)}")
            lines.append(f"Rubric: {LABEL_RUBRICS[name]}")
        lines.append("")
    rendered = "\n".join(lines)
    if not rendered.endswith("\n"):
        rendered += "\n"
    output.write_text(rendered, encoding="utf-8")
    return rendered


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--sheets", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    return parser


def _error(message: str, code: int = 1) -> int:
    print(f"hidden bench arm probe: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.capture:
            if args.out is None:
                return _error("--capture requires --out", 2)
            document = _capture_and_validate()
            _write_json(args.out, document)
            print(f"{len(document['payloads'])} payloads written to {args.out}")
            return 0
        if args.validate:
            _capture_and_validate()
            print("package arm difference: PASS")
            print("payload structural checks: PASS")
            return 0
        if args.sheets:
            if args.rows is None or args.out is None:
                return _error("--sheets requires --rows and --out", 2)
            sheets(args.rows, args.out)
            return 0
        if args.report:
            if args.rows is None or args.labels is None or args.out is None:
                return _error("--report requires --rows, --labels and --out", 2)
            rendered = report(args.rows, args.labels, args.out)
            print(rendered, end="")
            return 0
        if args.run:
            if not args.confirm:
                return _error("run mode requires --confirm", 2)
            if args.out is None:
                return _error("run mode requires --out", 2)
            if args.out.exists():
                return _error(f"output file already exists: {args.out}")
            if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
                return _error("run mode requires CLOUDFLARE_WORKER_URL")
            if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
                return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
            document = _capture_and_validate()
            calls = _planned(document)
            if len(calls) > args.max_calls:
                return _error(f"planned calls {len(calls)} exceed --max-calls {args.max_calls}")
            ceiling = _usd_ceiling(document)
            if ceiling > args.max_usd:
                return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
            result = run_rows(document, max_calls=args.max_calls, max_usd=args.max_usd, out=args.out)
            print(f"{len(result['rows'])} rows written to {args.out}")
            return 0 if result.get("stop_reason") is None else 1
        if args.dry_run:
            document = _capture_and_validate()
            calls = _planned(document)
            print("planned arms: base, B, C; state: find; samples per arm: 10")
            print(f"planned calls: {len(calls)}")
            print(f"token estimate: {_token_estimate(document):.2f}")
            print(f"USD ceiling: ${_usd_ceiling(document):.6f}")
            if len(calls) > args.max_calls:
                return _error(f"planned calls {len(calls)} exceed --max-calls {args.max_calls}")
            if _usd_ceiling(document) > args.max_usd:
                return _error(f"USD ceiling ${_usd_ceiling(document):.6f} exceeds --max-usd ${args.max_usd:.6f}")
            return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError, RuntimeError) as error:
        return _error(str(error))
    return _error("no mode selected", 2)


if __name__ == "__main__":
    raise SystemExit(main())

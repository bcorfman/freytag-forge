"""Build and run the preregistered T9h drain-details prose screen."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
RECORDED_ROWS_PATH = ROOT / "bench/results/environment-narration/t9h-hidden/smoke/rows/rows.json"
CAPTURE_SCRIPT = ROOT / "scripts/ringer/environment_narration/drain_details_capture.py"
STAGE = "t9h-drain-details-prose"
ARMS = ("control", "candidate")
SAMPLES = 10
DEFAULT_MAX_CALLS = 20
DEFAULT_MAX_USD = 0.03
COST_PER_MILLION_INPUT_TOKENS = 0.39
SHUFFLE_SEED = 880419
RECORDED_INPUT = "inspect the storm drain"
RECORDED_DETAILS_TEXT = "- ordinary park bench\n- damaged grounds\n- service path\n- checkpoints\n- emergency patrols"
CANDIDATE_SUFFIX = "; storm drain opening in the damaged grounds"
CANDIDATE_PHRASE = "storm drain opening in the damaged grounds"
FORBIDDEN_LABELS = (
    "opens_or_enters_drain",
    "invents_ajar_or_cover_state",
    "asserts_definite_contents",
)
LABEL_NAMES = FORBIDDEN_LABELS + (
    "speculative_only",
    "wrong_place",
    "capture_prose_disagree",
)


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _recorded_prompt(path: Path | None = None) -> dict[str, str]:
    path = RECORDED_ROWS_PATH if path is None else path
    document = _read_json(path)
    if not isinstance(document, list) or not document:
        raise ValueError("recorded rows must contain replicate rows")
    turns = document[0].get("turns") if isinstance(document[0], dict) else None
    if not isinstance(turns, list) or len(turns) <= 5:
        raise ValueError("recorded replicate 0 has no turn 5")
    turn = turns[5]
    if not isinstance(turn, dict) or turn.get("input") != RECORDED_INPUT:
        raise ValueError("recorded replicate 0 turn 5 is not the storm-drain inspection")
    prompts = turn.get("prompts")
    if not isinstance(prompts, list):
        raise ValueError("recorded drain turn has no prompts list")
    for prompt in prompts:
        if isinstance(prompt, dict) and str(prompt.get("system", "")).startswith("You are the narrator"):
            system = prompt.get("system")
            user = prompt.get("user")
            if isinstance(system, str) and isinstance(user, str):
                return {"system": system, "user": user}
    raise ValueError("recorded drain turn has no narrator prompt")


def _validate_details_location(user: str) -> None:
    scene_start = user.find("SCENE:")
    things_start = user.find("THINGS:")
    if scene_start < 0 or things_start <= scene_start:
        raise ValueError("recorded prompt has no usable SCENE section")
    scene = user[scene_start:things_start]
    if scene.count(RECORDED_DETAILS_TEXT) != 1:
        raise ValueError("recorded prompt details text must occur exactly once in SCENE")


def _candidate_for(control: dict[str, str]) -> dict[str, str]:
    _validate_details_location(control["user"])
    candidate_user = control["user"].replace(
        RECORDED_DETAILS_TEXT,
        RECORDED_DETAILS_TEXT + CANDIDATE_SUFFIX,
        1,
    )
    return {"system": control["system"], "user": candidate_user}


def _assert_prompt_pair(control: dict[str, str], candidate: dict[str, str], *, source: str) -> None:
    _validate_details_location(control["user"])
    expected = _candidate_for(control)
    if candidate != expected:
        raise ValueError(f"{source} control and candidate differ beyond the Details suffix")


def _assert_offline_prompt_pair(control: dict[str, str], candidate: dict[str, str], *, source: str) -> None:
    _validate_details_location(control["user"])
    if control["system"] != candidate["system"]:
        raise ValueError(f"{source} system prompts differ")
    if candidate["user"].count(CANDIDATE_PHRASE) != 1:
        raise ValueError(f"{source} candidate is missing the one Details phrase")
    rendered_bullet = "\n- " + CANDIDATE_PHRASE
    expected_bullet = control["user"].replace(rendered_bullet, "", 1)
    if expected_bullet == candidate["user"]:
        raise ValueError(f"{source} control and candidate are reversed")
    if candidate["user"].replace(rendered_bullet, "", 1) != control["user"]:
        raise ValueError(f"{source} control and candidate differ beyond the Details phrase")


def _load_capture_module() -> Any:
    specification = importlib.util.spec_from_file_location("drain_details_capture_for_probe", CAPTURE_SCRIPT)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load offline capture helper from {CAPTURE_SCRIPT}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _offline_crosscheck(recorded: dict[str, str], captures: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if captures is None:
        captures = _load_capture_module().capture_arms()
    by_path = {
        path: {
            arm: next(
                (item for item in captures if item.get("path") == path and item.get("arm") == arm),
                None,
            )
            for arm in ARMS
        }
        for path in _load_capture_module().PATHS
    }
    for path, arms in by_path.items():
        control = arms["control"]
        candidate = arms["candidate"]
        if not isinstance(control, dict) or not isinstance(candidate, dict):
            raise ValueError(f"offline capture is missing the {path} arm")
        if control.get("status") != "captured" or candidate.get("status") != "captured":
            raise ValueError(f"offline capture did not reproduce both arms for {path}")
        control_requests = control.get("requests")
        candidate_requests = candidate.get("requests")
        if not isinstance(control_requests, list) or not isinstance(candidate_requests, list):
            raise ValueError(f"offline capture has no requests for {path}")
        if len(control_requests) != len(candidate_requests):
            raise ValueError(f"offline request counts differ for {path}")
        for index, (left, right) in enumerate(zip(control_requests, candidate_requests, strict=True)):
            if not isinstance(left, dict) or not isinstance(right, dict):
                raise ValueError(f"offline request {path}/{index} is malformed")
            _assert_offline_prompt_pair(
                {"system": str(left.get("system", "")), "user": str(left.get("user", ""))},
                {"system": str(right.get("system", "")), "user": str(right.get("user", ""))},
                source=f"offline {path}/{index}",
            )
    initial_control = by_path["initial_inspect"]["control"]["requests"][0]
    recorded_agree = recorded == {
        "system": initial_control["system"],
        "user": initial_control["user"],
    }
    return {
        "arms_differ_only_by_suffix": True,
        "recorded_offline_control_agree": recorded_agree,
        "offline_control_path": "initial_inspect",
    }


def capture_payloads(
    recorded_path: Path | None = None,
    *,
    offline_captures: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    recorded_path = RECORDED_ROWS_PATH if recorded_path is None else recorded_path
    control = _recorded_prompt(recorded_path)
    _validate_details_location(control["user"])
    candidate = _candidate_for(control)
    _assert_prompt_pair(control, candidate, source="recorded prompt")
    offline = _offline_crosscheck(control, offline_captures)
    return {
        "schema": 1,
        "stage": STAGE,
        "samples": SAMPLES,
        "recorded_input": RECORDED_INPUT,
        "recorded_rows": str(recorded_path),
        "details_text": RECORDED_DETAILS_TEXT,
        "candidate_suffix": CANDIDATE_SUFFIX,
        "payloads": [
            {"id": "control", "arm": "control", "system": control["system"], "user": control["user"]},
            {"id": "candidate", "arm": "candidate", "system": candidate["system"], "user": candidate["user"]},
        ],
        "offline_crosscheck": offline,
    }


def _planned(document: dict[str, Any], samples: int | None = None) -> list[dict[str, Any]]:
    count = document.get("samples", SAMPLES) if samples is None else samples
    payloads = document.get("payloads")
    if not isinstance(count, int) or count < 1 or not isinstance(payloads, list):
        raise ValueError("capture document has invalid samples or payloads")
    return [{"payload": payload, "sample": sample} for payload in payloads for sample in range(1, count + 1)]


def _token_estimate(document: dict[str, Any], samples: int | None = None) -> float:
    payloads = document.get("payloads", ())
    count = document.get("samples", SAMPLES) if samples is None else samples
    characters = sum(
        len(str(payload.get("system", ""))) + len(str(payload.get("user", "")))
        for payload in payloads
        if isinstance(payload, dict)
    )
    return characters * count / 4


def _usd_ceiling(document: dict[str, Any], samples: int | None = None) -> float:
    return _token_estimate(document, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _status_code(error: BaseException) -> int | None:
    value = getattr(error, "code", None)
    if isinstance(value, int):
        return value
    value = getattr(error, "status_code", None)
    return value if isinstance(value, int) else None


def _stop_reason(error: BaseException) -> str:
    status = _status_code(error)
    message = str(error).casefold()
    if status == 429 or "quota" in message:
        return "http_429_quota_or_rate_limit"
    if status in {401, 403}:
        return f"auth_{status}"
    if status is not None and 500 <= status <= 599:
        return f"http_{status}"
    return "request_error"


def run_rows(document: dict[str, Any], *, max_calls: int, max_usd: float, out: Path) -> dict[str, Any]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.state import RuntimeState
    from storygame.story_package.loader import load_story_package

    if out.exists():
        raise ValueError(f"rows already exist at {out}; refusing to overwrite")
    calls = _planned(document)
    if len(calls) > max_calls:
        raise ValueError(f"planned calls {len(calls)} exceed --max-calls {max_calls}")
    ceiling = _usd_ceiling(document)
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    worker_url = os.environ.get("CLOUDFLARE_WORKER_URL", "").strip()
    worker_token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip()
    if not worker_url or not worker_token:
        raise ValueError("run mode requires CLOUDFLARE_WORKER_URL and CLOUDFLARE_WORKER_TOKEN")
    package = load_story_package(ROOT / "data/stories/continuity-initiative")
    rows_document: dict[str, Any] = {
        "schema": 1,
        "stage": STAGE,
        "samples": document.get("samples", SAMPLES),
        "calls_planned": len(calls),
        "prompt_metadata": document.get("offline_crosscheck", {}),
        "rows": [],
        "stop_reason": "incomplete",
    }
    _write_json(out, rows_document)
    for index, call in enumerate(calls, start=1):
        payload = call["payload"]
        provider = CloudflareTurnProvider(
            worker_url=worker_url,
            token=worker_token,
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
            rows_document["stop_reason"] = _stop_reason(error)
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
                "sample": call["sample"],
                "response_text": response_text,
            }
        )
        _write_json(out, rows_document)
    rows_document["stop_reason"] = None
    _write_json(out, rows_document)
    return rows_document


def _freeze_path(labels_path: Path) -> Path:
    return labels_path.parent / "labels.freeze.json"


def write_label_freeze(labels_path: Path) -> Path:
    labels = _read_json(labels_path)
    if not isinstance(labels, dict):
        raise ValueError("labels file must be a JSON object")
    for opaque_id, entry in labels.items():
        if not isinstance(entry, dict):
            raise ValueError(f"labels file has an invalid label entry for {opaque_id}")
        if any(name in entry and entry[name] is None for name in LABEL_NAMES):
            raise ValueError(f"labels file has a null label for {opaque_id}")
    freeze = _freeze_path(labels_path)
    digest = _sha256(labels_path)
    if freeze.exists():
        existing = _read_json(freeze)
        if not isinstance(existing, dict) or existing.get("sha256") != digest:
            raise ValueError("labels.freeze.json already exists with a different hash; refusing to overwrite")
        return freeze
    _write_json(freeze, {"sha256": digest})
    return freeze


def _shuffled_rows(rows: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    indexed = list(enumerate(rows, start=1))
    random.Random(SHUFFLE_SEED).shuffle(indexed)
    return indexed


def sheets(rows_path: Path, output: Path) -> None:
    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    output.mkdir(parents=True, exist_ok=True)
    lines = ["# Blind drain prose sheet", "", f"Shuffle seed: {SHUFFLE_SEED}", ""]
    key: dict[str, Any] = {}
    labels: dict[str, Any] = {}
    for display_index, (row_index, row) in enumerate(_shuffled_rows(rows), start=1):
        opaque_id = f"sample-{display_index:03d}"
        key[opaque_id] = {
            "row_index": row_index,
            "payload_id": row.get("payload_id"),
            "arm": row.get("arm"),
            "sample": row.get("sample"),
        }
        labels[opaque_id] = {name: None for name in LABEL_NAMES}
        lines.extend([f"## {opaque_id}", "", "Narration:", str(row.get("response_text", "(none)")), ""])
    (output / "blind_sheet.md").write_text("\n".join(lines), encoding="utf-8")
    _write_json(output / "blind_key.json", key)
    _write_json(output / "labels_template.json", labels)


def assert_blind_key_bijection(rows: list[dict[str, Any]], key: dict[str, Any]) -> None:
    indexes = [entry.get("row_index") for entry in key.values() if isinstance(entry, dict)]
    expected = set(range(1, len(rows) + 1))
    if len(indexes) != len(key) or len(indexes) != len(set(indexes)) or set(indexes) != expected:
        raise AssertionError("blind key row_index values are not a bijection over the rows")


def _freeze_hash(labels_path: Path) -> str:
    freeze = _freeze_path(labels_path)
    if not freeze.is_file():
        raise ValueError("run --freeze-labels first")
    document = _read_json(freeze)
    value = document.get("sha256")
    if not isinstance(value, str):
        raise ValueError("labels.freeze.json has no frozen sha256")
    return value


def _joined_rows(rows: list[dict[str, Any]], labels: dict[str, Any], key: dict[str, Any]) -> list[dict[str, Any]]:
    by_index = {index: row for index, row in enumerate(rows, start=1)}
    joined = []
    for opaque_id, entry in key.items():
        row = by_index.get(entry.get("row_index")) if isinstance(entry, dict) else None
        if row is not None:
            joined.append({"opaque_id": opaque_id, "row": row, "labels": labels[opaque_id]})
    return joined


def report(rows_path: Path, labels_path: Path, output: Path) -> tuple[str, bool]:
    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    actual_hash = _sha256(labels_path)
    if actual_hash != _freeze_hash(labels_path):
        raise ValueError("labels sha256 does not match the frozen labels hash")
    key_path = labels_path.parent / "blind_key.json"
    if not key_path.is_file():
        raise ValueError("blind_key.json is required beside the labels file")
    labels = _read_json(labels_path)
    key = _read_json(key_path)
    if not isinstance(labels, dict) or not isinstance(key, dict):
        raise ValueError("labels and blind key must be JSON objects")
    missing = [
        f"{opaque_id} {name}"
        for opaque_id in key
        for name in LABEL_NAMES
        if not isinstance(labels.get(opaque_id, {}).get(name), bool)
    ]
    if len(key) != len(rows):
        missing.append("key does not cover every row")
    if missing:
        raise ValueError("MISSING LABELS: " + ", ".join(missing))
    joined = _joined_rows(rows, labels, key)
    complete = document.get("stop_reason") is None and len(rows) == document.get("calls_planned")
    agree = document.get("prompt_metadata", {}).get("recorded_offline_control_agree")
    agree_text = "yes" if agree is True else "no" if agree is False else "unknown"
    lines = [
        "# T9h drain-details prose report",
        "",
        f"Rows: {len(rows)}/{document.get('calls_planned', '(unknown)')} | complete: {'yes' if complete else 'no'}",
        f"labels sha256: {actual_hash}",
        f"recorded prompt/offline control agree: {agree_text}",
        "",
    ]
    arm_counts: dict[str, int] = {}
    arm_defects: dict[str, int] = {}
    arm_labels: dict[str, dict[str, int]] = {}
    for arm in ARMS:
        arm_rows = [item for item in joined if item["row"].get("arm") == arm]
        arm_counts[arm] = len(arm_rows)
        arm_defects[arm] = sum(any(item["labels"][name] for name in FORBIDDEN_LABELS) for item in arm_rows)
        arm_labels[arm] = {name: sum(item["labels"][name] for item in arm_rows) for name in LABEL_NAMES}
        lines.append(f"{arm}: {len(arm_rows)} rows")
        for name in LABEL_NAMES:
            count = arm_labels[arm][name]
            rate = count / len(arm_rows) if arm_rows else 0.0
            lines.append(f"  {name}: {count}/{len(arm_rows)} ({rate:.1%})")
    lines.extend(
        [
            "",
            f"control forbidden defect rows: {arm_defects['control']}/{arm_counts['control']}",
            f"candidate forbidden defect rows: {arm_defects['candidate']}/{arm_counts['candidate']}",
        ]
    )
    if not complete or arm_defects["control"] == 0:
        screen = "INCONCLUSIVE"
        reason = "control did not reproduce the defect" if arm_defects["control"] == 0 else "partial run"
        lines.append(f"screen: {screen} — {reason}")
        passed = False
    else:
        passed = arm_defects["candidate"] == 0
        lines.append(f"screen: {'PASS' if passed else 'FAIL'}")
    lines.extend(
        [
            "",
            "One passing screen is not an enforcement guarantee.",
            "The separate confirmation is 15 samples per arm (30 calls) and must be run separately.",
        ]
    )
    rendered = "\n".join(lines) + "\n"
    output.write_text(rendered, encoding="utf-8")
    return rendered, passed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--sheets", action="store_true")
    modes.add_argument("--report", action="store_true")
    modes.add_argument("--freeze-labels", action="store_true")
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--labels", "--label-file", dest="labels", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--samples", type=int, default=SAMPLES)
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    return parser


def _error(message: str, code: int = 1) -> int:
    print(f"drain details prose probe: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.samples < 1:
            return _error("--samples must be positive", 2)
        if args.freeze_labels:
            if args.labels is None:
                return _error("--freeze-labels requires --labels", 2)
            freeze = write_label_freeze(args.labels)
            print(f"labels frozen at {freeze}")
            return 0
        if args.sheets:
            if args.rows is None or args.out is None:
                return _error("--sheets requires --rows and --out", 2)
            sheets(args.rows, args.out)
            return 0
        if args.report:
            if args.rows is None or args.labels is None or args.out is None:
                return _error("--report requires --rows, --labels and --out", 2)
            rendered, passed = report(args.rows, args.labels, args.out)
            print(rendered, end="")
            return 0 if passed else 1
        if args.run and not args.confirm:
            return _error("run mode requires --confirm", 2)
        document = capture_payloads()
        document["samples"] = args.samples
        errors = []
        calls = _planned(document)
        if args.capture:
            if args.out is None:
                return _error("--capture requires --out", 2)
            _write_json(args.out, document)
            print(f"2 payloads written to {args.out}")
            return 0
        if args.validate:
            print("recorded prompt: PASS")
            print("offline arm cross-check: PASS")
            return 0
        if args.dry_run or args.run:
            if len(calls) > args.max_calls:
                errors.append(f"planned calls {len(calls)} exceed --max-calls {args.max_calls}")
            ceiling = _usd_ceiling(document)
            if ceiling > args.max_usd:
                errors.append(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
            if args.dry_run:
                print(f"planned calls: {len(calls)}")
                print(f"token estimate: {_token_estimate(document):.2f}")
                print(f"USD ceiling: ${ceiling:.6f}")
            if errors:
                for error in errors:
                    print(error, file=sys.stderr)
                return 1
            if args.dry_run:
                return 0
        if args.run:
            if args.out is None:
                return _error("run mode requires --out", 2)
            result = run_rows(document, max_calls=args.max_calls, max_usd=args.max_usd, out=args.out)
            print(f"{len(result['rows'])} rows written to {args.out}")
            return 0 if result.get("stop_reason") is None else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))
    return _error("no mode selected", 2)


if __name__ == "__main__":
    raise SystemExit(main())

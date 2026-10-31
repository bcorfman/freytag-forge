"""Build and run the preregistered T9h hidden-bench prose probe."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_RELATIVE = Path("data/stories/continuity-initiative")
PACKAGE_ROOT = ROOT / PACKAGE_RELATIVE
STATES = ("opening", "prefind", "find")
ARMS = ("P0", "P1")
SAMPLES = 10
PLANNED_CALLS = len(STATES) * len(ARMS) * SAMPLES
DEFAULT_MAX_CALLS = PLANNED_CALLS
DEFAULT_MAX_USD = 0.06
COST_PER_MILLION_INPUT_TOKENS = 0.042
SHUFFLE_SEED = 731904
FIND_TEXT = "Kristin reaches beneath the park bench"
PREFLIGHT_TERMS = ("transit", "token", "number sequence", "photograph", "photo")
LABEL_NAMES = (
    "names_clue_object",
    "describes_photograph_content",
    "states_route_or_identity",
    "claims_nothing_under_bench",
    "moves_fixed_bench",
    "conveys_all_three_objects_and_keeping",
    "invents_fourth_object",
)
P1A_BAD_LABELS = LABEL_NAMES[:5]


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _package_from_head(destination: Path) -> Path:
    archive = destination / "package.tar"
    extracted = destination / "exported"
    with archive.open("wb") as handle:
        subprocess.run(
            ["git", "-C", str(ROOT), "archive", "--format=tar", "--prefix=", "HEAD", str(PACKAGE_RELATIVE)],
            check=True,
            stdout=handle,
        )
    extracted.mkdir()
    subprocess.run(["tar", "-xf", str(archive), "-C", str(extracted)], check=True)
    return extracted / PACKAGE_RELATIVE


def _scene_1b_state(package: object) -> Any:
    from storygame.runtime.state import RuntimeState
    from storygame.runtime.world_model import apply_scene_placements, world_for

    state = RuntimeState.bootstrap(package)
    state.current_scene_id = "1B"
    state.phase = next(scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == "1B")
    state._assert_scene_entry_fact("1B")
    apply_scene_placements(package, state.facts, "1B")
    world_for(package, state.facts).move(package.world.protagonist_id, "park_bench")
    state.active_event_ids.update(
        storylet.id for storylet in package.storylet_routes.storylets if storylet.scene_id == "1B"
    )
    return state


def _world_aware_provider(state: Any) -> Any:
    from storygame.runtime.capture import capture_prompt_variant
    from storygame.runtime.item_facts import ItemFactsProvider

    return ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        prompt_variant=capture_prompt_variant(state.package),
        item_facts={},
        mode="single_call",
        state_axes={},
        seed_from_package=True,
        drop_rules=(),
        held_by=True,
        mark_fixed=False,
    )


def _composed_segments(result: object) -> list[dict[str, str]]:
    return [{"kind": segment.kind, "text": segment.text} for segment in result.segments]


def _capture_package(package_root: Path, arm: str) -> list[dict[str, Any]]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.story_package.loader import load_story_package

    package = load_story_package(package_root)
    captured: list[dict[str, Any]] = []

    def stub_request(provider: object, payload: dict[str, object]) -> dict[str, object]:
        if payload.get("__freytag_request_budget", "narration") == "item_facts":
            return {"refers": [], "same_as": {}}
        model_segments = [{"kind": "narration", "text": "A short canned narration segment."}]
        captured.append(
            {
                "system": payload["system"],
                "user": payload["user"],
                "model_segment_count": len(model_segments),
            }
        )
        return {
            "segments": model_segments,
            "selected_knowledge_ids": [],
            "item_facts": {},
        }

    original_request = CloudflareTurnProvider._request
    CloudflareTurnProvider._request = stub_request
    try:
        for state_name in STATES:
            state = _scene_1b_state(package)
            provider = _world_aware_provider(state)
            engine = RuntimeEngine(state, provider)
            if state_name == "opening":
                result = engine.opening()
            else:
                engine.opening()
                command = "Inspect the park bench." if state_name == "prefind" else "Look under the park bench."
                result = engine.turn(command)
            prompt = captured[-1]
            captured[-1] = {
                "id": f"{arm.lower()}-{state_name}",
                "arm": arm,
                "state": state_name,
                "system": prompt["system"],
                "user": prompt["user"],
                "model_segment_count": prompt["model_segment_count"],
                "composed_segments": _composed_segments(result),
            }
    finally:
        CloudflareTurnProvider._request = original_request
    return [item for item in captured if "id" in item]


def capture_payloads() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="t9h-hidden-prose-") as temporary:
        temporary_root = Path(temporary)
        p0_root = _package_from_head(temporary_root)
        payloads = [*_capture_package(p0_root, "P0"), *_capture_package(PACKAGE_ROOT, "P1")]
    payloads.sort(key=lambda item: (STATES.index(item["state"]), ARMS.index(item["arm"])))
    return {"schema": 1, "stage": "t9h-hidden-prose", "payloads": payloads}


def _payload_material(payload: dict[str, Any]) -> str:
    return f"{payload.get('system', '')}\n{payload.get('user', '')}"


def preflight(document: dict[str, Any]) -> list[str]:
    payloads = document.get("payloads")
    if not isinstance(payloads, list):
        return ["capture document has no payloads list"]
    errors: list[str] = []
    p1_payloads = [payload for payload in payloads if isinstance(payload, dict) and payload.get("arm") == "P1"]
    for payload in p1_payloads:
        if payload.get("state") in {"opening", "prefind"}:
            material = _payload_material(payload).casefold()
            for term in PREFLIGHT_TERMS:
                if term in material:
                    errors.append(f"P1 {payload.get('state')} contains forbidden term {term!r}")
        if payload.get("state") == "find" and FIND_TEXT not in _payload_material(payload):
            errors.append("P1 find payload does not carry the authored find text")
    expected = {(state, arm) for state in STATES for arm in ARMS}
    actual = {(payload.get("state"), payload.get("arm")) for payload in payloads if isinstance(payload, dict)}
    if actual != expected:
        errors.append("capture document must contain exactly three states for both arms")
    return errors


def _token_estimate(document: dict[str, Any]) -> float:
    payloads = document.get("payloads", ())
    characters = sum(
        len(str(payload.get("system", ""))) + len(str(payload.get("user", "")))
        for payload in payloads
        if isinstance(payload, dict)
    )
    return characters * SAMPLES / 4


def _usd_ceiling(document: dict[str, Any]) -> float:
    return _token_estimate(document) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _planned(document: dict[str, Any]) -> list[dict[str, Any]]:
    payloads = document.get("payloads", ())
    calls = []
    for payload in payloads:
        for sample in range(1, SAMPLES + 1):
            calls.append({"payload": payload, "sample": sample})
    return calls


def _status_code(error: BaseException) -> int | None:
    value = getattr(error, "code", None)
    if isinstance(value, int):
        return value
    value = getattr(error, "status_code", None)
    return value if isinstance(value, int) else None


def _stop_reason(error: BaseException) -> str:
    status = _status_code(error)
    if status == 429:
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

    if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
        raise ValueError("run mode requires CLOUDFLARE_WORKER_URL")
    if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
        raise ValueError("run mode requires CLOUDFLARE_WORKER_TOKEN")
    package = load_story_package(PACKAGE_ROOT)
    calls = _planned(document)
    if len(calls) > max_calls:
        raise ValueError(f"planned calls {len(calls)} exceed --max-calls {max_calls}")
    ceiling = _usd_ceiling(document)
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    rows_document: dict[str, Any] = {
        "schema": 1,
        "stage": "t9h-hidden-prose",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": "incomplete",
    }
    _write_json(out, rows_document)
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
                "state": payload["state"],
                "sample": call["sample"],
                "response_text": response_text,
            }
        )
        _write_json(out, rows_document)
    if len(rows_document["rows"]) == len(calls):
        rows_document["stop_reason"] = None
        _write_json(out, rows_document)
    else:
        rows_document["stop_reason"] = "max_calls"
        _write_json(out, rows_document)
    return rows_document


def _labels_template(rows: list[dict[str, Any]]) -> dict[str, dict[str, bool | None]]:
    return {f"sample-{index:03d}": {name: None for name in LABEL_NAMES} for index, _row in enumerate(rows, start=1)}


def _freeze_path(labels_path: Path) -> Path:
    return labels_path.parent / "labels.freeze.json"


def write_label_freeze(labels_path: Path) -> Path:
    freeze = _freeze_path(labels_path)
    _write_json(freeze, {"sha256": _sha256(labels_path)})
    return freeze


def sheets(rows_path: Path, output: Path) -> None:
    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    indexed = _shuffled_rows(rows)
    output.mkdir(parents=True, exist_ok=True)
    sheet_lines = ["# Blind prose sheet", "", f"Shuffle seed: {SHUFFLE_SEED}", ""]
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
                "Narration:",
                str(row.get("response_text", "(none)")),
                "",
            ]
        )
    sheet_path = output / "blind_sheet.md"
    sheet_path.write_text("\n".join(sheet_lines), encoding="utf-8")
    key_path = output / "blind_key.json"
    _write_json(key_path, key)
    labels_path = output / "labels_template.json"
    _write_json(labels_path, labels)
    write_label_freeze(labels_path)


def _shuffled_rows(rows: list[dict[str, Any]]) -> list[tuple[int, dict[str, Any]]]:
    indexed = list(enumerate(rows, start=1))
    random.Random(SHUFFLE_SEED).shuffle(indexed)
    return indexed


def assert_blind_key_bijection(rows: list[dict[str, Any]], key: dict[str, Any]) -> None:
    expected_indexes = set(range(1, len(rows) + 1))
    entries = list(key.values())
    indexes = [entry.get("row_index") for entry in entries if isinstance(entry, dict)]
    if len(entries) != len(indexes) or len(indexes) != len(set(indexes)) or set(indexes) != expected_indexes:
        raise AssertionError("blind key row_index values are not a bijection over the rows")
    for entry in entries:
        row = rows[entry["row_index"] - 1]
        for field in ("payload_id", "arm", "state", "sample"):
            if entry.get(field) != row.get(field):
                raise AssertionError(f"blind key {field} does not match row {entry['row_index']}")


def _turn_proposal(response_text: str) -> Any:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.contracts import TurnProposal
    from storygame.runtime.item_facts import ItemFactsProvider

    payload = json.loads(response_text)
    if isinstance(payload, dict):
        world_aware_extra_keys: set[str] = set(ItemFactsProvider.allowed_reply_keys) - set(
            CloudflareTurnProvider.allowed_reply_keys
        )
        payload = {key: value for key, value in payload.items() if key not in world_aware_extra_keys}
    return TurnProposal.model_validate(payload)


def _inferred_delivery(package: object, state_name: str, response_text: str) -> tuple[list[dict[str, str]], bool]:
    proposal = _turn_proposal(response_text)
    if state_name == "opening":
        return [], True
    state = _scene_1b_state(package)
    provider = _world_aware_provider(state)
    command = "Inspect the park bench." if state_name == "prefind" else "Look under the park bench."
    provider.assemble_turn_prompt(command)
    if provider.authored_handoff is not None:
        composed = provider._compose_authored_handoff(proposal)
    else:
        composed = provider._compose_staged_cue(proposal)
    appended = composed.segments[len(proposal.segments) :]
    return [{"kind": segment.kind, "text": segment.text} for segment in appended], True


def composed_view(rows_path: Path, output: Path) -> None:
    from storygame.story_package.loader import load_story_package

    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    package = load_story_package(PACKAGE_ROOT)
    output.mkdir(parents=True, exist_ok=True)
    indexed = _shuffled_rows(rows)
    raw_lines = ["# Raw prose view", ""]
    composed_lines = [
        "# Composed prose view",
        "",
        "This is a post hoc, inferred composition, not a set of accepted game turns.",
        "It does not change the recorded stage 2 FAIL.",
        "",
    ]
    for display_index, (_row_index, row) in enumerate(indexed, start=1):
        opaque_id = f"sample-{display_index:03d}"
        state = row.get("state", "(unknown)")
        sample = row.get("sample", "(unknown)")
        response_text = str(row.get("response_text", "(none)"))
        section = [
            f"## {opaque_id}",
            "",
            f"State: {state}",
            f"Sample: {sample}",
            "",
            "Narration:",
            response_text,
            "",
        ]
        raw_lines.extend(section)
        composed_lines.extend(
            [
                f"## {opaque_id}",
                "",
                f"State: {state}",
                f"Sample: {sample}",
                "",
                "Narrator:",
                response_text,
            ]
        )
        try:
            delivery, composable = _inferred_delivery(package, str(state), response_text)
        except (TypeError, ValueError, json.JSONDecodeError):
            composable = False
            delivery = []
        if not composable:
            composed_lines.extend(["", "not composable"])
        elif delivery:
            composed_lines.extend(["", "Engine (appended by the game):"])
            composed_lines.extend(segment["text"] for segment in delivery)
        composed_lines.append("")
    (output / "raw_view.md").write_text("\n".join(raw_lines), encoding="utf-8")
    (output / "composed_view.md").write_text("\n".join(composed_lines), encoding="utf-8")


def _freeze_hash(labels_path: Path) -> str:
    freeze_candidates = (
        _freeze_path(labels_path),
        labels_path.with_name(labels_path.name + ".freeze.json"),
        labels_path.with_suffix(".freeze.json"),
    )
    for freeze_path in freeze_candidates:
        if freeze_path.is_file():
            document = _read_json(freeze_path)
            value = document.get("sha256") or document.get("labels_sha256")
            if isinstance(value, str):
                return value
    raise ValueError("labels file has no frozen sha256 file")


def _label_value(labels: dict[str, Any], opaque_id: str, name: str) -> bool | None:
    entry = labels.get(opaque_id)
    if not isinstance(entry, dict):
        return None
    value = entry.get(name)
    return value if isinstance(value, bool) else None


def _missing_labels(rows: list[dict[str, Any]], labels: dict[str, Any], key: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for opaque_id, value in key.items():
        if not isinstance(value, dict):
            missing.append(opaque_id)
            continue
        if not isinstance(labels.get(opaque_id), dict):
            missing.append(opaque_id)
            continue
        for name in LABEL_NAMES:
            if not isinstance(labels[opaque_id].get(name), bool):
                missing.append(f"{opaque_id} {name}")
    if len(key) != len(rows):
        missing.append("key does not cover every row")
    return missing


def _joined_rows(rows: list[dict[str, Any]], labels: dict[str, Any], key: dict[str, Any]) -> list[dict[str, Any]]:
    by_index = {index: row for index, row in enumerate(rows, start=1)}
    joined = []
    for opaque_id, value in key.items():
        row = by_index.get(value.get("row_index")) if isinstance(value, dict) else None
        if row is None:
            continue
        joined.append({"opaque_id": opaque_id, "row": row, "labels": labels[opaque_id]})
    return joined


def report(rows_path: Path, labels_path: Path, output: Path) -> tuple[str, bool]:
    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    actual_hash = _sha256(labels_path)
    frozen_hash = _freeze_hash(labels_path)
    if actual_hash != frozen_hash:
        raise ValueError("labels sha256 does not match the frozen labels hash")
    key_path = labels_path.parent / "blind_key.json"
    if not key_path.is_file():
        raise ValueError("blind_key.json is required beside the labels file")
    key = _read_json(key_path)
    labels = _read_json(labels_path)
    if not isinstance(key, dict) or not isinstance(labels, dict):
        raise ValueError("labels and blind key must be JSON objects")
    missing = _missing_labels(rows, labels, key)
    if missing:
        raise ValueError("MISSING LABELS: " + ", ".join(missing))
    joined = _joined_rows(rows, labels, key)
    p1_open_prefind = [
        item for item in joined if item["row"].get("arm") == "P1" and item["row"].get("state") in {"opening", "prefind"}
    ]
    p1_find = [item for item in joined if item["row"].get("arm") == "P1" and item["row"].get("state") == "find"]
    p1_rows = [item for item in joined if item["row"].get("arm") == "P1"]
    p1a_bad = sum(any(item["labels"][name] for name in P1A_BAD_LABELS) for item in p1_open_prefind)
    p1b_good = sum(
        item["labels"]["conveys_all_three_objects_and_keeping"] and not item["labels"]["states_route_or_identity"]
        for item in p1_find
    )
    p1c_invented = sum(item["labels"]["invents_fourth_object"] for item in p1_rows)
    complete = document.get("stop_reason") is None and len(rows) == document.get("calls_planned") == PLANNED_CALLS
    p1a_pass = len(p1_open_prefind) == 20 and p1a_bad == 0
    p1b_pass = len(p1_find) == 10 and p1b_good >= 9
    p1c_pass = len(p1_rows) == 30 and p1c_invented == 0
    lines = [
        "# T9h hidden-bench prose report",
        "",
        f"Rows: {len(rows)}/{document.get('calls_planned', '(unknown)')} | complete: {'yes' if complete else 'no'}",
        f"labels sha256: {actual_hash}",
        "",
        f"P1a: {'PASS' if p1a_pass else 'FAIL'} — {p1a_bad} prohibited labels in "
        f"{len(p1_open_prefind)} opening/pre-find samples",
        f"P1b: {'PASS' if p1b_pass else 'FAIL'} — {p1b_good}/{len(p1_find)} find samples "
        "convey all three and keeping without route/identity",
        f"P1c: {'PASS' if p1c_pass else 'FAIL'} — {p1c_invented} fourth-object labels in {len(p1_rows)} P1 samples",
        f"Overall: {'PASS' if complete and p1a_pass and p1b_pass and p1c_pass else 'FAIL'}",
    ]
    return "\n".join(lines) + "\n", complete and p1a_pass and p1b_pass and p1c_pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--capture", action="store_true")
    modes.add_argument("--validate", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--sheets", action="store_true")
    modes.add_argument("--composed-view", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    return parser


def _error(message: str, code: int = 1) -> int:
    print(f"hidden bench prose probe: {message}", file=sys.stderr)
    return code


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.sheets:
            if args.rows is None or args.out is None:
                return _error("--sheets requires --rows and --out", 2)
            sheets(args.rows, args.out)
            return 0
        if args.composed_view:
            if args.rows is None or args.out is None:
                return _error("--composed-view requires --rows and --out", 2)
            composed_view(args.rows, args.out)
            return 0
        if args.report:
            if args.rows is None or args.labels is None or args.out is None:
                return _error("--report requires --rows, --labels and --out", 2)
            rendered, passed = report(args.rows, args.labels, args.out)
            print(rendered, end="")
            args.out.write_text(rendered, encoding="utf-8")
            return 0 if passed else 1
        document = capture_payloads()
        errors = preflight(document)
        if errors:
            for error in errors:
                print(error, file=sys.stderr)
            return 1
        if args.capture:
            if args.out is None:
                return _error("--capture requires --out", 2)
            _write_json(args.out, document)
            print(f"{len(document['payloads'])} payloads written to {args.out}")
            return 0
        if args.validate:
            print("capture payloads: 6")
            print("pre-flight: PASS")
            return 0
        calls = _planned(document)
        if args.dry_run:
            print(f"planned calls: {len(calls)}")
            print(f"token estimate: {_token_estimate(document):.2f}")
            print(f"USD ceiling: ${_usd_ceiling(document):.6f}")
            if len(calls) > args.max_calls:
                return _error(f"planned calls {len(calls)} exceed --max-calls {args.max_calls}")
            if _usd_ceiling(document) > args.max_usd:
                return _error(f"USD ceiling ${_usd_ceiling(document):.6f} exceeds --max-usd ${args.max_usd:.6f}")
            return 0
        if args.run:
            if not args.confirm:
                return _error("run mode requires --confirm", 2)
            if args.out is None:
                return _error("run mode requires --out", 2)
            if len(calls) > args.max_calls:
                return _error(f"planned calls {len(calls)} exceed --max-calls {args.max_calls}", 1)
            ceiling = _usd_ceiling(document)
            if ceiling > args.max_usd:
                return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}", 1)
            result = run_rows(document, max_calls=args.max_calls, max_usd=args.max_usd, out=args.out)
            print(f"{len(result['rows'])} rows written to {args.out}")
            return 0 if result.get("stop_reason") is None else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError, subprocess.SubprocessError) as error:
        return _error(str(error))
    return _error("no mode selected", 2)


if __name__ == "__main__":
    raise SystemExit(main())

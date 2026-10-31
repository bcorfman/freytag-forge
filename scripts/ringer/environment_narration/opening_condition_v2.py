"""Build and run the preregistered T9h opening-condition judge."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import random
import socket
import statistics
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data" / "stories" / "continuity-initiative"
WORLD_PATH = PACKAGE_ROOT / "world.yaml"
STAGE = "t9h-opening-v2"
SAMPLES = 10
JUDGE_SAMPLES = 5
SHUFFLE_SEED = 880419
COST_PER_MILLION_INPUT_TOKENS = 0.39
EXCLUDED = {"storm_drain"}
LABEL_NAMES = (
    "opens_or_enters",
    "invents_open_state",
    "asserts_definite_contents",
    "speculative_only",
    "asserts_closed_or_locked",
    "wrong_place",
)
FORBIDDEN_LABELS = LABEL_NAMES[:3]
CASE_FIELDS = {"id", "set", "thing", "command", "narration", "declared", "forbidden", "source_ref"}
PROMPTS = {
    "back_door": ("1A", "kitchen", "Inspect the back door."),
    "house_gate": ("1A", "outside_house", "Inspect the house gate."),
    "service_gate": ("1B", "los_angeles_park", "Inspect the service gate."),
    "facility_gate": ("2A", "facility_perimeter", "Inspect the facility gate."),
}


def _load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise RuntimeError(f"cannot load helper from {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def _capture_probe() -> Any:
    return _load_module(
        ROOT / "scripts/ringer/environment_narration/drain_details_capture.py",
        "opening_condition_v2_capture_helpers",
    )


def _judge_probe() -> Any:
    return _load_module(
        ROOT / "scripts/ringer/environment_narration/drain_condition_judge_probe.py",
        "opening_condition_v2_judge_helpers",
    )


def _load_package(root: Path = PACKAGE_ROOT) -> Any:
    from storygame.story_package.loader import load_story_package

    return load_story_package(root)


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _schema(package: Any) -> Any:
    from worldkeeper import WorldSchema

    from storygame.story_package.world_schema import world_source_schema_data

    return WorldSchema.from_data(world_source_schema_data(package.world))


def _opening_items(package: Any) -> list[Any]:
    schema = _schema(package)
    return [item for item in package.world.items if schema.kind_is(item.kind, "opening")]


def _captured_items(package: Any) -> list[Any]:
    items = [item for item in _opening_items(package) if item.id not in EXCLUDED]
    expected = set(PROMPTS)
    actual = {item.id for item in items}
    if actual != expected:
        raise ValueError(
            f"opening class does not match the preregistered table: class={sorted(actual)} table={sorted(expected)}"
        )
    return sorted(items, key=lambda item: item.id)


def _scene_state(package: Any, scene_id: str, place_id: str) -> Any:
    from storygame.runtime.state import RuntimeState
    from storygame.runtime.world_model import apply_scene_placements, world_for

    state = RuntimeState.bootstrap(package)
    if scene_id != state.current_scene_id:
        state.current_scene_id = scene_id
        state.phase = next(
            scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == scene_id
        )
        state._assert_scene_entry_fact(scene_id)
        apply_scene_placements(package, state.facts, scene_id)
    world = world_for(package, state.facts)
    result = world.move(package.world.protagonist_id, place_id)
    if not result.ok:
        raise ValueError(f"could not place protagonist in {place_id}: {result.reason}")
    return state


def _fake_response() -> dict[str, object]:
    return {
        "segments": [{"kind": "narration", "text": "The scene continues."}],
        "selected_knowledge_ids": [],
        "item_facts": {},
    }


def _offline_response(payload: dict[str, object], declared_name: str) -> dict[str, object]:
    from storygame.runtime.item_facts import _MATCH_SYSTEM, _SECOND_CALL_SYSTEM

    if payload.get("system") == _MATCH_SYSTEM:
        return {"refers": [declared_name], "same_as": {}, "kind": {}}
    if payload.get("__freytag_request_budget") == "item_facts" or payload.get("system") == _SECOND_CALL_SYSTEM:
        return {"item_facts": {}}
    return _fake_response()


def _capture_request(
    package: Any,
    scene_id: str,
    place_id: str,
    command: str,
    declared_name: str,
) -> dict[str, object]:
    from storygame.runtime.capture import WorldCapture
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.engine import RuntimeEngine

    probe = _capture_probe()
    state = _scene_state(package, scene_id, place_id)
    provider = probe._load_probe()._world_aware_provider(state)
    requests: list[dict[str, object]] = []

    def recording_request(_provider: Any, payload: dict[str, object]) -> dict[str, object]:
        if payload.get("__freytag_request_budget", "narration") != "item_facts":
            requests.append({key: value for key, value in payload.items() if not key.startswith("__")})
        return _offline_response(payload, declared_name)

    original_request = CloudflareTurnProvider._request
    CloudflareTurnProvider._request = recording_request
    try:
        capture = WorldCapture(
            provider,
            lambda _state, questions: {key: {"noul": 0.0} for key in questions},
        )
        engine = RuntimeEngine(state, provider, capture=capture)
        engine.opening()
        requests.clear()
        engine.turn(command)
    finally:
        CloudflareTurnProvider._request = original_request
    for request in requests:
        if str(request.get("system", "")).startswith("You are the narrator"):
            return request
    raise ValueError("turn produced no narrator request")


def capture(out: Path) -> dict[str, Any]:
    package = _load_package()
    items = _captured_items(package)
    things = []
    for item in items:
        scene_id, place_id, command = PROMPTS[item.id]
        entry: dict[str, Any] = {
            "thing_id": item.id,
            "name": item.name,
            "scene_id": scene_id,
            "place_id": place_id,
            "command": command,
            "status": "not reproducible offline",
            "error": None,
            "request": None,
            "storylets_activated": [],
        }
        try:
            entry["request"] = _capture_request(package, scene_id, place_id, command, item.name)
            entry["status"] = "captured"
        except Exception as error:  # noqa: BLE001 - preserve per-thing offline evidence
            entry["error"] = f"{type(error).__name__}: {error}"
        things.append(entry)
    document = {
        "schema": 1,
        "stage": STAGE,
        "package_world_sha256": _sha256_path(WORLD_PATH),
        "things": things,
    }
    _write_json(out, document)
    return document


def _captured_requests(document: dict[str, Any]) -> list[dict[str, Any]]:
    things = document.get("things")
    if not isinstance(things, list):
        raise ValueError("capture document has no things list")
    captured = []
    for thing in things:
        if not isinstance(thing, dict) or thing.get("status") != "captured":
            continue
        request = thing.get("request")
        if not isinstance(request, dict):
            raise ValueError(f"captured thing has no request: {thing.get('thing_id')}")
        captured.append(thing)
    return captured


def _planned_capture(document: dict[str, Any], samples: int) -> list[dict[str, Any]]:
    return [
        {"thing": thing, "sample": sample} for thing in _captured_requests(document) for sample in range(1, samples + 1)
    ]


def _capture_token_estimate(document: dict[str, Any], samples: int, max_calls: int | None = None) -> float:
    captured = _captured_requests(document)
    characters = sum(
        len(str(thing["request"].get("system", ""))) + len(str(thing["request"].get("user", ""))) for thing in captured
    )
    if not captured:
        return 0
    calls = len(captured) * samples if max_calls is None else max_calls
    return characters * calls / len(captured) / 4


def _capture_usd_ceiling(document: dict[str, Any], samples: int, max_calls: int | None = None) -> float:
    return _capture_token_estimate(document, samples, max_calls) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _exception_chain(error: BaseException) -> list[BaseException]:
    chain = []
    pending = [error]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        chain.append(current)
        if current.__context__ is not None:
            pending.append(current.__context__)
        if current.__cause__ is not None:
            pending.append(current.__cause__)
    return chain


def _is_timeout(error: BaseException) -> bool:
    return any(isinstance(item, (TimeoutError, socket.timeout)) for item in _exception_chain(error))


def _status_code(error: BaseException) -> int | None:
    for item in _exception_chain(error):
        for name in ("code", "status_code"):
            value = getattr(item, name, None)
            if isinstance(value, int):
                return value
    return None


def _failure_text(error: BaseException) -> str:
    message = str(error)
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "")
    if token:
        message = message.replace(token, "<redacted>")
    return message[:300]


def _failed_call(call_index: int, planned: dict[str, Any], error: BaseException) -> dict[str, Any]:
    thing = planned["thing"]
    return {
        "call_index": call_index,
        "thing_id": thing["thing_id"],
        "sample": planned["sample"],
        "error_type": type(error).__name__,
        "error": _failure_text(error),
        "status": _status_code(error),
    }


def _stop_reason(error: BaseException) -> str:
    status = _status_code(error)
    if status == 429 or "quota" in str(error).casefold():
        return "http_429_quota_or_rate_limit"
    if status in {401, 403}:
        return f"auth_{status}"
    if status is not None and 500 <= status <= 599:
        return f"http_{status}"
    return "request_error"


def _response_text(response: object) -> str:
    if isinstance(response, str):
        return response
    return json.dumps(response, ensure_ascii=False, sort_keys=True)


def _narration(response_text: str) -> str:
    try:
        parsed = json.loads(response_text)
    except json.JSONDecodeError:
        return response_text
    if not isinstance(parsed, dict) or not isinstance(parsed.get("segments"), list):
        return response_text
    texts = [segment.get("text") for segment in parsed["segments"] if isinstance(segment, dict)]
    if not all(isinstance(text, str) for text in texts):
        return response_text
    return "".join(texts)


def run_rows(document: dict[str, Any], *, samples: int, max_calls: int, max_usd: float, out: Path) -> dict[str, Any]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.state import RuntimeState

    if samples != SAMPLES:
        raise ValueError(f"samples are frozen at {SAMPLES}")
    calls = _planned_capture(document, samples)
    if len(calls) > max_calls:
        raise ValueError(f"planned calls {len(calls)} exceed --max-calls {max_calls}")
    ceiling = _capture_usd_ceiling(document, samples, max_calls)
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    if out.exists():
        raise ValueError(f"rows already exist at {out}; refusing to overwrite")
    if len(_captured_requests(document)) < 3:
        raise ValueError("run mode requires at least 3 captured things")
    if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
        raise ValueError("run mode requires CLOUDFLARE_WORKER_URL")
    if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
        raise ValueError("run mode requires CLOUDFLARE_WORKER_TOKEN")
    from storygame.story_package.loader import load_story_package

    package = load_story_package(PACKAGE_ROOT)
    rows_document: dict[str, Any] = {
        "schema": 1,
        "stage": STAGE,
        "samples": samples,
        "calls_planned": len(calls),
        "rows": [],
        "failed_calls": [],
        "stop_reason": "incomplete",
    }
    _write_json(out, rows_document)
    timed_out: list[dict[str, Any]] = []
    consecutive_failures = 0
    call_index = 0
    final_failure_reason: str | None = None

    def send(planned: dict[str, Any], attempt: int) -> BaseException | None:
        nonlocal call_index, consecutive_failures, final_failure_reason
        call_index += 1
        thing = planned["thing"]
        provider = CloudflareTurnProvider(
            worker_url=os.environ["CLOUDFLARE_WORKER_URL"].strip(),
            token=os.environ["CLOUDFLARE_WORKER_TOKEN"].strip(),
            state=RuntimeState.bootstrap(package),
        )
        try:
            response = provider._request(thing["request"])
        except Exception as error:
            rows_document["failed_calls"].append(_failed_call(call_index, planned, error))
            consecutive_failures += 1
            if consecutive_failures >= 3:
                rows_document["stop_reason"] = "three_consecutive_failures"
            elif not _is_timeout(error):
                rows_document["stop_reason"] = _stop_reason(error)
            elif attempt == 2:
                final_failure_reason = _stop_reason(error)
            _write_json(out, rows_document)
            return error
        consecutive_failures = 0
        response_text = _response_text(response)
        rows_document["rows"].append(
            {
                "call_index": call_index,
                "thing_id": thing["thing_id"],
                "command": thing["command"],
                "sample": planned["sample"],
                "attempt": attempt,
                "response_text": response_text,
                "narration": _narration(response_text),
            }
        )
        _write_json(out, rows_document)
        return None

    for planned in calls:
        error = send(planned, 1)
        if error is None:
            continue
        if rows_document["stop_reason"] != "incomplete":
            return rows_document
        if _is_timeout(error):
            timed_out.append(planned)
            continue
        return rows_document

    for planned in timed_out:
        if call_index >= max_calls:
            rows_document["stop_reason"] = "max_calls"
            _write_json(out, rows_document)
            return rows_document
        error = send(planned, 2)
        if error is not None and rows_document["stop_reason"] != "incomplete":
            return rows_document

    if final_failure_reason is not None:
        rows_document["stop_reason"] = final_failure_reason
    elif len(rows_document["rows"]) == len(calls):
        rows_document["stop_reason"] = None
    else:
        rows_document["stop_reason"] = "request_error"
    _write_json(out, rows_document)
    return rows_document


def blind_sheet(rows_path: Path, out: Path) -> None:
    document = _read_json(rows_path)
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    indexed = list(enumerate(rows, start=1))
    random.Random(SHUFFLE_SEED).shuffle(indexed)
    lines = ["# Blind opening narration sheet", ""]
    key: dict[str, int] = {}
    labels: dict[str, dict[str, None]] = {}
    for display_index, (row_index, row) in enumerate(indexed, start=1):
        opaque_id = f"sample-{display_index:03d}"
        call_index = row.get("call_index") if isinstance(row, dict) else None
        if not isinstance(call_index, int):
            raise ValueError(f"row {row_index} has no call_index")
        key[opaque_id] = call_index
        labels[opaque_id] = {name: None for name in LABEL_NAMES}
        narration = row.get("narration") if isinstance(row, dict) else None
        lines.extend([f"## {opaque_id}", "", "Narration:", str(narration if narration is not None else "(none)"), ""])
    out.mkdir(parents=True, exist_ok=True)
    (out / "sheet.md").write_text("\n".join(lines), encoding="utf-8")
    _write_json(out / "blind_key.json", key)
    _write_json(out / "labels_template.json", labels)


def _freeze_path(labels: Path) -> Path:
    return labels.with_name(f"{labels.stem}.freeze.json")


def freeze_labels(labels: Path) -> Path:
    document = _read_json(labels)
    if not isinstance(document, dict):
        raise ValueError("labels file must be a JSON object")
    for opaque_id, entry in document.items():
        if not isinstance(entry, dict):
            raise ValueError(f"labels file has an invalid label entry for {opaque_id}")
        if any(entry.get(name) is None for name in LABEL_NAMES):
            raise ValueError(f"labels file has null labels for {opaque_id}")
    freeze = _freeze_path(labels)
    digest = _sha256_path(labels)
    if freeze.exists():
        current = _read_json(freeze)
        if not isinstance(current, dict) or current.get("sha256") != digest:
            raise ValueError(f"freeze already exists with a different hash: {freeze}")
        return freeze
    _write_json(freeze, {"sha256": digest})
    return freeze


def _frozen_hash(labels: Path) -> str:
    freeze = _freeze_path(labels)
    if not freeze.is_file():
        raise ValueError("run --freeze-labels first")
    document = _read_json(freeze)
    value = document.get("sha256") if isinstance(document, dict) else None
    if not isinstance(value, str):
        raise ValueError("freeze file has no sha256")
    if value != _sha256_path(labels):
        raise ValueError("labels sha256 does not match the frozen labels hash")
    return value


def _load_cases_inputs(
    rows_path: Path, labels_path: Path, key_path: Path
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _frozen_hash(labels_path)
    rows_document = _read_json(rows_path)
    labels = _read_json(labels_path)
    key = _read_json(key_path)
    rows = rows_document.get("rows") if isinstance(rows_document, dict) else None
    if not isinstance(rows, list) or not isinstance(labels, dict) or not isinstance(key, dict):
        raise ValueError("rows, labels and key have invalid shapes")
    by_call = {}
    for opaque_id, call_index in key.items():
        if not isinstance(call_index, int):
            raise ValueError(f"blind key entry is not a call index: {opaque_id}")
        by_call[call_index] = opaque_id
    joined = []
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("rows contain a non-object")
        call_index = row.get("call_index")
        opaque_id = by_call.get(call_index)
        if opaque_id is None or opaque_id not in labels:
            raise ValueError(f"no frozen labels for call index {call_index}")
        joined.append({"row": row, "labels": labels[opaque_id]})
    return joined, rows_document


def _opening_name_map() -> dict[str, str]:
    package = _load_package()
    return {item.id: item.name for item in _opening_items(package)}


def build_cases(rows_path: Path, labels_path: Path, key_path: Path, out: Path) -> None:
    joined, _rows_document = _load_cases_inputs(rows_path, labels_path, key_path)
    names = _opening_name_map()
    cases = []
    for item in joined:
        row = item["row"]
        labels = item["labels"]
        thing_id = row.get("thing_id")
        if thing_id not in names:
            raise ValueError(f"case thing is not declared with kind opening: {thing_id}")
        if not all(isinstance(labels.get(name), bool) for name in LABEL_NAMES):
            raise ValueError(f"labels are incomplete for call index {row.get('call_index')}")
        sample = row.get("sample")
        if not isinstance(sample, int):
            raise ValueError(f"row has no sample: {row.get('call_index')}")
        case = {
            "id": f"{thing_id}-sample-{sample:03d}",
            "set": "opening",
            "thing": names[thing_id],
            "command": row["command"],
            "narration": row["narration"],
            "declared": (
                f"the {names[thing_id]} has no open or closed value, no declared contents, and is fixed in place."
            ),
            "forbidden": any(labels[name] for name in FORBIDDEN_LABELS),
            "source_ref": f"{thing_id}/sample-{sample}",
        }
        if set(case) != CASE_FIELDS:
            raise AssertionError("opening case fields do not match the judge probe")
        cases.append(case)
    cases_path = out / "cases.jsonl"
    lock_path = out / "lock.json"
    if cases_path.exists() or lock_path.exists():
        raise ValueError("cases or lock already exists; refusing to overwrite")
    data = "".join(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n" for case in cases).encode()
    out.mkdir(parents=True, exist_ok=True)
    cases_path.write_bytes(data)
    _write_json(lock_path, {"cases_sha256": _sha256_bytes(data), "case_count": len(cases)})


def _read_cases(directory: Path) -> tuple[list[dict[str, Any]], bytes]:
    cases_path = directory / "cases.jsonl"
    lock_path = directory / "lock.json"
    data = cases_path.read_bytes()
    lock = _read_json(lock_path)
    if not isinstance(lock, dict) or lock.get("cases_sha256") != _sha256_bytes(data):
        raise ValueError("cases lock does not match cases.jsonl")
    cases = []
    for line in data.decode(encoding="utf-8").splitlines():
        if line.strip():
            case = json.loads(line)
            if not isinstance(case, dict) or set(case) != CASE_FIELDS:
                raise ValueError("cases contain fields different from the judge probe")
            cases.append(case)
    if lock.get("case_count") != len(cases):
        raise ValueError("cases lock count does not match cases.jsonl")
    return cases, data


def _judge_token_estimate(cases: list[dict[str, Any]], samples: int, judge: Any) -> float:
    characters = sum(
        len(json.dumps(judge.variant_b_payload(case), ensure_ascii=False, separators=(",", ":"))) for case in cases
    )
    return characters * samples / 4


def _judge_usd_ceiling(cases: list[dict[str, Any]], samples: int, judge: Any) -> float:
    return _judge_token_estimate(cases, samples, judge) / 1_000_000 * judge.COST_PER_MILLION_INPUT_TOKENS * 1.5


def _planned_judge(cases: list[dict[str, Any]], samples: int) -> list[dict[str, Any]]:
    return [{"case": case, "sample": sample, "variant": "B"} for sample in range(1, samples + 1) for case in cases]


def _judge_rows(
    cases: list[dict[str, Any]],
    *,
    cases_hash: str,
    samples: int,
    max_calls: int,
    max_usd: float,
    min_interval_s: float,
    out: Path,
    client: Any,
) -> dict[str, Any]:
    judge = _judge_probe()
    if samples != JUDGE_SAMPLES:
        raise ValueError(f"samples are frozen at {JUDGE_SAMPLES}")
    planned = _planned_judge(cases, samples)
    if len(planned) > max_calls:
        raise ValueError(f"planned calls {len(planned)} exceed --max-calls {max_calls}")
    ceiling = _judge_usd_ceiling(cases, samples, judge)
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    if min_interval_s < 0:
        raise ValueError("--min-interval-s must be non-negative")
    if out.exists():
        raise ValueError(f"rows already exist at {out}; refusing to overwrite")
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "samples": samples,
        "calls_planned": len(planned),
        "rows": [],
        "stop_reason": "incomplete",
        "cases_sha256": cases_hash,
    }
    _write_json(out, document)
    unusable = 0
    last_started: float | None = None
    for call_index, item in enumerate(planned, start=1):
        if min_interval_s > 0 and last_started is not None:
            remaining = min_interval_s - (time.monotonic() - last_started)
            if remaining > 0:
                time.sleep(remaining)
        if min_interval_s > 0:
            last_started = time.monotonic()
        state, questions = judge.variant_b_payload(item["case"])
        started = time.perf_counter()
        try:
            answers = client.ask(state, questions)
        except Exception:
            if judge._status_stop_reason(client) is None:
                raise
            answers = None
        latency_ms = (time.perf_counter() - started) * 1000
        document["rows"].append(judge._row(call_index, item, answers, client, latency_ms, document["cases_sha256"]))
        stop_reason = judge._status_stop_reason(client)
        if stop_reason is None and answers is None:
            unusable += 1
            if unusable >= judge.UNUSABLE_STOP_AFTER:
                stop_reason = "three_consecutive_unusable"
        elif stop_reason is None:
            unusable = 0
        if stop_reason is None and len(document["rows"]) == len(planned):
            document["stop_reason"] = None
        elif stop_reason is not None:
            document["stop_reason"] = stop_reason
        _write_json(out, document)
        if stop_reason is not None:
            break
    if len(document["rows"]) == len(planned):
        document["stop_reason"] = None
        _write_json(out, document)
    return document


def judge_run(
    cases_directory: Path,
    *,
    samples: int,
    max_calls: int,
    max_usd: float,
    min_interval_s: float,
    confirm: bool,
    out: Path,
    dry_run: bool,
) -> tuple[int, str | None]:
    cases, cases_data = _read_cases(cases_directory)
    judge = _judge_probe()
    if samples != JUDGE_SAMPLES:
        raise ValueError(f"samples are frozen at {JUDGE_SAMPLES}")
    planned = len(cases) * samples
    ceiling = _judge_usd_ceiling(cases, samples, judge)
    if planned > max_calls:
        raise ValueError(f"planned calls {planned} exceed --max-calls {max_calls}")
    if ceiling > max_usd:
        raise ValueError(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${max_usd:.6f}")
    if dry_run:
        text = f"planned calls: {planned}\nUSD ceiling: ${ceiling:.6f}"
        print(text)
        return 0, text
    if not confirm:
        raise ValueError("judge mode requires --confirm")
    if out.exists():
        raise ValueError(f"rows already exist at {out}; refusing to overwrite")
    if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
        raise ValueError("judge mode requires CLOUDFLARE_WORKER_URL")
    if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
        raise ValueError("judge mode requires CLOUDFLARE_WORKER_TOKEN")
    from storygame.runtime.jev import JevClient

    _judge_rows(
        cases,
        samples=samples,
        max_calls=max_calls,
        max_usd=max_usd,
        min_interval_s=min_interval_s,
        out=out,
        cases_hash=_sha256_bytes(cases_data),
        client=JevClient.from_environment(),
    )
    return 0, None


def _case_outcome(rows: list[dict[str, Any]], case_id: str, samples: int, judge: Any) -> tuple[str, float | None]:
    scores = [row.get("score") for row in rows if isinstance(row.get("score"), (int, float))]
    if len(scores) != samples:
        return "uncertain", None
    median = float(statistics.median(scores))
    return judge._verdict(median), median


def report_rows(cases_directory: Path, rows_path: Path, out: Path) -> str:
    cases, cases_data = _read_cases(cases_directory)
    document = _read_json(rows_path)
    rows = document.get("rows") if isinstance(document, dict) else None
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    if document.get("cases_sha256") not in {None, _sha256_bytes(cases_data)}:
        raise ValueError("rows file does not match the frozen cases")
    judge = _judge_probe()
    samples = document.get("samples", JUDGE_SAMPLES)
    planned = len(cases) * samples if isinstance(samples, int) else len(cases) * JUDGE_SAMPLES
    partial = document.get("stop_reason") is not None or len(rows) < planned
    results = {}
    for case in cases:
        case_rows = [row for row in rows if row.get("variant") == "B" and row.get("case_id") == case["id"]]
        results[case["id"]] = _case_outcome(case_rows, case["id"], samples, judge)
    forbidden_cases = [case for case in cases if case.get("forbidden") is True]
    clean_cases = [case for case in cases if case.get("forbidden") is False]
    forbidden_rejected = sum(results[case["id"]][0] == "reject" for case in forbidden_cases)
    clean_accepted = sum(results[case["id"]][0] == "accept" for case in clean_cases)
    if partial or len(forbidden_cases) < 10 or len(clean_cases) < 10:
        verdict = "INCONCLUSIVE"
    elif forbidden_rejected / len(forbidden_cases) >= 0.9 and clean_accepted / len(clean_cases) >= 0.9:
        verdict = "PASS"
    else:
        verdict = "FAIL"
    lines = [
        "# T9h opening condition v2 report",
        "",
        f"Rows rendered: {len(rows)}",
        f"Planned calls: {planned}",
        f"Run completeness: {'partial' if partial else 'complete'}",
        "",
    ]
    for label, selected, expected in (
        ("forbidden", forbidden_cases, "reject"),
        ("clean", clean_cases, "accept"),
    ):
        counts = {
            name: sum(results[case["id"]][0] == name for case in selected) for name in ("accept", "reject", "uncertain")
        }
        lines.append(
            f"- {label}: cases={len(selected)} accepted={counts['accept']} rejected={counts['reject']} "
            f"uncertain={counts['uncertain']} expected={expected}"
        )
    lines.extend(["", "## Per thing", ""])
    for thing in sorted({case["thing"] for case in cases}):
        selected = [case for case in cases if case["thing"] == thing]
        lines.append(
            f"- {thing}: cases={len(selected)} accepted={sum(results[case['id']][0] == 'accept' for case in selected)} "
            f"rejected={sum(results[case['id']][0] == 'reject' for case in selected)} "
            f"uncertain={sum(results[case['id']][0] == 'uncertain' for case in selected)}"
        )
    lines.extend(["", "## Per-case medians", ""])
    for case in cases:
        outcome, median = results[case["id"]]
        median_text = "unavailable" if median is None else f"{median:.6f}"
        lines.append(f"- {case['id']}: {outcome} median={median_text}")
    lines.extend(
        [
            "",
            (
                f"Gate: {verdict} — forbidden rejected {forbidden_rejected}/{len(forbidden_cases)}; "
                f"clean accepted {clean_accepted}/{len(clean_cases)}"
            ),
            f"Verdict: {verdict}",
        ]
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(verdict)
    return verdict


def _error(message: str) -> int:
    print(f"opening condition v2: {message}", file=sys.stderr)
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--blind-sheet", action="store_true")
    modes.add_argument("--freeze-labels", action="store_true")
    modes.add_argument("--build-cases", action="store_true")
    modes.add_argument("--judge", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--capture", nargs="?", const="__capture_mode__")
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--labels", type=Path)
    parser.add_argument("--key", type=Path)
    parser.add_argument("--cases", type=Path)
    parser.add_argument("--samples", type=int)
    parser.add_argument("--max-calls", type=int, default=0)
    parser.add_argument("--max-usd", type=float, default=0.0)
    parser.add_argument("--min-interval-s", type=float, default=0.0)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.capture == "__capture_mode__":
            if args.out is None:
                raise ValueError("--capture requires --out")
            capture(args.out)
            return 0
        if args.run:
            if args.capture in {None, "__capture_mode__"} or args.out is None:
                raise ValueError("--run requires --capture and --out")
            if not args.confirm:
                raise ValueError("run mode requires --confirm")
            document = _read_json(Path(args.capture))
            run_rows(
                document,
                samples=SAMPLES if args.samples is None else args.samples,
                max_calls=args.max_calls,
                max_usd=args.max_usd,
                out=args.out,
            )
            return 0
        if args.blind_sheet:
            if args.rows is None or args.out is None:
                raise ValueError("--blind-sheet requires --rows and --out")
            blind_sheet(args.rows, args.out)
            return 0
        if args.freeze_labels:
            if args.labels is None:
                raise ValueError("--freeze-labels requires --labels")
            freeze_labels(args.labels)
            return 0
        if args.build_cases:
            if args.rows is None or args.labels is None or args.key is None or args.out is None:
                raise ValueError("--build-cases requires --rows, --labels, --key and --out")
            build_cases(args.rows, args.labels, args.key, args.out)
            return 0
        if args.judge:
            if args.cases is None:
                raise ValueError("--judge requires --cases")
            if args.out is None and not args.dry_run:
                raise ValueError("--judge requires --out")
            _code, _text = judge_run(
                args.cases,
                samples=JUDGE_SAMPLES if args.samples is None else args.samples,
                max_calls=args.max_calls,
                max_usd=args.max_usd,
                min_interval_s=args.min_interval_s,
                confirm=args.confirm,
                out=args.out if args.out is not None else Path("/dev/null"),
                dry_run=args.dry_run,
            )
            return 0
        if args.report:
            if args.cases is None or args.rows is None or args.out is None:
                raise ValueError("--report requires --cases, --rows and --out")
            verdict = report_rows(args.cases, args.rows, args.out)
            return 0 if verdict == "PASS" else 1
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))
    return _error("one mode is required")


if __name__ == "__main__":
    raise SystemExit(main())

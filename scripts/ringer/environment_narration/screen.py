"""Offline prompt screen and explicitly gated billed-run harness."""

from __future__ import annotations

import argparse
import difflib
import hashlib
import importlib.util
import json
import math
import os
import shutil
import sys
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType
from typing import Any
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import yaml

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"
WORKER_USER_AGENT = "boarding_probe"
DEFAULT_MAX_CALLS = 366
QUOTA_CODES = ("AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED")
MODELS = (
    "@cf/meta/llama-3.1-8b-instruct-fast",
    "@cf/meta/llama-3.3-70b-instruct-fp8-fast",
    "@cf/deepseek-ai/deepseek-v4.1-flash-1017",
)

# These are the three entries in worker/src/budget.js, read for this screen on
# 2026-10-25.  Prices are dollars per million input/output tokens.
MODEL_PROFILES = {
    MODELS[0]: {"max_tokens": 1024, "input": 0.282, "output": 0.827, "reasoning": False},
    MODELS[1]: {"max_tokens": 1024, "input": 0.293, "output": 2.253, "reasoning": False},
    MODELS[2]: {"max_tokens": 3072, "input": 0.30, "output": 1.20, "reasoning": True},
}


class ScreenError(RuntimeError):
    """A preflight or frozen-fixture error."""


def _jsonable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_jsonable(item) for item in value]
    if hasattr(value, "model_dump"):
        return _jsonable(value.model_dump(mode="json"))
    return repr(value)


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_jsonable(value), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(_jsonable(value), ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def _state_hash(state: Any) -> str:
    facts = {"asserted": [_jsonable(fact) for fact in sorted(state.facts.asserted, key=lambda fact: fact.key)]}
    return hashlib.sha256(_canonical_json(facts)).hexdigest()


def _package_hash(package_root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in package_root.rglob("*") if item.is_file()):
        relative = path.relative_to(package_root).as_posix().encode()
        content = path.read_bytes()
        digest.update(len(relative).to_bytes(8, "big"))
        digest.update(relative)
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def _load_boarding_probe() -> ModuleType:
    path = ROOT / "scripts/ringer/transcript_1a/boarding_probe.py"
    spec = importlib.util.spec_from_file_location("environment_screen_boarding_probe", path)
    if spec is None or spec.loader is None:
        raise ScreenError(f"could not load boarding probe from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _find_named(entries: Any, wanted: str, label: str) -> str:
    matches = [entry.id for entry in entries if str(getattr(entry, "name", "")).casefold() == wanted.casefold()]
    if len(matches) != 1:
        raise ScreenError(f"expected one {label} named {wanted!r}, found {matches}")
    return matches[0]


def _find_item(package: Any, *, name: str | None = None, kind: str | None = None, label: str) -> str:
    matches = []
    for item in package.world.items:
        if name is not None and str(item.name).casefold() != name.casefold():
            continue
        if kind is not None and item.kind != kind:
            continue
        matches.append(item.id)
    if len(matches) != 1:
        raise ScreenError(f"expected one {label}, found {matches}")
    return matches[0]


def _ids(package: Any) -> dict[str, str]:
    return {
        "protagonist": package.world.protagonist_id,
        "outside": _find_named(package.world.locations, "outside the house", "outside location"),
        "kitchen": _find_named(package.world.locations, "kitchen", "kitchen location"),
        "truck": _find_item(package, name="Kristin's truck", kind="vehicle", label="truck"),
        "passenger_seat": _find_item(package, name="passenger seat", kind="seat", label="passenger seat"),
        "laptop": _find_item(package, name="Kristin's laptop", label="laptop"),
        "drawer": _find_item(package, name="drawer", kind="container", label="drawer"),
        "card": _find_item(package, name="Michelle's memory card", label="memory card"),
    }


def _state_at(boarding_probe: ModuleType, package: Any, place_id: str) -> Any:
    return boarding_probe._state_at(package, place_id)


def _assert(condition: bool, message: str) -> None:
    if not condition:
        raise ScreenError(message)


def _copy_package(
    source: Path, target: Path, *, add_view: bool = False, complete_drawer: bool = False, ids: dict[str, str]
) -> None:
    shutil.copytree(source, target)
    world_path = target / "world.yaml"
    world = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    items = world.get("items", [])
    if add_view:
        truck = next((item for item in items if item.get("id") == ids["truck"]), None)
        _assert(truck is not None, "copied package lost the discovered truck")
        truck["view"] = [{"from": ids["outside"]}]
        # Worldkeeper evaluates each enterable ancestor.  The passenger seat
        # is an enterable boundary too, so the same unobstructed window view
        # must be declared on it for a laptop resting on that seat.
        passenger_seat = next((item for item in items if item.get("id") == ids["passenger_seat"]), None)
        _assert(passenger_seat is not None, "copied package lost the passenger seat")
        passenger_seat["view"] = [{"from": ids["outside"]}]
    if complete_drawer:
        drawer = next((item for item in items if item.get("id") == ids["drawer"]), None)
        _assert(drawer is not None, "copied package lost the discovered drawer")
        drawer["contents_complete"] = True
    world_path.write_text(yaml.safe_dump(world, sort_keys=False), encoding="utf-8")


def _assert_start_facts(
    package: Any, place_id: str, start_id: str, ids: dict[str, str], boarding_probe: ModuleType
) -> Any:
    from storygame.runtime.facts import Fact
    from storygame.runtime.world_model import apply_world_effects, world_for

    state = _state_at(boarding_probe, package, place_id)
    world = world_for(package, state.facts)
    if start_id in {"S1", "S2"}:
        passenger = world.parent(ids["laptop"])
        _assert(passenger is not None and world.is_a(passenger, "seat"), f"{start_id} requires laptop in a seat")
        _assert(world.parent(passenger) == ids["truck"], f"{start_id} requires laptop seat inside the truck")
    elif start_id == "S3":
        _assert(world.move(ids["laptop"], ids["protagonist"]).ok, "S3 could not move the laptop to the protagonist")
        _assert(world.parent(ids["laptop"]) == ids["protagonist"], "S3 laptop is not held by the protagonist")
    elif start_id == "S4":
        _assert(world.area(ids["drawer"]) == place_id, "S4 drawer is not in the selected house room")
    elif start_id == "S5":
        state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
        apply_world_effects(package, state.facts)
        world = world_for(package, state.facts)
        _assert(
            world.parent(ids["card"]) == ids["protagonist"],
            "S5 memory card was not recovered into the protagonist's hands",
        )
    elif start_id == "S6":
        _assert(world.area(ids["protagonist"]) == place_id, "S6 protagonist is not in the kitchen area")
    return state


def _ask_for(start_id: str):
    def ask(_state: object, questions: dict[str, object]) -> dict[str, dict[str, float]]:
        boarding = start_id == "S1"
        return {
            key: {
                "noul": float(
                    boarding if key == "boards_vehicle" else boarding if key == "only_boards_vehicle" else False
                )
            }
            for key in questions
        }

    return ask


@contextmanager
def _capture_stubs(boarding_probe: ModuleType, ask: Any) -> Iterator[None]:
    with boarding_probe._stub_jev(), boarding_probe._stub_item_facts():
        yield


def _capture_prompt(
    package: Any,
    place_id: str,
    command: str,
    request: Any | None,
    start_id: str,
    boarding_probe: ModuleType,
    setup: Any,
) -> dict[str, Any]:
    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.cloudflare import CloudflareTurnProvider

    state = _assert_start_facts(package, place_id, start_id, setup["ids"], boarding_probe)
    setup["prepare_state"](state, package)
    before = _state_hash(state)
    with _capture_stubs(boarding_probe, _ask_for(start_id)):
        provider = build_capture_provider(state)
        provider.observation_request = request
        captured: dict[str, str] = {}

        def dispatch(system: str, user: dict[str, object]) -> dict[str, object]:
            captured["system"] = system
            captured["user"] = provider._section_user_prompt(user)
            return {"segments": [], "selected_knowledge_ids": []}

        provider._dispatch = dispatch
        capture = WorldCapture(provider, _ask_for(start_id))
        capture.before_turn(command)
        after = _state_hash(state)
        source = "product"
        engine_text = False
        if start_id == "S2" and request is not None:
            world = provider._world()
            laptop_name = world.name(setup["ids"]["laptop"])
            _assert(
                world.sees(setup["ids"]["protagonist"], setup["ids"]["laptop"]),
                "S2 view declaration did not expose the laptop",
            )
            selected = list(provider._selected_names or ())
            if laptop_name not in selected:
                selected.append(laptop_name)
            provider._selected_names = selected
        if start_id == "S3":
            laptop_name = provider._world().name(setup["ids"]["laptop"])
            selected = list(provider._selected_names or ())
            if laptop_name not in selected:
                selected.append(laptop_name)
            provider._selected_names = selected
        if provider.command_consumed and request is None:
            provider._dispatch = lambda _system, _user: (_ for _ in ()).throw(
                AssertionError("baseline consumed turn unexpectedly dispatched")
            )
            provider(command)
            engine_text = provider.last_turn_engine_text
            provider._dispatch = dispatch
            CloudflareTurnProvider.__call__(provider, command)
            source = "bypass_for_capture"
        elif request is None:
            CloudflareTurnProvider.__call__(provider, command)
        else:
            provider(command)
    _assert("system" in captured and "user" in captured, f"{start_id} did not produce a narrator request")
    return {
        "system": captured["system"],
        "user": captured["user"],
        "state_hash_before": before,
        "state_hash_after_implicit": after,
        "state_hash": after,
        "source": source,
        "engine_text_turn": engine_text,
    }


def _expected(start_id: str, ids: dict[str, str]) -> dict[str, Any]:
    required = []
    if start_id in {"S1", "S2"}:
        required = [{"name": "Kristin's laptop", "place": "passenger seat"}]
    elif start_id == "S3":
        required = [{"name": "Kristin's laptop", "holder": "Kristin"}]
    forbidden = {
        "S1": ["driving", "exit"],
        "S2": ["driving", "exit"],
        "S3": ["passenger seat"],
        "S4": ["Michelle's memory card", "replacement clue"],
        "S5": ["Michelle's memory card", "replacement clue"],
        "S6": ["Kristin's truck"],
    }[start_id]
    return {
        "required": required,
        "forbidden": forbidden,
        "forbidden_notes": {
            "S1": "no driving or exit",
            "S2": "no driving or exit",
            "S5": "no re-found card or replacement clue",
        }.get(start_id, ""),
    }


STARTS = (
    ("S1", "boarding", "Enter the truck.", "enter", "truck", "outside"),
    ("S2", "outside view", "Look through the truck window.", "look", "truck", "outside"),
    ("S3", "moved item", "Examine my laptop.", "look", "laptop", "outside"),
    ("S4", "drawer opening", "Open the drawer.", "open", "drawer", "drawer_area"),
    ("S5", "searched scope after recovery", "Search beneath the drawer.", "look", "drawer", "kitchen"),
    ("S6", "unrelated nearby observation", "Look around.", "look", "kitchen", "kitchen"),
)


def _build_start(boarding_probe: ModuleType, start_spec: tuple[str, ...]) -> dict[str, Any]:
    from storygame.runtime.observation import ObservationRequest
    from storygame.story_package.loader import load_story_package

    start_id, label, command, kind, focus_key, place_key = start_spec
    shipped = load_story_package(PACKAGE_ROOT)
    ids = _ids(shipped)
    shipped_world = __import__("storygame.runtime.world_model", fromlist=["world_for"])
    if place_key == "drawer_area":
        state = _assert_start_facts(shipped, ids["kitchen"], start_id, ids, boarding_probe)
        place_id = shipped_world.world_for(shipped, state.facts).area(ids["drawer"])
        _assert(place_id is not None, "S4 drawer has no containing house room")
    else:
        place_id = ids[place_key]
    focus_id = ids[focus_key]
    request = ObservationRequest(command, kind, focus_id)
    expected = _expected(start_id, ids)

    with TemporaryDirectory(prefix=f"environment-screen-{start_id}-") as temporary:
        temporary_root = Path(temporary)
        copy_path: Path | None = None
        copy_hash = _package_hash(PACKAGE_ROOT)
        if start_id in {"S2", "S5"}:
            copy_path = temporary_root / "package"
            _copy_package(
                PACKAGE_ROOT,
                copy_path,
                add_view=start_id == "S2",
                complete_drawer=start_id == "S5",
                ids=ids,
            )

        def make_setup(package: Any) -> dict[str, Any]:
            package_ids = _ids(package)

            def prepare_state(state: Any, _package: Any) -> None:
                from storygame.runtime.world_model import world_for

                world = world_for(package, state.facts)
                if start_id == "S3":
                    _assert(world.move(package_ids["laptop"], package_ids["protagonist"]).ok, "S3 laptop move failed")
                elif start_id == "S5":
                    from storygame.runtime.facts import Fact
                    from storygame.runtime.world_model import apply_world_effects

                    state.facts.assert_fact(Fact(predicate="memory_card_recovered", subject="story", value="true"))
                    apply_world_effects(package, state.facts)

            return {"ids": package_ids, "prepare_state": prepare_state}

        existing_package = shipped
        proposed_package = load_story_package(copy_path) if copy_path else shipped
        existing_setup = make_setup(existing_package)
        proposed_setup = make_setup(proposed_package)
        existing = _capture_prompt(
            existing_package,
            place_id,
            command,
            None,
            start_id,
            boarding_probe,
            existing_setup,
        )
        proposed = _capture_prompt(
            proposed_package,
            place_id,
            command,
            request,
            start_id,
            boarding_probe,
            proposed_setup,
        )
        if copy_path is not None:
            copy_hash = _package_hash(copy_path)

    _assert(existing["system"] == proposed["system"], f"{start_id} existing/proposed system text differs")
    diff = "".join(
        difflib.unified_diff(
            existing["user"].splitlines(keepends=True),
            proposed["user"].splitlines(keepends=True),
            fromfile=f"{start_id}/existing",
            tofile=f"{start_id}/proposed",
        )
    )
    contexts = {}
    for name, capture in (("existing", existing), ("proposed", proposed)):
        focus_name = next(item.name for item in (*shipped.world.items, *shipped.world.locations) if item.id == focus_id)
        contexts[name] = {
            **capture,
            "package_hash": _package_hash(PACKAGE_ROOT) if name == "existing" else copy_hash,
            "request": {"action": command, "kind": kind, "focus": focus_id, "focus_name": focus_name},
            "expected_observations": expected,
        }
    return {
        "id": start_id,
        "label": label,
        "command": command,
        "place": place_id,
        "request": {"action": command, "kind": kind, "focus": focus_id},
        "package_hashes": {"shipped": _package_hash(PACKAGE_ROOT), "copy": copy_hash},
        "expected_observations": expected,
        "contexts": contexts,
        "user_diff": diff,
    }


def build_document() -> dict[str, Any]:
    boarding_probe = _load_boarding_probe()
    starts = [_build_start(boarding_probe, spec) for spec in STARTS]
    cells = []
    for start in starts:
        for context_name in ("existing", "proposed"):
            context = start["contexts"][context_name]
            for model in MODELS:
                profile = MODEL_PROFILES[model]
                input_tokens = math.ceil(len((context["system"] + context["user"]).encode("utf-8")) / 3)
                ceiling = (input_tokens * profile["input"] + profile["max_tokens"] * profile["output"]) / 1_000_000
                cells.append(
                    {
                        "start": start["id"],
                        "context": context_name,
                        "model": model,
                        "max_tokens": profile["max_tokens"],
                        "reasoning_allowance": profile["reasoning"],
                        "input_tokens_estimate": input_tokens,
                        "ceiling_usd": ceiling,
                    }
                )
    per_cell_total = sum(cell["ceiling_usd"] for cell in cells)
    smoke_cells = [cell for cell in cells if cell["start"] == "S1"]
    smoke_total = sum(cell["ceiling_usd"] for cell in smoke_cells)
    return {
        "schema": 1,
        "mode": "dry",
        "models": list(MODELS),
        "starts": starts,
        "cells": len(cells),
        "cell_costs": cells,
        "cost": {
            "samples": 10,
            "calls": len(cells) * 10,
            "per_cell": cells,
            "ceiling_usd": per_cell_total * 10,
            "smoke": {"calls": 6, "ceiling_usd": smoke_total},
            "estimator": "ceil(utf8_bytes(system + user) / 3)",
        },
    }


def _print_table(document: dict[str, Any], calls: int | None = None, ceiling: float | None = None) -> None:
    cost = document["cost"]
    print(
        f"cells={document['cells']} calls={cost['calls'] if calls is None else calls} "
        f"ceiling_usd=${cost['ceiling_usd'] if ceiling is None else ceiling:.6f} smoke_calls=6 "
        f"smoke_ceiling_usd=${cost['smoke']['ceiling_usd']:.6f}"
    )


def _error(message: str) -> int:
    print(f"environment screen: {message}", file=sys.stderr)
    return 2


def _request_body(context: dict[str, Any]) -> dict[str, Any]:
    return {
        "system": context["system"],
        "user": context["user"],
        "max_tokens": context["max_tokens"],
        "response_format": {"type": "json_object"},
    }


def _headers(response: Any) -> dict[str, str]:
    raw = getattr(response, "headers", {})
    return {str(key): str(value) for key, value in raw.items()} if hasattr(raw, "items") else {}


def _http_error_body(error: HTTPError) -> tuple[str, dict[str, str]]:
    try:
        body = error.read().decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - defensive for malformed transports
        body = str(error)
    return body, _headers(error)


def _parse_reply(raw_response: str) -> tuple[Any, str | None, bool, Any, dict[str, Any] | None]:
    try:
        outer = json.loads(raw_response)
    except json.JSONDecodeError:
        return None, None, False, None, None
    if not isinstance(outer, dict):
        return outer, None, False, None, None
    result = outer.get("result") if isinstance(outer.get("result"), dict) else outer
    echoed = outer.get("model") or result.get("model")
    truncated = bool(outer.get("truncated") or result.get("truncated"))
    usage = outer.get("usage") or result.get("usage")
    raw_reply = outer.get("narration", outer.get("response", result.get("response", result)))
    reply = raw_reply
    if isinstance(raw_reply, str):
        try:
            reply = json.loads(raw_reply)
        except json.JSONDecodeError:
            reply = raw_reply
    if isinstance(reply, dict) and isinstance(reply.get("segments"), list):
        narration = (
            "\n\n".join(
                str(segment.get("text", ""))
                for segment in reply["segments"]
                if isinstance(segment, dict) and segment.get("text")
            )
            or None
        )
        usable = bool(narration)
    elif isinstance(reply, str):
        narration = reply.strip() or None
        usable = bool(narration)
    else:
        narration = None
        usable = False
    return raw_reply, narration, usable, usage, {"outer": outer, "echoed_model": echoed, "truncated": truncated}


def _body_code(text: str) -> str | None:
    for code in (*QUOTA_CODES, "BENCH_MODEL_REJECTED"):
        if code in text:
            return code
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return None
    if isinstance(value, dict):
        for key in ("code", "error", "error_code", "message", "detail"):
            candidate = value.get(key, "")
            candidate_text = (
                json.dumps(candidate, ensure_ascii=False) if isinstance(candidate, (dict, list)) else str(candidate)
            )
            if code := _body_code(candidate_text):
                return code
    return None


def _call(url: str, token: str, model: str, context: dict[str, Any]) -> dict[str, Any]:
    body = _request_body(context)
    request_bytes = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": WORKER_USER_AGENT,
        "X-Bench-Model": model,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(url, data=request_bytes, headers=headers, method="POST")
    started = time.perf_counter()
    try:
        with urlopen(request, timeout=float(os.environ.get("CLOUDFLARE_TIMEOUT", "15"))) as response:  # noqa: S310
            raw_bytes = response.read()
            status = int(getattr(response, "status", getattr(response, "code", 200)))
            response_headers = _headers(response)
    except HTTPError as error:
        raw_text, response_headers = _http_error_body(error)
        status = int(error.code)
        raw_bytes = raw_text.encode("utf-8", errors="replace")
    except Exception as error:  # one answered attempt, never a retry
        raw_text = f"{type(error).__name__}: {error}"
        return {
            "status": None,
            "raw_response": raw_text,
            "raw_reply": None,
            "narration": None,
            "usable": False,
            "truncated": False,
            "echoed_model": None,
            "headers": {},
            "worker_revision": None,
            "latency_ms": round((time.perf_counter() - started) * 1000, 3),
            "request_bytes": len(request_bytes),
            "response_bytes": len(raw_text.encode()),
            "usage": None,
            "error": raw_text,
        }
    raw_text = raw_bytes.decode("utf-8", errors="replace")
    raw_reply, narration, usable, usage, parsed = _parse_reply(raw_text)
    worker_revision = next(
        (value for key, value in response_headers.items() if key.casefold() == "x-worker-revision"),
        None,
    )
    return {
        "status": status,
        "raw_response": raw_text,
        "raw_reply": raw_reply,
        "narration": narration,
        "usable": usable and status is not None and 200 <= status < 300,
        "truncated": bool(parsed and parsed["truncated"]),
        "echoed_model": parsed["echoed_model"] if parsed else None,
        "headers": response_headers,
        "worker_revision": worker_revision,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "request_bytes": len(request_bytes),
        "response_bytes": len(raw_bytes),
        "usage": usage,
    }


def _live_result(document: dict[str, Any], *, samples: int, smoke: bool, max_calls: int, out: Path) -> dict[str, Any]:
    cells = [cell for cell in document["cell_costs"] if not smoke or cell["start"] == "S1"]
    planned_calls = len(cells) if smoke else len(cells) * samples
    if planned_calls > max_calls:
        raise ScreenError(f"estimated calls {planned_calls} exceed --max-calls {max_calls}")
    result: dict[str, Any] = {
        "schema": 1,
        "mode": "smoke" if smoke else "run",
        "invalid": False,
        "stop_reason": None,
        "calls_planned": planned_calls,
        "calls_made": 0,
        "starts": document["starts"],
        "models": document["models"],
        "rows": [],
        "cost": document["cost"],
    }
    _write_json(out, result)
    url = os.environ["CLOUDFLARE_WORKER_URL"].strip()
    token = os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip()
    sequence = range(1) if smoke else range(samples)
    for sample in sequence:
        for cell in cells:
            start = next(item for item in document["starts"] if item["id"] == cell["start"])
            context = start["contexts"][cell["context"]]
            request_context = {**context, "max_tokens": cell["max_tokens"]}
            row = {
                "start": cell["start"],
                "context": cell["context"],
                "model": cell["model"],
                "sample": sample,
                "requested_model": cell["model"],
            }
            response = _call(url, token, cell["model"], request_context)
            row.update(response)
            result["calls_made"] += 1
            code = _body_code(str(response.get("raw_response", "")))
            if response.get("status") == 429 and code in QUOTA_CODES:
                result["stop_reason"] = code
            elif code == "BENCH_MODEL_REJECTED":
                result["stop_reason"] = code
                result["invalid"] = True
            elif 200 <= int(response.get("status") or 0) < 300 and response.get("echoed_model") != cell["model"]:
                result["stop_reason"] = "MODEL_ECHO_MISMATCH"
                result["invalid"] = True
            result["rows"].append(row)
            _write_json(out, result)
            if result["stop_reason"]:
                return result
    return result


def _count_report(rows: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "usable": sum(bool(row.get("usable")) for row in rows),
        "unusable": sum(row.get("usable") is False for row in rows),
        "errors": sum(row.get("status") is None or not (200 <= int(row.get("status", 0)) < 300) for row in rows),
        "truncated": sum(bool(row.get("truncated")) for row in rows),
    }


def _usage_number(usage: dict[str, Any], *names: str) -> float:
    for name in names:
        if usage.get(name) is not None:
            return float(usage[name] or 0)
    return 0.0


def _report(rows_path: Path, out: Path) -> None:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows", [])
    counts = _count_report(rows)
    lines = [
        "# Environment narration screen report",
        "",
        "## Summary",
        "",
        "| usable | unusable | errors | truncated |",
        "| ---: | ---: | ---: | ---: |",
        f"| {counts['usable']} | {counts['unusable']} | {counts['errors']} | {counts['truncated']} |",
        "",
    ]
    usages = [row.get("usage") for row in rows if isinstance(row.get("usage"), dict)]
    if usages:
        input_tokens = sum(_usage_number(usage, "prompt_tokens", "input_tokens") for usage in usages)
        output_tokens = sum(_usage_number(usage, "completion_tokens", "output_tokens") for usage in usages)
        observed_usd = sum(
            (
                _usage_number(row["usage"], "prompt_tokens", "input_tokens")
                * MODEL_PROFILES.get(row.get("model"), {}).get("input", 0)
                + _usage_number(row["usage"], "completion_tokens", "output_tokens")
                * MODEL_PROFILES.get(row.get("model"), {}).get("output", 0)
            )
            / 1_000_000
            for row in rows
            if isinstance(row.get("usage"), dict)
        )
        lines.extend(
            [
                f"Observed token cost: ${observed_usd:.6f} ({input_tokens:g} input, {output_tokens:g} output tokens).",
                "",
                "```json",
                json.dumps(usages, indent=2, ensure_ascii=False),
                "```",
                "",
            ]
        )
    starts = document.get("starts", [])
    start_meta = {start.get("id"): start for start in starts}
    for start_id in sorted({row.get("start") for row in rows}, key=lambda value: str(value)):
        meta = start_meta.get(start_id, {})
        lines.extend([f"## {start_id} — {meta.get('label', '')}", ""])
        expected = meta.get("expected_observations", {})
        lines.append("Hand-scoring checklist:")
        for item in expected.get("required", []):
            lines.append(f"- [ ] Required: {item}")
        for item in expected.get("forbidden", []):
            lines.append(f"- [ ] Forbidden: {item}")
        lines.append("")
        for context in ("existing", "proposed"):
            lines.extend([f"### {context}", ""])
            for row in [item for item in rows if item.get("start") == start_id and item.get("context") == context]:
                state = "usable" if row.get("usable") else "unusable"
                lines.extend(
                    [
                        f"#### {row.get('model')} — sample {row.get('sample')}",
                        "",
                        f"- Status: {row.get('status')}; {state}; latency {row.get('latency_ms')} ms",
                        "",
                        "Narration:",
                        "",
                        str(row.get("narration") or "(none)"),
                        "",
                        "Raw response:",
                        "",
                        "```",
                        str(row.get("raw_response", "")),
                        "```",
                        "",
                    ]
                )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--dry", action="store_true")
    modes.add_argument("--smoke", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--out", type=Path)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--max-calls", type=int, default=DEFAULT_MAX_CALLS)
    parser.add_argument("--max-usd", type=float)
    parser.add_argument("--confirm", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    if args.report:
        if args.rows is None or args.out is None:
            return _error("--report requires --rows and --out")
        _report(args.rows, args.out)
        print(f"report: {args.out}")
        return 0
    if args.out is None:
        return _error("--out is required")
    if args.samples < 1:
        return _error("--samples must be positive")
    try:
        if args.dry:
            document = build_document()
            document["cost"]["samples"] = args.samples
            document["cost"]["calls"] = document["cells"] * args.samples
            document["cost"]["ceiling_usd"] = sum(cell["ceiling_usd"] for cell in document["cell_costs"]) * args.samples
            _write_json(args.out, document)
            _print_table(document)
            return 0
        if not args.confirm:
            return _error("live mode requires --confirm")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("live mode requires CLOUDFLARE_WORKER_URL")
        smoke = args.smoke
        planned = 6 if smoke else 36 * args.samples
        if args.run and args.max_usd is None:
            return _error("--run requires --max-usd")
        if args.max_calls < planned:
            return _error(f"estimated calls {planned} exceed --max-calls {args.max_calls}")
        document = build_document()
        ceiling = (
            document["cost"]["smoke"]["ceiling_usd"]
            if smoke
            else sum(cell["ceiling_usd"] for cell in document["cell_costs"]) * args.samples
        )
        if args.max_usd is not None and ceiling > args.max_usd:
            return _error(f"estimated ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        document["cost"]["samples"] = 1 if smoke else args.samples
        document["cost"]["calls"] = planned
        document["cost"]["ceiling_usd"] = ceiling
        result = _live_result(document, samples=args.samples, smoke=smoke, max_calls=args.max_calls, out=args.out)
        _print_table(document, calls=result["calls_made"], ceiling=ceiling)
        return 0
    except (ScreenError, OSError, ValueError, yaml.YAMLError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

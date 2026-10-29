"""Probe Jev's scope-aware underneath-search question on frozen player commands."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from storygame.runtime.jev import JevClient
from storygame.runtime.jev_questions import searches_underneath

REPO_DIR = Path(__file__).resolve().parents[3]
PROBE_DIR = Path(__file__).with_name("under_probe")
CASES_PATH = PROBE_DIR / "cases.jsonl"
LOCK_PATH = PROBE_DIR / "cases.lock.json"
V2_PROBE_DIR = Path(__file__).with_name("under_probe_v2")
V2_CASES_PATH = V2_PROBE_DIR / "cases.jsonl"
V2_LOCK_PATH = V2_PROBE_DIR / "cases.lock.json"
V4_PROBE_DIR = Path(__file__).with_name("under_probe_v4")
V4_CASES_PATH = V4_PROBE_DIR / "cases.jsonl"
V4_LOCK_PATH = V4_PROBE_DIR / "cases.lock.json"
DEFAULT_SAMPLES = 2
DEFAULT_MAX_CALLS = 98
V2_DEFAULT_MAX_CALLS = 128
V4_DEFAULT_MAX_CALLS = 48
DEFAULT_MAX_USD = 0.01
COST_PER_MILLION_INPUT_TOKENS = 0.042
WILSON_Z = 1.6448536269514722

FROZEN_CASES = [
    {"id": "u-p01", "command": "Feel under the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p02", "command": "Search beneath the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p03", "command": "Look under the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p04", "command": "Check below the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p05", "command": "Run my hand under the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p06", "command": "Reach beneath the drawer.", "thing": "drawer", "expected": True},
    {"id": "u-p07", "command": "Feel under the passenger seat.", "thing": "passenger seat", "expected": True},
    {"id": "u-p08", "command": "Look under the passenger seat.", "thing": "passenger seat", "expected": True},
    {"id": "u-p09", "command": "Search beneath the passenger seat.", "thing": "passenger seat", "expected": True},
    {"id": "u-p10", "command": "Check under the driver's seat.", "thing": "driver's seat", "expected": True},
    {"id": "u-p11", "command": "Feel under the desk.", "thing": "desk", "expected": True},
    {"id": "u-p12", "command": "Search under the bed.", "thing": "bed", "expected": True},
    {"id": "u-p13", "command": "Look beneath the tray.", "thing": "telescope tray", "expected": True},
    {"id": "u-p14", "command": "Feel under the telescope tray.", "thing": "telescope tray", "expected": True},
    {"id": "u-p15", "command": "Check under the bench.", "thing": "skiff bench", "expected": True},
    {"id": "u-p16", "command": "Reach under the locker.", "thing": "locker", "expected": True},
    {"id": "u-p17", "command": "Search below the workbench.", "thing": "workbench", "expected": True},
    {"id": "u-p18", "command": "Look under the crate.", "thing": "crate", "expected": True},
    {"id": "u-p19", "command": "Feel beneath the table.", "thing": "table", "expected": True},
    {"id": "u-p20", "command": "Slide my hand under the shelf.", "thing": "shelf", "expected": True},
    {"id": "u-n01", "command": "Inspect the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n02", "command": "Open the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n03", "command": "Pull out the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n04", "command": "Search the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n05", "command": "Feel inside the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n06", "command": "Look inside the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n07", "command": "Close the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n08", "command": "Look behind the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n09", "command": "Check the top of the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n10", "command": "Take the pens from the drawer.", "thing": "drawer", "expected": False},
    {"id": "u-n11", "command": "Inspect the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n12", "command": "Sit on the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n13", "command": "Search the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n14", "command": "Put my laptop on the passenger seat.", "thing": "passenger seat", "expected": False},
    {"id": "u-n15", "command": "Look at the driver's seat.", "thing": "driver's seat", "expected": False},
    {"id": "u-n16", "command": "Inspect the telescope tray.", "thing": "telescope tray", "expected": False},
    {"id": "u-n17", "command": "Look in the locker.", "thing": "locker", "expected": False},
    {"id": "u-n18", "command": "Open the crate.", "thing": "crate", "expected": False},
    {"id": "u-n19", "command": "Examine the bench.", "thing": "skiff bench", "expected": False},
    {"id": "u-n20", "command": "Search the table.", "thing": "table", "expected": False},
    {"id": "u-n21", "command": "Clear the desk.", "thing": "desk", "expected": False},
    {"id": "u-n22", "command": "Check on top of the shelf.", "thing": "shelf", "expected": False},
    {"id": "u-n23", "command": "Look behind the bed.", "thing": "bed", "expected": False},
    {"id": "u-n24", "command": "Search the workbench.", "thing": "workbench", "expected": False},
    {"id": "u-n25", "command": "Wipe the table.", "thing": "table", "expected": False},
    {"id": "u-n26", "command": "Push the chair under the desk.", "thing": "chair", "expected": False, "hard": True},
    {"id": "u-n27", "command": "Slide the tray under the telescope.", "thing": "tray", "expected": False, "hard": True},
    {"id": "u-n28", "command": "Lift the crate.", "thing": "crate", "expected": False},
    {"id": "u-n29", "command": "Read the label on the locker.", "thing": "locker", "expected": False},
]

V2_FROZEN_CASES = [
    {"id": "v-p01", "command": "Feel under the cabinet.", "thing": "cabinet", "expected": True, "kind": "fresh"},
    {"id": "v-p02", "command": "Search under the cot.", "thing": "cot", "expected": True, "kind": "fresh"},
    {"id": "v-p03", "command": "Look under the dashboard.", "thing": "dashboard", "expected": True, "kind": "fresh"},
    {"id": "v-p04", "command": "Check beneath the rug.", "thing": "rug", "expected": True, "kind": "fresh"},
    {"id": "v-p05", "command": "Reach under the sofa.", "thing": "sofa", "expected": True, "kind": "fresh"},
    {"id": "v-p06", "command": "Feel beneath the mattress.", "thing": "mattress", "expected": True, "kind": "fresh"},
    {
        "id": "v-p07",
        "command": "Run my fingers under the counter.",
        "thing": "counter",
        "expected": True,
        "kind": "fresh",
    },
    {"id": "v-p08", "command": "Peer beneath the console.", "thing": "console", "expected": True, "kind": "fresh"},
    {"id": "v-p09", "command": "Sweep my hand under the bunk.", "thing": "bunk", "expected": True, "kind": "fresh"},
    {"id": "v-p10", "command": "Search underneath the cabinet.", "thing": "cabinet", "expected": True, "kind": "fresh"},
    {"id": "v-p11", "command": "Look underneath the truck.", "thing": "truck", "expected": True, "kind": "fresh"},
    {"id": "v-p12", "command": "Check below the desk.", "thing": "desk", "expected": True, "kind": "fresh"},
    {
        "id": "v-p13",
        "command": "Feel along the underside of the table.",
        "thing": "table",
        "expected": True,
        "kind": "fresh",
    },
    {
        "id": "v-p14",
        "command": "Examine the underside of the drawer.",
        "thing": "drawer",
        "expected": True,
        "kind": "fresh",
    },
    {
        "id": "v-p15",
        "command": "Inspect beneath the workbench.",
        "thing": "workbench",
        "expected": True,
        "kind": "fresh",
    },
    {"id": "v-p16", "command": "Examine under the seat.", "thing": "seat", "expected": True, "kind": "fresh"},
    {"id": "v-p17", "command": "Search beneath the pillow.", "thing": "pillow", "expected": True, "kind": "fresh"},
    {"id": "v-p18", "command": "Reach below the shelf.", "thing": "shelf", "expected": True, "kind": "fresh"},
    {"id": "v-p19", "command": "Look under the lantern.", "thing": "lantern", "expected": True, "kind": "fresh"},
    {"id": "v-p20", "command": "Feel beneath the bench.", "thing": "bench", "expected": True, "kind": "fresh"},
    {
        "id": "v-p21",
        "command": "Search under the driver's seat.",
        "thing": "driver's seat",
        "expected": True,
        "kind": "fresh",
    },
    {"id": "v-p22", "command": "Slide my arm under the bed.", "thing": "bed", "expected": True, "kind": "fresh"},
    {"id": "v-p23", "command": "Check under the cooler.", "thing": "cooler", "expected": True, "kind": "fresh"},
    {"id": "v-p24", "command": "Peek beneath the tarp.", "thing": "tarp", "expected": True, "kind": "fresh"},
    {"id": "v-n01", "command": "Search the cabinet.", "thing": "cabinet", "expected": False, "kind": "fresh"},
    {"id": "v-n02", "command": "Check the cot.", "thing": "cot", "expected": False, "kind": "fresh"},
    {"id": "v-n03", "command": "Examine the dashboard.", "thing": "dashboard", "expected": False, "kind": "fresh"},
    {"id": "v-n04", "command": "Inspect the rug.", "thing": "rug", "expected": False, "kind": "fresh"},
    {"id": "v-n05", "command": "Search the sofa.", "thing": "sofa", "expected": False, "kind": "fresh"},
    {"id": "v-n06", "command": "Check the mattress.", "thing": "mattress", "expected": False, "kind": "fresh"},
    {"id": "v-n07", "command": "Examine the counter.", "thing": "counter", "expected": False, "kind": "fresh"},
    {"id": "v-n08", "command": "Search the console.", "thing": "console", "expected": False, "kind": "fresh"},
    {"id": "v-n09", "command": "Search the bunk.", "thing": "bunk", "expected": False, "kind": "fresh"},
    {"id": "v-n10", "command": "Check the truck.", "thing": "truck", "expected": False, "kind": "fresh"},
    {"id": "v-n11", "command": "Examine the desk.", "thing": "desk", "expected": False, "kind": "fresh"},
    {"id": "v-n12", "command": "Inspect the seat.", "thing": "seat", "expected": False, "kind": "fresh"},
    {"id": "v-n13", "command": "Search the cooler.", "thing": "cooler", "expected": False, "kind": "fresh"},
    {"id": "v-n14", "command": "Check the lantern.", "thing": "lantern", "expected": False, "kind": "fresh"},
    {"id": "v-n15", "command": "Look inside the cabinet.", "thing": "cabinet", "expected": False, "kind": "fresh"},
    {"id": "v-n16", "command": "Search inside the console.", "thing": "console", "expected": False, "kind": "fresh"},
    {"id": "v-n17", "command": "Look behind the sofa.", "thing": "sofa", "expected": False, "kind": "fresh"},
    {"id": "v-n18", "command": "Check behind the dashboard.", "thing": "dashboard", "expected": False, "kind": "fresh"},
    {"id": "v-n19", "command": "Look on top of the cabinet.", "thing": "cabinet", "expected": False, "kind": "fresh"},
    {
        "id": "v-n20",
        "command": "Feel along the top of the counter.",
        "thing": "counter",
        "expected": False,
        "kind": "fresh",
    },
    {"id": "v-n21", "command": "Check the back of the bunk.", "thing": "bunk", "expected": False, "kind": "fresh"},
    {"id": "v-n22", "command": "Reach into the cooler.", "thing": "cooler", "expected": False, "kind": "fresh"},
    {"id": "v-n23", "command": "Open the cabinet.", "thing": "cabinet", "expected": False, "kind": "fresh"},
    {"id": "v-n24", "command": "Sit on the mattress.", "thing": "mattress", "expected": False, "kind": "fresh"},
    {"id": "v-n25", "command": "Vacuum the rug.", "thing": "rug", "expected": False, "kind": "fresh"},
    {"id": "v-n26", "command": "Carry the cot.", "thing": "cot", "expected": False, "kind": "fresh"},
    {"id": "v-n27", "command": "Push the sofa against the wall.", "thing": "sofa", "expected": False, "kind": "fresh"},
    {"id": "v-n28", "command": "Close the cooler.", "thing": "cooler", "expected": False, "kind": "fresh"},
    {
        "id": "v-n29",
        "command": "Push the bunk under the window.",
        "thing": "bunk",
        "expected": False,
        "kind": "fresh",
        "hard": True,
    },
    {
        "id": "v-n30",
        "command": "Park the truck under the tree.",
        "thing": "truck",
        "expected": False,
        "kind": "fresh",
        "hard": True,
    },
    {"id": "v-n31", "command": "Wipe the counter.", "thing": "counter", "expected": False, "kind": "fresh"},
    {"id": "v-n32", "command": "Read the label on the tarp.", "thing": "tarp", "expected": False, "kind": "fresh"},
    {"id": "v-n33", "command": "Take the lantern.", "thing": "lantern", "expected": False, "kind": "fresh"},
    {"id": "v-n34", "command": "Sit on the bench.", "thing": "bench", "expected": False, "kind": "fresh"},
    {"id": "v-n35", "command": "Shake out the pillow.", "thing": "pillow", "expected": False, "kind": "fresh"},
    {"id": "v-n36", "command": "Polish the lantern.", "thing": "lantern", "expected": False, "kind": "fresh"},
    {"id": "v-r1", "command": "Search the drawer.", "thing": "drawer", "expected": False, "kind": "regression"},
    {
        "id": "v-r2",
        "command": "Search the passenger seat.",
        "thing": "passenger seat",
        "expected": False,
        "kind": "regression",
    },
    {"id": "v-r3", "command": "Search the workbench.", "thing": "workbench", "expected": False, "kind": "regression"},
    {"id": "v-r4", "command": "Search the table.", "thing": "table", "expected": False, "kind": "regression"},
]

V4_FROZEN_CASES = [
    {
        "id": "us01",
        "command": "Look under the workstation.",
        "thing": "workstation",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us02",
        "command": "Search under the park bench.",
        "thing": "park bench",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us03",
        "command": "Check beneath the executive desk.",
        "thing": "executive desk",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us04",
        "command": "Feel under the sofa.",
        "thing": "sofa",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us05",
        "command": "Look under the coffee table.",
        "thing": "coffee table",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us06",
        "command": "Inspect underneath the bed.",
        "thing": "bed",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us07",
        "command": "Look beneath the bookshelf.",
        "thing": "bookshelf",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us08",
        "command": "Search under the chair.",
        "thing": "chair",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us09",
        "command": "Check under the stool.",
        "thing": "stool",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us10",
        "command": "Feel beneath the counter.",
        "thing": "counter",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us11",
        "command": "Look under the picnic table.",
        "thing": "picnic table",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "us12",
        "command": "Examine below the bench.",
        "thing": "bench",
        "question": "searches_underneath",
        "expected": True,
        "label": "US",
    },
    {
        "id": "ub01",
        "command": "Inspect the workstation.",
        "thing": "workstation",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub02",
        "command": "Search the park bench.",
        "thing": "park bench",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub03",
        "command": "Examine the executive desk.",
        "thing": "executive desk",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub04",
        "command": "Check the sofa.",
        "thing": "sofa",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub05",
        "command": "Look at the coffee table.",
        "thing": "coffee table",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub06",
        "command": "Inspect the bed.",
        "thing": "bed",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub07",
        "command": "Search the bookshelf.",
        "thing": "bookshelf",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub08",
        "command": "Examine the chair.",
        "thing": "chair",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub09",
        "command": "Check the stool.",
        "thing": "stool",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub10",
        "command": "Look at the counter.",
        "thing": "counter",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub11",
        "command": "Search the picnic table.",
        "thing": "picnic table",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
    {
        "id": "ub12",
        "command": "Inspect the bench.",
        "thing": "bench",
        "question": "searches_underneath",
        "expected": False,
        "label": "UB",
    },
]


def _credential_values() -> tuple[str, ...]:
    names = (
        "CLOUDFLARE_WORKER_TOKEN",
        "CLOUDFLARE_AI_TOKEN",
        "CLOUDFLARE_ACCOUNT_ID",
        "OPENAI_API_KEY",
        "RAILWAY_TOKEN",
        "RAILWAY_PROJECT_ID",
        "FREYTAG_TEST_CLOCK_TOKEN",
    )
    values = [os.environ.get(name, "").strip() for name in names]
    return tuple(sorted({value for value in values if value}, key=len, reverse=True))


def _redact(value: str) -> str:
    for secret in _credential_values():
        value = value.replace(secret, "[REDACTED]")
    return value


def _write_json(path: Path, document: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    path.write_text(_redact(text), encoding="utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _cases_bytes(cases: list[dict[str, Any]] | tuple[dict[str, Any], ...]) -> bytes:
    return "".join(json.dumps(case, ensure_ascii=False, separators=(",", ":")) + "\n" for case in cases).encode("utf-8")


def _corpus_paths(corpus: str) -> tuple[Path, Path]:
    if corpus == "v1":
        return CASES_PATH, LOCK_PATH
    if corpus == "v2":
        return V2_CASES_PATH, V2_LOCK_PATH
    if corpus == "v4":
        return V4_CASES_PATH, V4_LOCK_PATH
    raise ValueError(f"unknown corpus: {corpus}")


def _corpus_literal(corpus: str) -> list[dict[str, Any]]:
    if corpus == "v1":
        return FROZEN_CASES
    if corpus == "v2":
        return V2_FROZEN_CASES
    if corpus == "v4":
        return V4_FROZEN_CASES
    raise ValueError(f"unknown corpus: {corpus}")


def _corpus_max_calls(corpus: str) -> int:
    if corpus == "v1":
        return DEFAULT_MAX_CALLS
    if corpus == "v2":
        return V2_DEFAULT_MAX_CALLS
    if corpus == "v4":
        return V4_DEFAULT_MAX_CALLS
    raise ValueError(f"unknown corpus: {corpus}")


def build_cases(corpus: str = "v1") -> list[dict[str, Any]]:
    """Return the preregistered cases from the literal frozen list."""
    return [dict(case) for case in _corpus_literal(corpus)]


def _write_cases(cases: list[dict[str, Any]], corpus: str = "v1") -> None:
    data = _cases_bytes(cases)
    cases_path, lock_path = _corpus_paths(corpus)
    cases_path.parent.mkdir(parents=True, exist_ok=True)
    cases_path.write_bytes(data)
    _write_json(lock_path, {"sha256": _sha256(data), "count": len(cases)})


def _load_cases(path: Path | None = None, corpus: str = "v1") -> list[dict[str, Any]]:
    source = _corpus_paths(corpus)[0] if path is None else path
    try:
        lines = source.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError as error:
        raise ValueError(f"cases.jsonl is missing: {source}") from error
    cases: list[dict[str, Any]] = []
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
        raise ValueError(f"cases.jsonl has no cases: {source}")
    return cases


def _lock_matches(
    cases: list[dict[str, Any]],
    cases_path: Path | None = None,
    lock_path: Path | None = None,
    corpus: str = "v1",
) -> bool:
    default_cases_path, default_lock_path = _corpus_paths(corpus)
    source = default_cases_path if cases_path is None else cases_path
    lock_source = default_lock_path if lock_path is None else lock_path
    try:
        lock = json.loads(lock_source.read_text(encoding="utf-8"))
        data = source.read_bytes()
    except (OSError, json.JSONDecodeError):
        return False
    return lock == {"sha256": _sha256(data), "count": len(cases)}


def recording_ask(client: object, records: list[dict[str, Any]]):
    """Wrap a Jev client ask while preserving its raw answer and response metadata."""

    def ask(state: object, questions: object) -> dict | None:
        raw_answer: dict | None = None
        try:
            raw_answer = client.ask(state, questions)
            return raw_answer
        finally:
            records.append(
                {
                    "raw_answer": raw_answer,
                    "jev_model": _client_model(client),
                    "status": getattr(client, "last_status", None),
                }
            )

    return ask


def _client_model(client: object) -> str | None:
    for name in ("last_model", "model", "model_header"):
        value = getattr(client, name, None)
        if isinstance(value, str) and value:
            return value
    return None


def _score(raw_answer: object) -> object:
    if not isinstance(raw_answer, dict):
        return None
    answer = raw_answer.get("searches_underneath")
    return answer.get("noul") if isinstance(answer, dict) else None


def _status_stop_reason(client: object) -> str | None:
    status = getattr(client, "last_status", None)
    if not isinstance(status, int):
        return None
    if status == 429:
        return "http_429"
    if status in {401, 403}:
        return "auth_failure"
    if status >= 500:
        return f"http_{status}"
    if status >= 400:
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
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    if max_calls < 1:
        raise ValueError("--max-calls must be at least 1")
    calls = [(case, sample) for sample in range(samples) for case in cases]
    document: dict[str, Any] = {
        "schema": 1,
        "mode": "run",
        "calls_planned": len(calls),
        "rows": [],
        "stop_reason": None,
    }
    for call_index, (case, sample) in enumerate(calls[:max_calls], start=1):
        records: list[dict[str, Any]] = []
        started = time.perf_counter()
        returned = searches_underneath(
            recording_ask(client, records),
            case["command"],
            case["thing"],
        )
        latency_ms = (time.perf_counter() - started) * 1000
        record = records[-1] if records else {}
        raw_answer = record.get("raw_answer")
        row = {
            "call_index": call_index,
            "case_id": case["id"],
            "command": case["command"],
            "thing": case["thing"],
            "expected": case["expected"],
            "sample": sample,
            "returned": returned,
            "answer": returned,
            "noul": _score(raw_answer),
            "score": _score(raw_answer),
            "raw_answer": raw_answer,
            "jev_model": record.get("jev_model"),
            "latency_ms": latency_ms,
        }
        document["rows"].append(row)
        stop_reason = _status_stop_reason(client)
        if stop_reason is None and len(document["rows"]) >= max_calls:
            stop_reason = "max_calls"
        if stop_reason is not None:
            document["stop_reason"] = stop_reason
        _write_json(out, document)
        if stop_reason is not None:
            break
    if document["stop_reason"] is None and len(document["rows"]) == len(calls):
        document["stop_reason"] = "completed"
        _write_json(out, document)
    return document


def _estimate_tokens(cases: list[dict[str, Any]], samples: int) -> float:
    chars = sum(
        len(json.dumps({"command": case["command"], "thing": case["thing"]}, ensure_ascii=False, separators=(",", ":")))
        for case in cases
    )
    return chars * samples / 4


def _ceiling(cases: list[dict[str, Any]], samples: int) -> float:
    return _estimate_tokens(cases, samples) / 1_000_000 * COST_PER_MILLION_INPUT_TOKENS * 1.5


def _print_dry_run(cases: list[dict[str, Any]], samples: int) -> None:
    if samples < 1:
        raise ValueError("--samples must be at least 1")
    print(f"case count: {len(cases)}")
    print(f"planned requests: {len(cases) * samples}")
    print(f"token estimate: {_estimate_tokens(cases, samples):.2f}")
    print(f"USD ceiling: ${_ceiling(cases, samples):.6f}")


def _display(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _wilson_upper(successes: int, trials: int) -> float | None:
    if trials < 1:
        return None
    proportion = successes / trials
    adjustment = WILSON_Z * WILSON_Z / trials
    numerator = (
        proportion
        + adjustment / 2
        + WILSON_Z * (proportion * (1 - proportion) / trials + adjustment * adjustment / 4) ** 0.5
    )
    return numerator / (1 + adjustment)


def _report_text(rows: list[dict[str, Any]], rows_sha256: str) -> tuple[str, bool]:
    frozen = {case["id"]: case for case in FROZEN_CASES}
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(str(row.get("case_id")), []).append(row)
    negative_rows = [row for row in rows if frozen.get(row.get("case_id"), {}).get("expected") is False]
    positive_rows = [row for row in rows if frozen.get(row.get("case_id"), {}).get("expected") is True]
    negative_true = sum(row.get("returned") is True for row in negative_rows)
    positive_true = sum(row.get("returned") is True for row in positive_rows)
    null_answers = sum(row.get("returned") is None for row in rows)
    j1 = len(negative_rows) == 58 and negative_true == 0
    j2 = len(positive_rows) == 40 and positive_true >= 36
    bound = _wilson_upper(negative_true, len(negative_rows))
    bound_text = "n/a" if bound is None else f"{bound * 100:.2f}%"

    lines = [
        "# Under question probe report",
        "",
        f"Rows sha256: {rows_sha256}",
        f"Rows rendered: {len(rows)}",
        f"null answers: {null_answers}",
        "",
        "## Per-case results",
        "",
        "| Case | Command | Expected | Sample answers and scores |",
        "| --- | --- | ---: | --- |",
    ]
    for case in FROZEN_CASES:
        case_rows = sorted(by_case.get(case["id"], []), key=lambda row: row.get("sample", 0))
        samples_text = (
            ", ".join(
                f"{row.get('sample')}: {_display(row.get('returned'))} ({_display(row.get('noul'))})"
                for row in case_rows
            )
            or "—"
        )
        lines.append(f"| {case['id']} | {case['command']} | {_display(case['expected'])} | {samples_text} |")

    missed_positive = [row for row in positive_rows if row.get("returned") is not True]
    true_negative = [row for row in negative_rows if row.get("returned") is True]
    lines.extend(
        [
            "",
            "## Gate P",
            "",
            f"- J1: {'PASS' if j1 else 'FAIL'} — true answers among negative samples: {negative_true} of 58; "
            f"one-sided 95% Wilson upper bound: {bound_text}",
            f"- J2: {'PASS' if j2 else 'FAIL'} — true answers among positive samples: {positive_true} of 40 "
            "(required at least 36)",
            "",
            "### Missed positives",
            "",
        ]
    )
    if missed_positive:
        lines.extend(
            f"- {row.get('case_id')} sample {row.get('sample')}: score {_display(row.get('noul'))}"
            for row in missed_positive
        )
    else:
        lines.append("- none")
    lines.extend(["", "### True negatives", ""])
    if true_negative:
        lines.extend(
            f"- {row.get('case_id')} sample {row.get('sample')}: score {_display(row.get('noul'))}"
            for row in true_negative
        )
    else:
        lines.append("- none")
    lines.extend(["", f"probe gate: {'PASS' if j1 and j2 else 'FAIL'}", ""])
    return "\n".join(lines), j1 and j2


def _v2_row_score(row: dict[str, Any]) -> object:
    return row.get("score") if "score" in row else row.get("noul")


def _report_text_v2(rows: list[dict[str, Any]], rows_sha256: str) -> tuple[str, bool]:
    frozen = {case["id"]: case for case in V2_FROZEN_CASES}
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(str(row.get("case_id")), []).append(row)

    fresh_positive_rows = [
        row
        for row in rows
        if frozen.get(row.get("case_id"), {}).get("kind") == "fresh"
        and frozen.get(row.get("case_id"), {}).get("expected") is True
    ]
    fresh_negative_rows = [
        row
        for row in rows
        if frozen.get(row.get("case_id"), {}).get("kind") == "fresh"
        and frozen.get(row.get("case_id"), {}).get("expected") is False
    ]
    regression_rows = [row for row in rows if frozen.get(row.get("case_id"), {}).get("kind") == "regression"]
    fresh_negative_true = sum(row.get("returned") is True for row in fresh_negative_rows)
    fresh_positive_true = sum(row.get("returned") is True for row in fresh_positive_rows)
    regression_true = sum(row.get("returned") is True for row in regression_rows)
    null_answers = sum(row.get("returned") is None for row in rows)
    j1 = len(fresh_negative_rows) == 72 and fresh_negative_true == 0
    j2 = len(fresh_positive_rows) == 48 and fresh_positive_true >= 44
    regression_gate = len(regression_rows) == 8 and regression_true == 0
    bound = _wilson_upper(fresh_negative_true, len(fresh_negative_rows))
    bound_text = "n/a" if bound is None else f"{bound * 100:.2f}%"

    lines = [
        "# Under question probe v2 report",
        "",
        f"Rows sha256: {rows_sha256}",
        f"Rows rendered: {len(rows)}",
        f"null answers: {null_answers}",
        "",
        "## Per-case results",
        "",
        "| Case | Command | Expected | Sample answers and scores |",
        "| --- | --- | ---: | --- |",
    ]
    for case in V2_FROZEN_CASES:
        case_rows = sorted(by_case.get(case["id"], []), key=lambda row: row.get("sample", 0))
        samples_text = (
            ", ".join(
                f"{row.get('sample')}: {_display(row.get('returned'))} (score {_display(_v2_row_score(row))})"
                for row in case_rows
            )
            or "—"
        )
        lines.append(f"| {case['id']} | {case['command']} | {_display(case['expected'])} | {samples_text} |")

    missed_positive = [row for row in fresh_positive_rows if row.get("returned") is not True]
    true_fresh_negative = [row for row in fresh_negative_rows if row.get("returned") is True]
    true_regression = [row for row in regression_rows if row.get("returned") is True]
    lines.extend(
        [
            "",
            "## Gates",
            "",
            (
                f"- J1: {'PASS' if j1 else 'FAIL'} — true answers among fresh-negative samples: "
                f"{fresh_negative_true} of 72; one-sided 95% Wilson upper bound: {bound_text}"
            ),
            (
                f"- J2: {'PASS' if j2 else 'FAIL'} — true answers among fresh-positive samples: "
                f"{fresh_positive_true} of 48 (required at least 44)"
            ),
            f"- R: {'PASS' if regression_gate else 'FAIL'} — true answers among regression samples: "
            f"{regression_true} of 8",
            "",
            "### Missed positives",
            "",
        ]
    )
    if missed_positive:
        lines.extend(
            f"- {row.get('case_id')} sample {row.get('sample')}: score {_display(_v2_row_score(row))}"
            for row in missed_positive
        )
    else:
        lines.append("- none")
    lines.extend(["", "### True fresh negatives", ""])
    if true_fresh_negative:
        lines.extend(
            f"- {row.get('case_id')} sample {row.get('sample')}: score {_display(_v2_row_score(row))}"
            for row in true_fresh_negative
        )
    else:
        lines.append("- none")
    lines.extend(["", "### True regression answers", ""])
    if true_regression:
        lines.extend(
            f"- {row.get('case_id')} sample {row.get('sample')}: score {_display(_v2_row_score(row))}"
            for row in true_regression
        )
    else:
        lines.append("- none")
    passed = j1 and j2 and regression_gate
    lines.extend(["", f"probe gate: {'PASS' if passed else 'FAIL'}", ""])
    return "\n".join(lines), passed


def _v4_row_score(row: dict[str, Any]) -> object:
    return row.get("score") if "score" in row else row.get("noul")


def _report_text_v4(rows: list[dict[str, Any]], rows_sha256: str) -> tuple[str, bool]:
    frozen = {case["id"]: case for case in V4_FROZEN_CASES}
    by_case: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_case.setdefault(str(row.get("case_id")), []).append(row)

    us_rows = [row for row in rows if frozen.get(row.get("case_id"), {}).get("label") == "US"]
    ub_rows = [row for row in rows if frozen.get(row.get("case_id"), {}).get("label") == "UB"]
    us_true = sum(row.get("returned") is True for row in us_rows)
    ub_true = sum(row.get("returned") is True for row in ub_rows)
    ub_false_or_null = sum(row.get("returned") is not True for row in ub_rows)
    null_answers = sum(row.get("returned") is None for row in rows)
    p1 = us_true >= 22
    p2 = ub_false_or_null >= 22
    bound = _wilson_upper(ub_true, len(ub_rows))
    bound_text = "n/a" if bound is None else f"{bound * 100:.2f}%"

    lines = [
        "# Under question probe v4 report",
        "",
        f"Rows sha256: {rows_sha256}",
        f"Rows rendered: {len(rows)}",
        f"null answers: {null_answers}",
        "",
        "## Per-case results",
        "",
        "| Case | Command | Label | Sample answers and scores |",
        "| --- | --- | --- | --- |",
    ]
    for case in V4_FROZEN_CASES:
        case_rows = sorted(by_case.get(case["id"], []), key=lambda row: row.get("sample", 0))
        samples_text = (
            ", ".join(
                f"{row.get('sample')}: {_display(row.get('returned'))} (score {_display(_v4_row_score(row))})"
                for row in case_rows
            )
            or "—"
        )
        lines.append(f"| {case['id']} | {case['command']} | {case['label']} | {samples_text} |")

    missed_us = [row for row in us_rows if row.get("returned") is not True]
    true_ub = [row for row in ub_rows if row.get("returned") is True]
    lines.extend(
        [
            "",
            "## Gate P",
            "",
            f"- P1: {'PASS' if p1 else 'FAIL'} — true US samples: {us_true} of 24 (required at least 22)",
            f"- P2: {'PASS' if p2 else 'FAIL'} — false-or-null UB samples: {ub_false_or_null} of 24 "
            f"(required at least 22); true-answer Wilson upper bound: {bound_text}",
            "",
            "### Misses",
            "",
        ]
    )
    misses = [("US", row) for row in missed_us] + [("UB", row) for row in true_ub]
    if misses:
        lines.extend(
            f"- {label} {row.get('case_id')} sample {row.get('sample')}: score {_display(_v4_row_score(row))}"
            for label, row in misses
        )
    else:
        lines.append("- none")
    lines.extend(["", f"probe gate: {'PASS' if p1 and p2 else 'FAIL'}", ""])
    return "\n".join(lines), p1 and p2


def report_rows(rows_path: Path, out: Path, corpus: str = "v1") -> int:
    document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = document.get("rows")
    if not isinstance(rows, list):
        raise ValueError("rows file has no rows list")
    if corpus == "v1":
        report, passed = _report_text(rows, _sha256(rows_path.read_bytes()))
    elif corpus == "v2":
        report, passed = _report_text_v2(rows, _sha256(rows_path.read_bytes()))
    elif corpus == "v4":
        report, passed = _report_text_v4(rows, _sha256(rows_path.read_bytes()))
    else:
        raise ValueError(f"unknown corpus: {corpus}")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(_redact(report), encoding="utf-8")
    return 0 if passed else 1


def _error(message: str) -> int:
    print(_redact(f"under question probe: {message}"), file=sys.stderr)
    return 2


def _check_corpus(corpus: str = "v1") -> int:
    cases = _load_cases(corpus=corpus)
    literal_matches = cases == _corpus_literal(corpus)
    lock_matches = _lock_matches(cases, corpus=corpus)
    print(f"case count: {len(cases)}")
    print(f"corpus literal: {'PASS' if literal_matches else 'FAIL'}")
    print(f"corpus lock: {'PASS' if lock_matches else 'FAIL'}")
    return 0 if literal_matches and lock_matches else 1


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--build-cases", action="store_true")
    modes.add_argument("--check-corpus", action="store_true")
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--run", action="store_true")
    modes.add_argument("--report", action="store_true")
    parser.add_argument("--corpus", choices=("v1", "v2", "v4"), default="v1")
    parser.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--max-calls", type=int)
    parser.add_argument("--max-usd", type=float, default=DEFAULT_MAX_USD)
    parser.add_argument("--rows", type=Path)
    parser.add_argument("--out", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.build_cases:
            cases = build_cases(args.corpus)
            _write_cases(cases, args.corpus)
            print(f"built {len(cases)} cases at {_redact(str(_corpus_paths(args.corpus)[0]))}")
            return 0
        if args.check_corpus:
            return _check_corpus(args.corpus)
        if args.report:
            if args.rows is None or args.out is None:
                return _error("--report requires --rows and --out")
            return report_rows(args.rows, args.out, corpus=args.corpus)
        cases = _load_cases(corpus=args.corpus)
        if args.dry_run:
            _print_dry_run(cases, args.samples)
            return 0
        if not args.confirm:
            return _error("run mode requires --confirm")
        if args.out is None:
            return _error("run mode requires --out")
        max_calls = args.max_calls if args.max_calls is not None else _corpus_max_calls(args.corpus)
        if max_calls < 1:
            return _error("--max-calls must be at least 1")
        ceiling = _ceiling(cases, args.samples)
        if ceiling > args.max_usd:
            return _error(f"USD ceiling ${ceiling:.6f} exceeds --max-usd ${args.max_usd:.6f}")
        if not _lock_matches(cases, corpus=args.corpus):
            return _error("run mode requires a matching lock")
        if not os.environ.get("CLOUDFLARE_WORKER_URL", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_URL")
        if not os.environ.get("CLOUDFLARE_WORKER_TOKEN", "").strip():
            return _error("run mode requires CLOUDFLARE_WORKER_TOKEN")
        client = JevClient.from_environment()
        document = run_cases(cases, samples=args.samples, max_calls=max_calls, out=args.out, client=client)
        print(f"{len(document['rows'])} rows written to {_redact(str(args.out))}")
        if document.get("stop_reason"):
            print(f"stop reason: {_redact(str(document['stop_reason']))}")
        return 0
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as error:
        return _error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())

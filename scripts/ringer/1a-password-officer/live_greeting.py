"""Measure the live fused-segment repair on the 1A officer greeting."""

from __future__ import annotations

import argparse
import copy
import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

import bench.frozen_prompts as fp
from bench.core import load_variation
from storygame.runtime.capture import WorldCapture
from storygame.runtime.contracts import parse_turn_proposal
from storygame.runtime.engine import RuntimeEngine

ROOT = Path(__file__).resolve().parents[3]
VARIATION_PATH = ROOT / "bench" / "variations" / "1a-password-officer.json"
LOGGER = logging.getLogger("storygame.runtime.cloudflare")
INPUT = "Greet the officer."


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _first_reply_parses(raw: str | None) -> bool:
    if raw is None:
        return False
    try:
        payload = json.loads(raw)
        if isinstance(payload, dict):
            payload = dict(payload)
            payload.pop("item_facts", None)
        parse_turn_proposal(payload)
    except (TypeError, ValueError, json.JSONDecodeError):
        return False
    return True


def _segments(result: object) -> list[str] | None:
    values = getattr(result, "segments", None)
    if values is None:
        return None
    texts = []
    for segment in values:
        if hasattr(segment, "text"):
            texts.append(segment.text)
        else:
            texts.append(segment.get("text"))
    return texts


def _officer_inputs() -> list[str]:
    import importlib.util

    spec = importlib.util.spec_from_file_location("capture_1a", Path(__file__).with_name("capture.py"))
    if spec is None or spec.loader is None:
        raise ImportError("cannot load capture.py")
    capture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(capture)
    return capture.OFFICER_INPUTS[:8]


def _run_turn(
    state: object,
    arm: str,
    sample: int,
    send: Callable[[dict[str, Any]], bytes],
    cap: int,
    real_requests: list[int],
) -> dict[str, Any]:
    row: dict[str, Any] = {
        "arm": arm,
        "sample": sample,
        "requests": 0,
        "request_systems": [],
        "recovery_used": False,
        "first_reply_raw": None,
        "first_reply_parses": False,
        "segments": None,
        "error": None,
        "logs": [],
    }
    turn_state = copy.deepcopy(state)
    provider = fp._offline_capture_provider(turn_state)
    if arm == "OFF":
        provider._repair_fused_segments = lambda response: None

    class WarningHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            row["logs"].append(record.getMessage())

    handler = WarningHandler()
    LOGGER.addHandler(handler)

    def hook(payload: dict[str, Any]) -> bytes:
        if not fp._is_narration_payload(payload):
            return fp._CANNED_REPLY
        if real_requests[0] >= cap:
            raise RuntimeError("request cap reached")
        real_requests[0] += 1
        row["request_systems"].append(payload["system"])
        row["requests"] += 1
        row["recovery_used"] = row["recovery_used"] or "Your last answer was not valid" in payload["system"]
        body = send(payload)
        if row["first_reply_raw"] is None:
            row["first_reply_raw"] = fp._decode_replay_body(body)
            row["first_reply_parses"] = _first_reply_parses(row["first_reply_raw"])
        return body

    provider._send_http = hook
    try:
        capture = WorldCapture(provider, lambda _state, _questions: None)
        result = RuntimeEngine(turn_state, provider, capture=capture).turn(INPUT)
        row["segments"] = _segments(result)
    except Exception as error:  # retain partial evidence for transport and turn failures
        row["error"] = str(error)
    finally:
        LOGGER.removeHandler(handler)
    return row


def run(
    out: Path | str,
    samples: int,
    send: Callable[[dict[str, Any]], bytes] | None = None,
    cap: int = 36,
) -> list[dict[str, Any]]:
    """Run sample-major ON/OFF greeting turns and persist rows incrementally."""

    assert 1 <= samples <= 12
    out_path = Path(out)
    if out_path.exists():
        raise FileExistsError(out_path)

    fp.SCENE = "1A"
    variation = load_variation(VARIATION_PATH)
    variation["scripts"] = {"1A": [{"name": "officer", "inputs": _officer_inputs()}]}
    states, _ = fp._prefix_states(variation, [8])
    state = states[7]
    transport = send
    if transport is None:
        transport = fp._default_transport({"variation": "1a-password-officer"})

    rows: list[dict[str, Any]] = []
    real_requests = [0]
    for sample in range(1, samples + 1):
        for arm in ("ON", "OFF"):
            if real_requests[0] + 3 > cap:
                _write_rows(out_path, rows)
                return rows
            rows.append(_run_turn(state, arm, sample, transport, cap, real_requests))
            _write_rows(out_path, rows)
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("out", type=Path)
    parser.add_argument("samples", type=int)
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--cap", type=int, default=36)
    return parser


if __name__ == "__main__":
    args = _parser().parse_args()
    if not 1 <= args.samples <= 12:
        raise SystemExit("samples must be between 1 and 12")
    if not args.confirm:
        print(f"turns {2 * args.samples} (arms ON and OFF, {args.samples} samples each); cap {args.cap} real requests")
        print("dry run: nothing sent")
    else:
        run(args.out, args.samples, cap=args.cap)

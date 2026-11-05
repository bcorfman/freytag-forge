"""Capture and replay saved narrator wire payloads without a model call."""

from __future__ import annotations

import argparse
import copy
import json
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any

from bench.core import load_dotenv, load_variation, seeded_state_for_scene
from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.engine import RuntimeEngine

ROOT = Path(__file__).resolve().parents[1]
SCENE = "3A"
_CANNED_REPLY = json.dumps(
    {
        "narration": json.dumps(
            {"segments": [{"kind": "narration", "text": "Kristin acts."}], "selected_knowledge_ids": []}
        )
    }
).encode()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _script_inputs(variation: dict[str, Any]) -> list[str]:
    scripts = variation.get("scripts", {})
    scene_scripts = scripts.get(SCENE) if isinstance(scripts, dict) else None
    if not isinstance(scene_scripts, list) or not scene_scripts:
        raise ValueError(f"variation has no {SCENE} script")
    script = scene_scripts[0]
    if not isinstance(script, dict) or not isinstance(script.get("inputs"), list):
        raise ValueError(f"variation {variation.get('name', '<unknown>')} has an invalid {SCENE} script")
    inputs = script["inputs"]
    if not all(isinstance(command, str) and command for command in inputs):
        raise ValueError(f"variation {variation.get('name', '<unknown>')} has invalid script inputs")
    return inputs


def _true_fact_ids(state) -> list[str]:
    return sorted(
        fact.predicate
        for fact in state.facts.asserted
        if fact.subject == "story" and str(fact.value).casefold() == "true"
    )


def _handoff_id(engine: RuntimeEngine, state, command: str) -> str | None:
    engine._activate_pacing()
    candidates = engine.projector.project(state, "player", command).candidates
    handoff = uniquely_matched_authored_handoff(command, candidates)
    return handoff.candidate.id if handoff is not None else None


def _prefix_states(variation: dict[str, Any], endpoints: list[int]):
    package, state = seeded_state_for_scene(variation, SCENE)
    inputs = _script_inputs(variation)
    for endpoint in endpoints:
        if endpoint < 1 or endpoint > len(inputs):
            raise ValueError(f"endpoint {endpoint} is outside the {SCENE} script (1-{len(inputs)})")

    def provider(command: str) -> dict[str, object]:
        knowledge_id = _handoff_id(engine, state, command)
        if knowledge_id is None:
            return {"segments": [{"kind": "narration", "text": "Kristin looks."}], "selected_knowledge_ids": []}
        entry = package.knowledge_indexes.by_id[knowledge_id]
        return {
            "segments": [{"kind": "narration", "text": entry.delivery_text, "grounding_ids": [knowledge_id]}],
            "selected_knowledge_ids": [knowledge_id],
        }

    engine = RuntimeEngine(state, provider)
    states = {0: copy.deepcopy(state)}
    for index, command in enumerate(inputs[: max(endpoints) - 1], start=1):
        engine.turn(command)
        states[index] = copy.deepcopy(state)
    return states, inputs


def _offline_capture_provider(state):
    """Build the normal ItemFactsProvider while making its construction offline-safe."""

    inserted_url = "CLOUDFLARE_WORKER_URL" not in os.environ
    old_url = os.environ.get("CLOUDFLARE_WORKER_URL")
    old_semantic = os.environ.get("FREYTAG_SEMANTIC_REVEAL")
    os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    os.environ["FREYTAG_SEMANTIC_REVEAL"] = "0"
    try:
        provider = build_capture_provider(state, mark_fixed=False)
        provider.semantic_ask = None
        return provider
    finally:
        if inserted_url:
            os.environ.pop("CLOUDFLARE_WORKER_URL", None)
        elif old_url is not None:
            os.environ["CLOUDFLARE_WORKER_URL"] = old_url
        if old_semantic is None:
            os.environ.pop("FREYTAG_SEMANTIC_REVEAL", None)
        else:
            os.environ["FREYTAG_SEMANTIC_REVEAL"] = old_semantic


def _is_narration_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False
    system = payload.get("system")
    user = payload.get("user")
    return (
        isinstance(system, str)
        and system.startswith("You are the narrator of an interactive")
        and isinstance(user, str)
        and "CHARACTERS:" in user
        and "SCENE:" in user
    )


def _capture_wire_payload(state, command: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    provider = _offline_capture_provider(state)
    calls: list[dict[str, Any]] = []

    def send(wire_payload: dict[str, Any]) -> bytes:
        calls.append(copy.deepcopy(wire_payload))
        return _CANNED_REPLY

    provider._send_http = send
    capture = WorldCapture(provider, lambda _state, _questions: None)
    RuntimeEngine(state, provider, capture=capture).turn(command)
    narration = [payload for payload in calls if _is_narration_payload(payload)]
    if len(narration) != 1:
        raise RuntimeError(f"expected one narrator payload, found {len(narration)}")
    return narration[0], [payload for payload in calls if not _is_narration_payload(payload)]


def capture(variation_path: Path | str, endpoints: list[int], out_path: Path | str) -> dict[str, Any]:
    """Capture exact narrator requests for selected commands in a 3A script."""

    variation = load_variation(Path(variation_path))
    inputs = _script_inputs(variation)
    if not endpoints:
        raise ValueError("at least one endpoint is required")
    if any(isinstance(endpoint, bool) or not isinstance(endpoint, int) for endpoint in endpoints):
        raise ValueError("endpoints must be command numbers")
    states, inputs = _prefix_states(variation, endpoints)
    records = []
    for endpoint in endpoints:
        state = states[endpoint - 1]
        command = inputs[endpoint - 1]
        prefix = inputs[: endpoint - 1]
        wire_payload, other_payloads = _capture_wire_payload(state, command)
        records.append(
            {
                "n": endpoint,
                "command": command,
                "prefix": prefix,
                "committed_after_prefix": _true_fact_ids(state),
                "wire_payload": wire_payload,
                "other_payloads": other_payloads,
            }
        )
    result = {
        "variation": variation["name"],
        "package_hash": variation["_package_hash"],
        "endpoints": records,
    }
    _write_json(Path(out_path), result)
    return result


def _variation_path(name: str) -> Path:
    direct = ROOT / "bench" / "variations" / f"{name}.json"
    if direct.is_file():
        return direct
    for path in sorted((ROOT / "bench" / "variations").glob("*.json")):
        try:
            if json.loads(path.read_text(encoding="utf-8")).get("name") == name:
                return path
        except (OSError, json.JSONDecodeError):
            continue
    raise FileNotFoundError(f"cannot find variation named {name!r}")


def _default_transport(frozen: dict[str, Any]):
    load_dotenv()
    variation = load_variation(_variation_path(str(frozen["variation"])))
    _, state = seeded_state_for_scene(variation, SCENE)
    return _offline_capture_provider(state)._send_http


def _decode_replay_body(body: bytes) -> str:
    raw = body.decode("utf-8", errors="replace")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return raw
    if isinstance(decoded, dict) and isinstance(decoded.get("narration"), str):
        return decoded["narration"]
    return raw


def replay(
    frozen_path: Path | str,
    samples: int,
    out_path: Path | str,
    *,
    send: Callable[[dict[str, Any]], bytes] | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Replay each saved wire payload exactly once per requested sample."""

    frozen = json.loads(Path(frozen_path).read_text(encoding="utf-8"))
    endpoints = frozen.get("endpoints", [])
    if not isinstance(endpoints, list):
        raise ValueError("frozen endpoints must be a list")
    if isinstance(samples, bool) or not isinstance(samples, int) or samples < 1:
        raise ValueError("samples must be positive")
    if dry_run:
        print(f"requests {len(endpoints) * samples}")
        print("endpoints " + ", ".join(str(item.get("n")) for item in endpoints))
        return []

    transport = send
    transport_error: Exception | None = None
    if transport is None:
        try:
            transport = _default_transport(frozen)
        except Exception as error:  # keep one result row per requested sample
            transport_error = error

    rows: list[dict[str, Any]] = []
    for endpoint in endpoints:
        number = endpoint.get("n")
        command = endpoint.get("command")
        payload = endpoint.get("wire_payload")
        for sample in range(1, samples + 1):
            row: dict[str, Any] = {
                "n": number,
                "sample": sample,
                "command": command,
                "narration": None,
                "error": None,
                "raw": None,
            }
            try:
                if transport_error is not None:
                    raise transport_error
                assert transport is not None
                body = transport(payload)
                if not isinstance(body, bytes):
                    raise TypeError("transport returned non-bytes body")
                row["raw"] = body.decode("utf-8", errors="replace")
                row["narration"] = _decode_replay_body(body)
                print(f"{number} {sample} ok")
            except Exception as error:
                row["error"] = str(error)
                print(f"{number} {sample} error")
            rows.append(row)
            _write_json(Path(out_path), rows)
    return rows


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m bench.frozen_prompts")
    commands = parser.add_subparsers(dest="action", required=True)

    capture_parser = commands.add_parser("capture", help="capture offline narrator payloads")
    capture_parser.add_argument("variation_pos", type=Path, nargs="?")
    capture_parser.add_argument("endpoints_pos", type=int, nargs="*")
    capture_parser.add_argument("--variation", dest="variation_opt", type=Path)
    capture_parser.add_argument("--endpoints", dest="endpoints_opt", type=int, nargs="+")
    capture_parser.add_argument("--out", type=Path, required=True)

    replay_parser = commands.add_parser("replay", help="replay saved narrator payloads")
    replay_parser.add_argument("frozen", type=Path)
    replay_parser.add_argument("--samples", type=int, default=1)
    replay_parser.add_argument("--out", type=Path)
    replay_parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.action == "capture":
        variation = args.variation_opt or args.variation_pos
        endpoints = args.endpoints_opt or args.endpoints_pos
        if variation is None:
            raise SystemExit("capture requires a variation path")
        if not endpoints:
            raise SystemExit("capture requires at least one endpoint")
        capture(variation, endpoints, args.out)
        return 0
    if args.dry_run:
        replay(args.frozen, args.samples, args.out or Path("/tmp/frozen-prompts-unused.json"), dry_run=True)
        return 0
    if args.out is None:
        raise SystemExit("replay requires --out unless --dry-run is used")
    replay(args.frozen, args.samples, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

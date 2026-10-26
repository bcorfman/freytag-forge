"""Run the 1A transcript against product wiring, with a safe dry-run mode."""

from __future__ import annotations

import argparse
import io
import json
import os
import subprocess
import sys
import urllib.error
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

ROUTES = {
    "reported": (
        "go in the house",
        "feel in the gap",
        "look at the fabric",
        "pull out the drawer",
        "feel under the drawer",
        "go out to the truck",
        "get in",
        "look around",
    ),
    "corrected": (
        "go in the house",
        "pull out the drawer",
        "feel in the gap",
        "look around",
        "wait",
        "wait",
        "go out to the truck",
        "get in",
        "look around",
        "get out of the truck",
        "look around",
        "wait",
    ),
    "witnessed": (
        "go in the house",
        "examine the carved initials",
        "wait",
        "wait",
        "wait",
        "feel under the drawer",
        "say what the card is to the officer",
        "wait",
        "go out to the truck",
        "get in",
        "look around",
    ),
    "movement": (
        "look around",
        "go outside",
        "look around",
        "go out to the truck",
        "look around",
        "get out of the truck",
        "look around",
        "go inside",
        "look around",
        "go out to the truck",
        "go inside",
        "look around",
    ),
    "observe": (
        "inspect the drawer",
        "pull out the drawer",
        "feel under the drawer",
        "feel under the drawer",
        "go outside",
        "inspect the truck",
        "enter the truck",
        "inspect the passenger seat",
        "examine my laptop",
        "get out of the truck",
        "examine the truck",
        "go inside",
        "inspect the drawer",
    ),
    "observe_topup": (
        "inspect the drawer",
        "pull out the drawer",
        "feel under the drawer",
        "feel under the drawer",
        "go outside",
        "inspect the truck",
        "enter the truck",
        "pick up my laptop",
        "inspect the passenger seat",
    ),
}
TRACKED = (
    "kristin",
    "kristin_laptop",
    "memory_card",
    "michelle_drawer",
    "kristin_truck",
    "patrol_officer",
)
QUOTA_CODES = ("AI_QUOTA_EXCEEDED", "AI_DAILY_BUDGET_EXCEEDED")


class CallCapExceeded(RuntimeError):
    pass


class QuotaExceeded(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


class _Response:
    def __init__(self, body: object, counter: CallCounter) -> None:
        self._body = json.dumps(body).encode() if not isinstance(body, bytes) else body
        self._counter = counter
        self.status = 200
        self.headers = {}

    def read(self, *args: object, **kwargs: object) -> bytes:
        self._counter.inspect(self._body.decode(errors="replace"))
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class _LiveResponse:
    def __init__(self, response: object, counter: CallCounter) -> None:
        self._response = response
        self._counter = counter
        self.status = getattr(response, "status", 200)
        self.headers = getattr(response, "headers", {})
        counter.inspect(str(self.headers))

    def read(self, *args: object, **kwargs: object) -> bytes:
        body = self._response.read(*args, **kwargs)
        self._counter.inspect(body.decode(errors="replace"))
        return body

    def __enter__(self) -> _LiveResponse:
        self._response.__enter__()
        return self

    def __exit__(self, *args: object) -> object:
        return self._response.__exit__(*args)


class CallCounter:
    def __init__(self, max_calls: int, dry: bool) -> None:
        self.max_calls = max_calls
        self.dry = dry
        self.calls_made = 0
        self.prompts: list[dict[str, str]] = []
        self.responses: list[str] = []
        self.real_calls = 0
        self.stop_reason: str | None = None

    def capture_prompt(self, request: object) -> None:
        try:
            payload = json.loads(getattr(request, "data", b"{}").decode())
        except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
            return
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("system"), str)
            and isinstance(payload.get("user"), str)
        ):
            self.prompts.append({"system": payload["system"], "user": payload["user"]})

    def before_call(self) -> None:
        if self.stop_reason is not None:
            if self.stop_reason == "MAX_CALLS_EXCEEDED":
                raise CallCapExceeded(f"max-calls exceeded ({self.max_calls})")
            raise QuotaExceeded(self.stop_reason)
        if self.calls_made >= self.max_calls:
            self.stop_reason = "MAX_CALLS_EXCEEDED"
            raise CallCapExceeded(f"max-calls exceeded ({self.max_calls})")
        self.calls_made += 1

    def inspect(self, text: str) -> None:
        self.responses.append(text)
        for code in QUOTA_CODES:
            if code in text:
                self.stop_reason = code
                raise QuotaExceeded(code)

    def dry_urlopen(self, request: object, timeout: float | None = None, **_kwargs: object) -> _Response:
        self.before_call()
        self.capture_prompt(request)
        url = getattr(request, "full_url", "")
        if str(url).endswith("/jev"):
            raise urllib.error.URLError("dry-run Jev disabled")
        payload = {
            "narration": json.dumps(
                {"segments": [{"kind": "narration", "text": "The scene continues."}], "selected_knowledge_ids": []}
            )
        }
        return _Response(payload, self)

    def live_urlopen(self, request: object, timeout: float | None = None, **kwargs: object) -> object:
        self.before_call()
        self.real_calls += 1
        self.capture_prompt(request)
        from urllib.request import urlopen

        try:
            response = urlopen(request, timeout=timeout, **kwargs)
        except urllib.error.HTTPError as error:
            quota_error = None
            try:
                self.inspect(str(error.headers))
            except QuotaExceeded as exc:
                quota_error = exc
            try:
                body = error.read()
            except Exception:
                body = None
            if body is not None:
                error = urllib.error.HTTPError(error.url, error.code, error.msg, error.headers, io.BytesIO(body))
                try:
                    self.inspect(body.decode(errors="replace"))
                except QuotaExceeded as exc:
                    quota_error = exc
            if quota_error is not None:
                raise error
            raise
        return _LiveResponse(response, self)


def _json(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(k): _json(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json(v) for v in value]
    if hasattr(value, "model_dump"):
        return _json(value.model_dump(mode="json"))
    return repr(value)


def _places(state: Any) -> dict[str, Any]:
    from storygame.runtime.world_model import world_for

    world = world_for(state.package, state.facts)
    return {name: world.parent(name) for name in TRACKED}


def _prompts(counter: CallCounter) -> list[dict[str, str]]:
    return list(counter.prompts)


def _route_inputs(route: str, turns: int | None = None) -> tuple[str, ...]:
    inputs = ROUTES[route]
    return inputs if turns is None else inputs[:turns]


def _wire(counter: CallCounter, dry: bool) -> None:
    import storygame.runtime.cloudflare as cf
    import storygame.runtime.jev as jev

    opener = counter.dry_urlopen if dry else counter.live_urlopen
    cf.urlopen = opener
    jev.urlopen = opener


def _record_steps(engine: Any, capture: Any) -> dict[str, Any]:
    before = getattr(capture, "last_before", None)
    attempt = getattr(engine, "last_attempt", None)
    return {
        "steps": list(before.get("steps", ())) if isinstance(before, dict) else None,
        "attempt_stages": [_json(stage) for stage in getattr(attempt, "stages", ())] if attempt else None,
    }


def _observation_relations(calls: list[tuple[Any, ...]]) -> list[dict[str, Any]] | None:
    if not calls:
        return None
    return [
        {"thing": relation.thing, "place": relation.place, "holder": relation.holder}
        for relations in calls
        for relation in relations
    ]


def _observation_request(capture: Any, state: Any) -> dict[str, str | None] | None:
    request = getattr(capture.provider, "observation_request", None)
    if request is None:
        return None
    from storygame.runtime.world_model import world_for

    world = world_for(state.package, state.facts)
    focus = world.name(request.focus) if request.focus is not None else None
    return {"kind": request.kind, "focus": focus}


def _shadow_observation_values(
    capture: Any,
    state: Any,
    previous_after: object,
    previous_request: object,
) -> tuple[Any, dict[str, str | None] | None]:
    after = getattr(capture, "last_after", None)
    observation_shadow = after.get("observation_shadow") if isinstance(after, dict) else None
    if after is previous_after:
        observation_shadow = None
    observation_request = _observation_request(capture, state)
    if previous_request is not None and capture.provider.observation_request is previous_request:
        observation_request = None
    return observation_shadow, observation_request


def _stop_exception(counter: CallCounter) -> CallCapExceeded | QuotaExceeded | None:
    if counter.stop_reason == "MAX_CALLS_EXCEEDED":
        return CallCapExceeded(f"max-calls exceeded ({counter.max_calls})")
    if counter.stop_reason is not None:
        return QuotaExceeded(counter.stop_reason)
    return None


def _replicate(
    counter: CallCounter,
    package: Any,
    route: str,
    inputs: tuple[str, ...],
    record: dict[str, Any],
    on_turn: Any = None,
    shadow: bool = False,
    relation_calls: list[tuple[Any, ...]] | None = None,
) -> dict[str, Any]:
    from storygame.runtime.capture import WorldCapture, build_capture_provider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.runtime.jev import JevClient
    from storygame.runtime.state import RuntimeState

    state = RuntimeState.bootstrap(package)
    provider = build_capture_provider(state)
    capture_ask = JevClient.from_environment().ask
    provider.semantic_ask = capture_ask
    capture = WorldCapture(provider, capture_ask, fixed_refusal=True, engine_refusal=True)
    if shadow:
        from storygame.runtime.observation_verifier import ObservationVerifier

        capture.shadow_verifier = ObservationVerifier(capture_ask)
    engine = RuntimeEngine(state, provider, capture=capture)
    counter.prompts.clear()
    counter.responses.clear()
    opening = engine.opening()
    record["opening"] = {
        "narration": opening.narration,
        "places": _places(state),
        "prompts": _prompts(counter),
        "provider_responses": list(counter.responses),
    }
    stop = _stop_exception(counter)
    if stop is not None:
        raise stop
    for command in inputs:
        if relation_calls is not None:
            relation_calls.clear()
        counter.prompts.clear()
        counter.responses.clear()
        before = _places(state)
        fired_before = set(state.fired_event_ids)
        if shadow:
            previous_after = getattr(capture, "last_after", None)
            previous_request = capture.provider.observation_request
        error = None
        try:
            result = engine.turn(command)
            narration = result.narration
            selected = list(getattr(result, "selected_knowledge_ids", ()))
        except Exception as exc:  # preserve this sample and continue as requested
            result = None
            narration = None
            selected = []
            error = f"{type(exc).__name__}: {exc}"
        row = {
            "route": route,
            "input": command,
            "before": before,
            "after": _places(state),
            "places_before": before,
            "places_after": _places(state),
            "scene": state.current_scene_id,
            "turn_index": state.turn_index,
            "fired": sorted(set(state.fired_event_ids) - fired_before),
            "newly_fired_event_ids": sorted(set(state.fired_event_ids) - fired_before),
            "selected_knowledge_ids": selected,
            "reference": repr(engine.last_reference_resolution)
            if engine.last_reference_resolution is not None
            else None,
            "engine_steps": _record_steps(engine, capture),
            "item_facts_unplaced": provider.last_item_facts_unplaced()
            if hasattr(provider, "last_item_facts_unplaced")
            else None,
            "prompts": _prompts(counter),
            "provider_responses": list(counter.responses),
            "narration": narration,
            "narrator_called": any(prompt["system"].startswith("You are the narrator") for prompt in counter.prompts),
            "error": error,
            "notes": [] if getattr(capture, "last_before", None) is not None else ["capture step field unavailable"],
        }
        if shadow:
            observation_shadow, observation_request = _shadow_observation_values(
                capture, state, previous_after, previous_request
            )
            row["observation_shadow"] = observation_shadow
            row["observation_relations"] = (
                _observation_relations(relation_calls) if relation_calls is not None else None
            )
            row["observation_request"] = observation_request
        record.setdefault("turns", []).append(row)
        if on_turn is not None:
            on_turn()
        stop = _stop_exception(counter)
        if stop is not None:
            raise stop
    return record


def _summary(
    mode: str,
    requested: int,
    rows: list[dict[str, Any]],
    route: str,
    inputs: tuple[str, ...],
    counter: CallCounter,
    stopped: str | None,
    package: Any,
    out: Path,
    shadow: bool = False,
) -> dict[str, Any]:
    completed = sum(len(row.get("turns", ())) == len(inputs) for row in rows)
    errors = sum(1 for row in rows for turn in row.get("turns", ()) if turn.get("error"))
    sha = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=False
    ).stdout.strip()
    summary = {
        "mode": mode,
        "route": route,
        "replicates_requested": requested,
        "replicates_completed": completed,
        "turns_recorded": sum(len(row.get("turns", ())) for row in rows),
        "calls_made": counter.calls_made,
        "max_calls": counter.max_calls,
        "stopped_reason": stopped,
        "errors": errors,
        "git_sha": sha,
        "package_dir": str(ROOT / "data/stories/continuity-initiative"),
        "worker_url_host": "worker.example"
        if mode == "dry"
        else urlparse(os.environ["CLOUDFLARE_WORKER_URL"]).hostname,
        "real_calls": counter.real_calls,
        "inputs": list(inputs),
        "semantic_reveal_effective": os.environ.get("FREYTAG_SEMANTIC_REVEAL", "1"),
    }
    if shadow:
        summary.update(
            {
                "shadow": True,
                "observation_turns": sum(
                    turn.get("observation_relations") is not None for row in rows for turn in row.get("turns", ())
                ),
                "shadow_verifier_requests": sum(
                    turn.get("observation_shadow", {}).get("requests", 0)
                    for row in rows
                    for turn in row.get("turns", ())
                    if isinstance(turn.get("observation_shadow"), dict)
                ),
            }
        )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--replicates", type=int, default=5)
    parser.add_argument("--turns", type=int)
    parser.add_argument("--route", choices=tuple(ROUTES), default="reported")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--max-calls", type=int, default=200)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--confirm", action="store_true")
    parser.add_argument("--shadow", action="store_true")
    args = parser.parse_args(argv)
    if not args.dry_run and (not args.confirm or not os.environ.get("CLOUDFLARE_WORKER_URL")):
        print("live mode requires --confirm and CLOUDFLARE_WORKER_URL", file=sys.stderr)
        return 2
    turns = len(ROUTES[args.route]) if args.turns is None else args.turns
    if not 0 <= turns <= len(ROUTES[args.route]) or args.replicates < 0 or args.max_calls < 0:
        parser.error("invalid replicate, turn, or call limit")
    inputs = _route_inputs(args.route, turns)
    mode = "dry" if args.dry_run else "live"
    if args.dry_run:
        os.environ.setdefault("CLOUDFLARE_WORKER_URL", "https://worker.example/turn")
    os.environ["FREYTAG_WORLD_CAPTURE"] = "1"
    from storygame.story_package.loader import load_story_package

    package = load_story_package(ROOT / "data/stories/continuity-initiative")
    counter = CallCounter(args.max_calls, args.dry_run)
    _wire(counter, args.dry_run)
    args.out.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    stopped = None
    relation_calls: list[tuple[Any, ...]] = []
    capture_module = None
    original_relations = None
    try:
        if args.shadow:
            import storygame.runtime.capture as capture_module

            original_relations = capture_module.relations_from_context

            def record_relations(context: Any) -> tuple[Any, ...]:
                relations = original_relations(context)
                relation_calls.append(relations)
                return relations

            capture_module.relations_from_context = record_relations
        for _ in range(args.replicates):
            record: dict[str, Any] = {"route": args.route, "opening": None, "turns": []}
            rows.append(record)
            _replicate(
                counter,
                package,
                args.route,
                inputs,
                record,
                lambda: (args.out / "rows.json").write_text(
                    json.dumps(rows, indent=2, ensure_ascii=False, default=_json) + "\n"
                ),
                args.shadow,
                relation_calls,
            )
            (args.out / "rows.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=_json) + "\n")
    except (CallCapExceeded, QuotaExceeded) as exc:
        stopped = getattr(exc, "code", "MAX_CALLS_EXCEEDED")
    finally:
        if capture_module is not None and original_relations is not None:
            capture_module.relations_from_context = original_relations
        (args.out / "rows.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False, default=_json) + "\n")
        summary = _summary(
            mode, args.replicates, rows, args.route, inputs, counter, stopped, package, args.out, args.shadow
        )
        (args.out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

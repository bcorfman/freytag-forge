"""Shared offline engine-capture helpers."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]


def _load_probe() -> Any:
    probe_path = ROOT / "scripts" / "ringer" / "environment_narration" / "hidden_bench_prose_probe.py"
    spec = importlib.util.spec_from_file_location("drain_details_hidden_probe", probe_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load offline probe from {probe_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _build_state(package: Any, *, recovered: bool = False) -> Any:
    probe = _load_probe()
    state = probe._scene_1b_state(package)
    if recovered:
        from storygame.runtime.facts import Fact
        from storygame.runtime.world_model import apply_world_effects

        state.facts.assert_fact(Fact(predicate="bench_clues_recovered", subject="story", value="true"))
        apply_world_effects(package, state.facts)
    return state


def _force_1b2(package: Any, state: Any, provider: Any) -> None:
    from bench.core import resolve_beat

    selected = resolve_beat(package, "1B", "1B.2")
    provider._forced_beat_anchors.add(selected.anchor)
    storylets = [item.id for item in package.storylets if selected.anchor in item.source_links]
    if not storylets:
        raise RuntimeError("1B.2 has no storylet source")
    state.active_event_ids.update(storylets)


def _fake_response(text: str = "The scene continues.") -> dict[str, object]:
    return {
        "segments": [{"kind": "narration", "text": text}],
        "selected_knowledge_ids": [],
        "item_facts": {},
    }


def _run_engine(
    package: Any,
    command: str | None = None,
    *,
    recovered: bool = False,
    force_1b2: bool = False,
    retry: bool = False,
    malformed: bool = False,
    earned_escape: bool = False,
) -> list[dict[str, str]]:
    from storygame.runtime.cloudflare import CloudflareTurnProvider
    from storygame.runtime.engine import RuntimeEngine
    from storygame.runtime.validation import ProposalValidationError

    probe = _load_probe()
    state = _build_state(package, recovered=recovered)
    provider = probe._world_aware_provider(state)
    if force_1b2:
        _force_1b2(package, state, provider)
    if earned_escape:
        from storygame.runtime.facts import Fact

        state.active_event_ids.add("SL-1B-C")
        for fact_id in ("brandon_identified", "missing_may_be_alive"):
            state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    requests: list[dict[str, str]] = []
    request_count = 0

    def recording_request(_provider: Any, payload: dict[str, object]) -> dict[str, object]:
        nonlocal request_count
        if payload.get("__freytag_request_budget", "narration") == "item_facts":
            return {"refers": [], "same_as": {}}
        requests.append({"system": str(payload["system"]), "user": str(payload["user"])})
        request_count += 1
        if malformed and request_count == 1:
            raise json.JSONDecodeError("offline malformed reply", "{", 0)
        return _fake_response()

    original_request = CloudflareTurnProvider._request
    CloudflareTurnProvider._request = recording_request
    try:
        engine = RuntimeEngine(state, provider)
        if command is None:
            engine.opening()
        else:
            engine.opening()
            requests.clear()
            request_count = 0
            if retry:
                original_validate = engine.narration_validator.validate
                validation_calls = 0

                def reject_once(*args: Any, **kwargs: Any) -> None:
                    nonlocal validation_calls
                    validation_calls += 1
                    if validation_calls == 1:
                        raise ProposalValidationError("offline retry", code="test_guard_retry")
                    original_validate(*args, **kwargs)

                engine.narration_validator.validate = reject_once
            engine.turn(command)
    finally:
        CloudflareTurnProvider._request = original_request
    return requests

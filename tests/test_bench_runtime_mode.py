"""The runtime bench must stay equivalent to the original in-process path.

This comparison is deliberately strict: if save/load or provider recreation
exposes a real difference, the test should show it rather than hide it in the
bench record.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import bench.core as core
from storygame.runtime.cloudflare import CloudflareTurnProvider

ROOT = Path(__file__).resolve().parents[1]
NORMAL = ROOT / "bench/variations/item-facts-world-two-scene.json"
RUNTIME = ROOT / "bench/variations/item-facts-world-two-scene-runtime.json"


def _variation(path: Path, turns: int = 3) -> dict:
    variation = core.load_variation(path)
    variation["fixed_turns"] = turns
    variation["_fixed_turns"] = turns
    variation["continue_to"] = None
    variation["_continue_to"] = None
    variation["scripts"]["1A"][0]["inputs"] = [
        "Open the drawer with my initials carved into it.",
        "Pick up Michelle's phone and put it in my pocket.",
        "Look beneath the KMS drawer.",
    ]
    return variation


def _narration_reply(_self, _payload):
    return {
        "segments": [{"kind": "narration", "text": "Kristin searches the room."}],
        "item_facts": {"Michelle's phone": {"held_by": "Kristin"}},
    }


def _run(monkeypatch: pytest.MonkeyPatch, path: Path, turns: int = 3) -> dict:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", _narration_reply)
    variation = _variation(path, turns)
    return core.run_scene(variation, "1A", variation["scripts"]["1A"][0])


def test_runtime_mode_matches_bench_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    normal = _run(monkeypatch, NORMAL)
    runtime = _run(monkeypatch, RUNTIME)

    fields = ("prompt_user", "things_given", "item_facts_before", "item_facts_after", "item_facts_issues")
    assert [[turn[field] for field in fields] for turn in normal["turns"]] == [
        [turn[field] for field in fields] for turn in runtime["turns"]
    ]


def test_runtime_mode_builds_fresh_provider_each_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    original = core.build_capture_provider

    def build(state):
        calls.append(state)
        return original(state)

    loads = []
    original_load = core.RuntimeStateSqliteStore.load

    def load(store, session_id, package):
        loaded = original_load(store, session_id, package)
        loads.append(loaded)
        return loaded

    monkeypatch.setattr(core, "build_capture_provider", build)
    monkeypatch.setattr(core.RuntimeStateSqliteStore, "load", load)
    result = _run(monkeypatch, RUNTIME, turns=3)

    assert result["status"] == "ok"
    assert len(calls) == 1 + len(result["turns"])
    assert len(loads) == len(result["turns"])


def test_runtime_mode_records_rejected_turn(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0

    def invalid_after_opening(_self, _payload):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"segments": [{"kind": "narration", "text": "The room is quiet."}]}
        return {"not": "a turn"}

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", invalid_after_opening)
    variation = _variation(RUNTIME, turns=1)
    result = core.run_scene(variation, "1A", variation["scripts"]["1A"][0])

    assert result["status"] == "ok"
    rejected = result["rejected_turns"][0]
    assert rejected["rejection_code"]
    assert rejected["item_facts_after"] == rejected["item_facts_before"]


def test_runtime_flag_loader_requires_boolean() -> None:
    variation = json.loads(NORMAL.read_text())
    variation["runtime"] = "yes"
    with pytest.raises(ValueError, match="runtime must be a boolean"):
        core.resolve_variation(copy.deepcopy(variation), NORMAL)

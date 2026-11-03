"""A runtime-wired bench script may walk between places; that turn has no capture record and must not break the run."""

from __future__ import annotations

from pathlib import Path

import pytest

import bench.core as core
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import _MATCH_SYSTEM

VARIATION = Path("bench/variations/richer-1a-candidate.json")


@pytest.fixture
def stubbed_network(monkeypatch):
    """Answer every narration and matching request locally; any real call would raise."""
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "x")
    calls: list[str] = []

    def request(_provider, payload):
        calls.append(payload.get("system", "")[:20])
        if payload.get("system") == _MATCH_SYSTEM:
            return {"refers": [], "same_as": {}, "kind": {}}
        return {
            "segments": [{"kind": "narration", "text": f"Kristin takes in the scene, view number {len(calls)}."}],
            "selected_knowledge_ids": [],
        }

    def blocked(*_args, **_kwargs):
        raise AssertionError("the offline bench test must not reach any network")

    monkeypatch.setattr(CloudflareTurnProvider, "_request", request)
    monkeypatch.setattr(core, "ask_jev", lambda **_kwargs: lambda *_a, **_k: {})
    monkeypatch.setattr("urllib.request.urlopen", blocked)
    return calls


def _record(inputs: list[str]) -> dict:
    variation = core.resolve_variation(core.load_variation(VARIATION), VARIATION)
    variation["_fixed_turns"] = len(inputs)
    return core.run_scene(variation, "1A", {"name": "t", "inputs": inputs})


def test_a_walk_between_places_is_recorded_with_empty_capture_fields(stubbed_network):
    record = _record(["Examine the back door.", "Go outside.", "Talk to the neighbor."])
    turns = record["turns"]
    assert len(turns) == 3
    walk = turns[1]
    assert walk["item_facts_resolutions"] == {} and walk["item_facts_engine_resolutions"] == {}
    assert walk["item_facts_place_resolutions"] == {} and walk["match_call"] is False


def test_a_walk_never_inherits_the_previous_turns_capture_record(stubbed_network):
    record = _record(["Examine the back door.", "Go outside."])
    first, walk = record["turns"]
    assert first["item_facts_raw"] is not None
    assert walk["item_facts_raw"] in ({}, None)
    assert walk["item_facts_issues"] == [] and walk["item_facts_unplaced"] == []

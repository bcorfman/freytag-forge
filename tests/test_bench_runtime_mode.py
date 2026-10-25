"""The runtime bench must stay equivalent to the original in-process path.

This comparison is deliberately strict: if save/load or provider recreation
exposes a real difference, the test should show it rather than hide it in the
bench record.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import bench.core as core
import bench.jev_use as jev_use
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import NarrationSegment
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
NORMAL = ROOT / "bench/variations/item-facts-world-two-scene.json"
RUNTIME = ROOT / "bench/variations/item-facts-world-two-scene-runtime.json"
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")


def _variation(path: Path, turns: int = 3, inputs: list[str] | None = None) -> dict:
    variation = core.load_variation(path)
    variation["fixed_turns"] = turns
    variation["_fixed_turns"] = turns
    variation["continue_to"] = None
    variation["_continue_to"] = None
    variation["scripts"]["1A"][0]["inputs"] = inputs or [
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


@pytest.fixture
def fake_jev(monkeypatch: pytest.MonkeyPatch) -> list[dict]:
    questions_asked: list[dict] = []

    def factory(*, environment, opener):
        def ask(_state, questions):
            questions_asked.append(questions)
            return {question_id: {"noul": 1.0} for question_id in questions}

        return ask

    monkeypatch.setattr(jev_use, "_ask", factory)
    monkeypatch.setattr(core, "ask_jev", factory)
    return questions_asked


def _run(monkeypatch: pytest.MonkeyPatch, path: Path, turns: int = 3, inputs: list[str] | None = None) -> dict:
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", _narration_reply)
    variation = _variation(path, turns, inputs)
    return core.run_scene(variation, "1A", variation["scripts"]["1A"][0])


def test_runtime_mode_exit_turn_records_facts_before_transition(
    monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]
) -> None:
    def leave_scene(engine):
        world = world_for(engine.state.package, engine.state.facts)
        assert world.move("kristin", "los_angeles_park").ok
        engine.state.current_scene_id = "1B"
        return (NarrationSegment(kind="narration", text="Kristin reaches the park."),)

    monkeypatch.setattr(core.RuntimeEngine, "_apply_authored_transition", leave_scene)
    result = _run(monkeypatch, RUNTIME, turns=1)
    turn = result["turns"][0]

    assert turn["left_scene"] is True
    assert turn["item_facts_after"]["Kristin"] == turn["item_facts_before"]["Kristin"]
    assert turn["item_facts_after"]["Kristin"]["place"] != "Los Angeles park"


def test_runtime_mode_exit_turn_narration_leaves_out_bridge_and_entry(
    monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]
) -> None:
    authored_texts: dict[str, str] = {}

    def leave_scene(engine):
        world = world_for(engine.state.package, engine.state.facts)
        assert world.move("kristin", "los_angeles_park").ok
        source_scene = next(
            scene for scene in engine.state.package.scenes if scene.metadata.scene_id == engine.state.current_scene_id
        )
        target_scene = next(scene for scene in engine.state.package.scenes if scene.metadata.scene_id == "1B")
        bridge_text = next(iter(source_scene.metadata.bridge_text.values()))
        authored_texts["bridge"] = bridge_text
        authored_texts["entry"] = target_scene.metadata.entry_text
        engine.state.current_scene_id = target_scene.metadata.scene_id
        return (
            NarrationSegment(kind="narration", text=bridge_text),
            NarrationSegment(kind="narration", text=target_scene.metadata.entry_text),
        )

    monkeypatch.setattr(core.RuntimeEngine, "_apply_authored_transition", leave_scene)
    result = _run(monkeypatch, RUNTIME, turns=1, inputs=["Walk out to the truck."])
    turn = result["turns"][0]

    assert turn["narration"] == ("Kristin sat down in the driver's seat. Kristin's laptop sat on the passenger seat.")
    assert authored_texts["bridge"] not in turn["narration"]
    assert authored_texts["entry"] not in turn["narration"]


def test_runtime_mode_records_narration_prompt(monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]) -> None:
    calls: list[dict] = []

    def scripted_reply(self, payload):
        calls.append(payload)
        self.last_prompt = {"system": payload["system"], "user": payload["user"]}
        system = payload["system"]
        if system.startswith("You match names"):
            return {"refers": [], "same_as": {"Mysterious key": "new"}, "kind": {"Mysterious key": "thing"}}
        if system.startswith("You keep track"):
            return {"item_facts": {}}
        if "Open the drawer" in payload["user"]:
            return {
                "segments": [{"kind": "narration", "text": "Kristin finds the key."}],
                "item_facts": {"Mysterious key": {"held_by": "Kristin"}},
            }
        return {"segments": [{"kind": "narration", "text": "The room is quiet."}]}

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", scripted_reply)
    variation = _variation(RUNTIME, turns=1)
    result = core.run_scene(variation, "1A", variation["scripts"]["1A"][0])

    match_calls = [call for call in calls if call["system"].startswith("You match names")]
    narration_calls = [
        call
        for call in calls
        if not call["system"].startswith("You match names") and not call["system"].startswith("You keep track")
    ]
    assert len(match_calls) == 2
    assert calls.index(match_calls[-1]) > calls.index(narration_calls[1])
    assert result["turns"][0]["prompt_system"] == narration_calls[1]["system"]
    assert result["turns"][0]["prompt_user"] == narration_calls[1]["user"]


def test_runtime_mode_builds_fresh_provider_each_turn(monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]) -> None:
    calls = []
    original = core.build_capture_provider

    def build(state, *, mark_fixed=False):
        calls.append(mark_fixed)
        return original(state, mark_fixed=mark_fixed)

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


def test_runtime_mode_passes_engine_refusal_to_capture(monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]) -> None:
    calls: list[tuple[bool, bool]] = []
    original = core.WorldCapture

    def capture(provider, ask, fixed_refusal=False, *, engine_refusal=False):
        calls.append((fixed_refusal, engine_refusal))
        return original(provider, ask, fixed_refusal=fixed_refusal, engine_refusal=engine_refusal)

    monkeypatch.setattr(core, "WorldCapture", capture)
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", _narration_reply)
    enabled = _variation(RUNTIME, turns=1)
    enabled["fixed_refusal"] = True
    enabled["engine_refusal"] = True
    assert core.run_scene(enabled, "1A", enabled["scripts"]["1A"][0])["status"] == "ok"
    assert calls == [(True, True), (True, True)]


def test_bench_engine_refused_turn_has_no_prompt_and_no_stale_item_facts(
    monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]
) -> None:
    narrator_calls = []

    def narrator(self, payload):
        narrator_calls.append(payload)
        return _narration_reply(self, payload)

    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://worker.invalid/turn")
    monkeypatch.setattr(CloudflareTurnProvider, "_request", narrator)
    monkeypatch.setattr(core.RuntimeEngine, "opening", lambda _engine: SimpleNamespace(narration="Opening."))
    variation = _variation(
        RUNTIME,
        turns=2,
        inputs=["Search the kitchen.", "Carry the workstation to the truck."],
    )
    variation["fixed_refusal"] = True
    variation["engine_refusal"] = True
    result = core.run_scene(variation, "1A", variation["scripts"]["1A"][0])

    assert result["status"] == "ok"
    normal, refused = result["turns"]
    assert normal["narrator_called"] is True
    assert refused["narrator_called"] is False
    assert refused["prompt_system"] is None
    assert refused["prompt_user"] is None
    assert refused["item_facts_raw"] == {}
    assert refused["item_facts_unplaced"] == []
    assert refused["item_facts_after"] == refused["item_facts_before"]
    assert refused["engine_refusal"]
    assert refused["narration"] == refused["engine_refusal"]
    assert len([call for call in narrator_calls if call["system"].startswith("You are the narrator")]) == 1


def test_engine_refusal_variation_hash() -> None:
    baseline = core.load_variation(RUNTIME)
    absent = core.load_variation(RUNTIME)
    disabled = copy.deepcopy(json.loads(RUNTIME.read_text()))
    disabled["engine_refusal"] = False
    disabled = core.resolve_variation(disabled, RUNTIME)
    enabled = copy.deepcopy(json.loads(RUNTIME.read_text()))
    enabled["engine_refusal"] = True
    enabled = core.resolve_variation(enabled, RUNTIME)

    assert absent["_variation_hash"] == baseline["_variation_hash"]
    assert disabled["_variation_hash"] == baseline["_variation_hash"]
    assert enabled["_variation_hash"] != baseline["_variation_hash"]


def test_runtime_mode_records_rejected_turn(monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]) -> None:
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

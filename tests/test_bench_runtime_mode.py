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
import bench.jev_use as jev_use
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.contracts import NarrationSegment
from storygame.runtime.world_model import world_for

ROOT = Path(__file__).resolve().parents[1]
NORMAL = ROOT / "bench/variations/item-facts-world-two-scene.json"
RUNTIME = ROOT / "bench/variations/item-facts-world-two-scene-runtime.json"


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


def test_runtime_mode_matches_bench_mode(monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]) -> None:
    normal = _run(monkeypatch, NORMAL)
    runtime = _run(monkeypatch, RUNTIME)

    fields = (
        "player_input",
        "typed_input",
        "prompt_system",
        "prompt_user",
        "things_given",
        "item_facts_before",
        "item_facts_after",
        "item_facts_issues",
        "match_issues",
        "seating_steps",
        "seating_asked",
        "seating_issues",
        "taking_steps",
        "taking_asked",
        "taking_issues",
        "standing_steps",
        "standing_asked",
        "standing_issues",
    )
    assert [[turn[field] for field in fields] for turn in normal["turns"]] == [
        [turn[field] for field in fields] for turn in runtime["turns"]
    ]


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

    assert "Kristin searches the room." in turn["narration"]
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


def test_runtime_mode_records_steps(monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]) -> None:
    def prepare_state(state):
        world = world_for(state.package, state.facts)
        assert world.move("kristin", "kitchen").ok
        assert world.move("kristin_laptop", "kitchen").ok

    original_provider_for = core.provider_for
    original_before_turn = core.WorldCapture.before_turn

    def provider_for_with_laptop(state, variation):
        prepare_state(state)
        return original_provider_for(state, variation)

    def before_turn_with_laptop(capture, command):
        prepare_state(capture.provider.state)
        return original_before_turn(capture, command)

    monkeypatch.setattr(core, "provider_for", provider_for_with_laptop)
    monkeypatch.setattr(core.WorldCapture, "before_turn", before_turn_with_laptop)
    original_opening = core.RuntimeEngine.opening

    def opening_with_laptop_ready(engine):
        result = original_opening(engine)
        prepare_state(engine.state)
        return result

    monkeypatch.setattr(core.RuntimeEngine, "opening", opening_with_laptop_ready)
    inputs = ["Read the files on my laptop."]
    normal = _run(monkeypatch, NORMAL, turns=1, inputs=inputs)
    runtime = _run(monkeypatch, RUNTIME, turns=1, inputs=inputs)

    normal_turn = normal["turns"][0]
    runtime_turn = runtime["turns"][0]
    step_fields = (
        "seating_steps",
        "seating_asked",
        "seating_issues",
        "taking_steps",
        "taking_asked",
        "taking_issues",
        "standing_steps",
        "standing_asked",
        "standing_issues",
    )
    assert any(runtime_turn[field] for field in ("seating_steps", "taking_steps", "standing_steps")), {
        "runtime": {field: runtime_turn[field] for field in step_fields},
        "normal": {field: normal_turn[field] for field in step_fields},
    }
    assert [runtime_turn[field] for field in step_fields] == [normal_turn[field] for field in step_fields]
    steps = runtime_turn["standing_steps"] + runtime_turn["taking_steps"] + runtime_turn["seating_steps"]
    assert runtime_turn["player_input"].startswith(" ".join(steps))
    assert runtime_turn["player_input"].endswith(inputs[0])


def test_runtime_mode_builds_fresh_provider_each_turn(monkeypatch: pytest.MonkeyPatch, fake_jev: list[dict]) -> None:
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

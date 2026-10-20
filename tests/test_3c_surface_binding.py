from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from bench.core import load_variation, package_and_state
from storygame.runtime.world_model import world_for

ROOT = Path(__file__).resolve().parents[1]
PROBE_PATH = ROOT / "scripts/ringer/stage7/3c_surface_binding_probe.py"
ARM_FILES = {"control": "stage7-3c-control.json", "surface": "stage7-3c-surface-binding.json"}
SPEC = importlib.util.spec_from_file_location("surface_binding_probe", PROBE_PATH)
assert SPEC and SPEC.loader
surface_probe = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(surface_probe)


def _package(arm: str):
    variation = load_variation(ROOT / "bench/variations" / ARM_FILES[arm])
    return package_and_state(variation, "3C")


def _engine(arm: str, *, turn_index: int = 0):
    package, _ = _package(arm)
    state = surface_probe.state_3c(package, turn_index=turn_index)
    engine = surface_probe.RuntimeEngine(state, None)
    return package, engine


def _add_real_members(package, engine) -> tuple[str, ...]:
    world = world_for(package, engine.state.facts)
    members = world.members("captives")
    if not members:
        for member in ("charles", "rebecca", "senior_official"):
            result = world.place(member, "captives")
            assert result.ok, result.reason
        members = world.members("captives")
    assert members
    assert set(members).isdisjoint({"kristin", "michelle", "brandon"})
    return members


def _parents(package, engine, members):
    world = world_for(package, engine.state.facts)
    return {
        "captives": world.parent("captives"),
        "members": {member: world.area(member) for member in members},
        "people": {person: world.parent(person) for person in ("kristin", "michelle", "brandon")},
    }


def _finish_a_and_b(package, engine) -> None:
    surface_probe.reveal(engine, package, "k_sl_3c_a_r1", "Send the evidence package.")
    surface_probe.reveal(engine, package, "k_sl_3c_b_r1", "Take the Portable data case from Rebecca.")


@pytest.mark.parametrize("order", surface_probe.ORDERS)
def test_surface_binding_moves_real_group_and_members_only_after_both_c_parts(order) -> None:
    package, engine = _engine("surface")
    members = _add_real_members(package, engine)
    _finish_a_and_b(package, engine)
    commands = surface_probe.COMMANDS

    surface_probe.reveal(engine, package, order[0], commands[order[0]])
    before = _parents(package, engine, members)
    assert before["captives"] != "facility_escape"
    assert all(parent != "facility_escape" for parent in before["members"].values())

    surface_probe.reveal(engine, package, order[1], commands[order[1]])
    after = _parents(package, engine, members)
    assert after["captives"] == "facility_escape"
    assert set(after["members"].values()) == {"facility_escape"}
    assert set(after["people"].values()) == set(before["people"].values())


def test_surface_binding_c_r2_alone_does_not_move_captives() -> None:
    package, engine = _engine("surface")
    members = _add_real_members(package, engine)
    _finish_a_and_b(package, engine)
    surface_probe.reveal(engine, package, "k_sl_3c_c_r2", surface_probe.COMMANDS["k_sl_3c_c_r2"])
    state = _parents(package, engine, members)
    assert state["captives"] != "facility_escape"
    assert all(parent != "facility_escape" for parent in state["members"].values())


@pytest.mark.parametrize("arm,expected", [("surface", "facility_escape"), ("control", "maintenance_network")])
def test_surface_binding_deadline_respects_variation(arm: str, expected: str) -> None:
    package, _ = _package(arm)
    handoff = next(w for w in package.pacing.scenes if w.scene_id == "3C").handoff_after_turns
    _, engine = _engine(arm, turn_index=handoff - 1)
    members = _add_real_members(package, engine)
    engine.provider = lambda _command: {
        "segments": [{"kind": "narration", "text": "The broadcast continues."}],
        "selected_knowledge_ids": [],
    }
    engine.turn("Get everyone to the surface.")
    state = _parents(package, engine, members)
    assert state["captives"] == expected


def test_surface_binding_save_load_keeps_group_members_and_people() -> None:
    package, engine = _engine("surface")
    members = _add_real_members(package, engine)
    _finish_a_and_b(package, engine)
    for knowledge_id in surface_probe.ORDERS[0]:
        surface_probe.reveal(engine, package, knowledge_id, surface_probe.COMMANDS[knowledge_id])
    saved = _parents(package, engine, members)
    reloaded_state = surface_probe.state_3c(package)
    reloaded_state.restore_snapshot(engine.state.snapshot())
    reloaded = surface_probe.RuntimeEngine(reloaded_state, None)
    assert _parents(package, reloaded, members) == saved


def test_control_variation_never_moves_group_members_or_people() -> None:
    package, engine = _engine("control")
    members = _add_real_members(package, engine)
    _finish_a_and_b(package, engine)
    for knowledge_id in surface_probe.ORDERS[0]:
        surface_probe.reveal(engine, package, knowledge_id, surface_probe.COMMANDS[knowledge_id])
    result = _parents(package, engine, members)
    assert result["captives"] == "maintenance_network"
    assert set(result["members"].values()) == {"maintenance_network"}
    assert (
        result["people"]
        == _parents(package, surface_probe.RuntimeEngine(surface_probe.state_3c(package), None), ())["people"]
    )

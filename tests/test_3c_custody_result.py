from __future__ import annotations

from pathlib import Path

import pytest

from bench.core import load_variation, package_and_state
from scripts.ringer.stage7 import three_c_probe as probe
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.world_model import world_for

ROOT = Path(__file__).resolve().parents[1]


def _package(arm: str):
    return package_and_state(load_variation(probe.variation_paths((arm,))[arm]), "3C")


def _provider(package, knowledge_id: str):
    knowledge = package.knowledge_indexes.by_id[knowledge_id]
    return lambda _command: {
        "segments": [{"kind": "narration", "text": knowledge.delivery_text or knowledge.statement}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _state_with_entry_facts(state):
    probe.assert_3c_entry_facts(state)
    return state


def _finish_a_and_b(arm: str):
    package, state = _package(arm)
    _state_with_entry_facts(state)
    engine = RuntimeEngine(state, _provider(package, "k_sl_3c_a_r1"))
    engine.turn("Send the evidence package.")
    engine._activate_pacing()  # noqa: SLF001
    engine.provider = _provider(package, "k_sl_3c_b_r1")
    engine.turn("Take the Portable data case from Rebecca.")
    return package, engine


def _mask(value, replacements):
    if isinstance(value, dict):
        return {key: _mask(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask(item, replacements) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask(item, replacements) for item in value)
    return replacements.get(value, value)


def test_custody_variation_changes_only_entry_text_and_b_r1_delivery() -> None:
    control, _ = _package("control")
    entry, _ = _package("entry")
    custody, _ = _package("custody")
    entry_scene = next(scene for scene in entry.scenes if scene.metadata.scene_id == "3C")
    custody_scene = next(scene for scene in custody.scenes if scene.metadata.scene_id == "3C")
    entry_b = entry.knowledge_indexes.by_id["k_sl_3c_b_r1"]
    custody_b = custody.knowledge_indexes.by_id["k_sl_3c_b_r1"]

    entry_payload = entry.model_dump()
    custody_payload = custody.model_dump()
    replacements = {
        entry_scene.metadata.entry_text: "<entry>",
        custody_scene.metadata.entry_text: "<entry>",
        entry_b.delivery_text: "<b>",
        custody_b.delivery_text: "<b>",
    }
    entry_payload = _mask(entry_payload, replacements)
    custody_payload = _mask(custody_payload, replacements)
    assert entry_payload == custody_payload

    control_scene = next(scene for scene in control.scenes if scene.metadata.scene_id == "3C")
    control_b = control.knowledge_indexes.by_id["k_sl_3c_b_r1"]
    assert control_scene.metadata.entry_text != custody_scene.metadata.entry_text
    assert control_b.delivery_text != custody_b.delivery_text
    assert entry_b.delivery_text != custody_b.delivery_text
    assert probe.source_proof(("entry", "custody"))["plot_md"]["replacement"]["matches"] == 1
    assert probe.source_proof(("entry", "custody"))["knowledge_yaml"]["custody_b_r1_replacement"]["matches"] == 1


@pytest.mark.parametrize("arm", ("entry", "custody"))
def test_b_commit_keeps_case_with_kristin_without_c_parts(arm: str) -> None:
    package, engine = _finish_a_and_b(arm)
    world = world_for(package, engine.state.facts)
    assert world.parent(probe.CASE_ENTITY_ID) == "kristin"
    assert not any(fact.predicate == "captives_reaching_surface" for fact in engine.state.facts.asserted)
    assert not any(fact.predicate.startswith("k_sl_3c_c") for fact in engine.state.facts.asserted)


def test_replaying_take_case_with_no_world_change_keeps_kristin_parent() -> None:
    package, engine = _finish_a_and_b("custody")
    engine.provider = lambda _command: {"segments": [{"kind": "narration", "text": "No change."}]}
    engine.turn("Take the Portable data case from Rebecca.")
    assert world_for(package, engine.state.facts).parent(probe.CASE_ENTITY_ID) == "kristin"


@pytest.mark.parametrize("arm", ("entry", "custody"))
def test_posta_preflight_is_exactly_b_r1_and_b_r2(arm: str) -> None:
    package, state = _package(arm)
    _state_with_entry_facts(state)
    prefix = probe.apply_posta_prefix(package, state)
    assert prefix["committed_reveal_ids"] == ["k_sl_3c_a_r1"]
    assert state.turn_index == 1
    assert probe.preflight_reveal_universe(RuntimeEngine(state, None), state, "posta") == [
        "k_sl_3c_b_r1",
        "k_sl_3c_b_r2",
    ]

from __future__ import annotations

from bench.core import load_variation, package_and_state
from scripts.ringer.stage7 import three_c_probe as probe
from storygame.runtime.engine import RuntimeEngine


def _package(arm: str):
    return package_and_state(load_variation(probe.variation_paths((arm,))[arm]), "3C")


def _provider(package, knowledge_id: str):
    knowledge = package.knowledge_indexes.by_id[knowledge_id]
    return lambda _command: {
        "segments": [{"kind": "narration", "text": knowledge.delivery_text or knowledge.statement}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _mask(value, replacements):
    if isinstance(value, dict):
        return {key: _mask(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [_mask(item, replacements) for item in value]
    if isinstance(value, tuple):
        return tuple(_mask(item, replacements) for item in value)
    return replacements.get(value, value)


def test_pump_changes_only_b_r1_delivery_and_sentence_occurs_once() -> None:
    custody, _ = _package("custody")
    pump, _ = _package("pump")
    custody_scene = next(scene for scene in custody.scenes if scene.metadata.scene_id == "3C")
    pump_scene = next(scene for scene in pump.scenes if scene.metadata.scene_id == "3C")
    custody_b = custody.knowledge_indexes.by_id["k_sl_3c_b_r1"]
    pump_b = pump.knowledge_indexes.by_id["k_sl_3c_b_r1"]
    assert pump_b.delivery_text.count("The drainage pumps need power. ") == 1
    replacements = {
        custody_scene.metadata.entry_text: "<entry>",
        pump_scene.metadata.entry_text: "<entry>",
        custody_b.delivery_text: "<b>",
        pump_b.delivery_text: "<b>",
    }
    assert _mask(custody.model_dump(), replacements) == _mask(pump.model_dump(), replacements)
    assert custody_b.delivery_text != pump_b.delivery_text


def test_b_r1_does_not_grant_c_parts_or_surface_fact() -> None:
    for arm in ("custody", "pump"):
        package, state = _package(arm)
        probe.assert_3c_entry_facts(state)
        engine = RuntimeEngine(state, _provider(package, "k_sl_3c_a_r1"))
        engine.turn("Send the evidence package.")
        engine._activate_pacing()  # noqa: SLF001
        engine.provider = _provider(package, "k_sl_3c_b_r1")
        engine.turn("Take the Portable data case from Rebecca.")
        assert not any(fact.predicate.startswith("k_sl_3c_c") for fact in state.facts.asserted)
        assert not any(fact.predicate == "captives_reaching_surface" for fact in state.facts.asserted)


def test_c2_then_c1_keeps_surface_false_until_both_commit() -> None:
    for arm in ("custody", "pump"):
        package, state = _package(arm)
        probe.assert_3c_entry_facts(state)
        engine = RuntimeEngine(state, _provider(package, "k_sl_3c_a_r1"))
        engine.turn("Send the evidence package.")
        engine._activate_pacing()  # noqa: SLF001
        engine.provider = _provider(package, "k_sl_3c_b_r1")
        engine.turn("Take the Portable data case from Rebecca.")
        engine._activate_pacing()  # noqa: SLF001
        engine.provider = _provider(package, "k_sl_3c_c_r2")
        engine.turn("Open the surface gates.")
        assert not any(fact.predicate == "captives_reaching_surface" for fact in state.facts.asserted)
        engine._activate_pacing()  # noqa: SLF001
        engine.provider = _provider(package, "k_sl_3c_c_r1")
        engine.turn("Restore the drainage pumps.")
        assert any(fact.predicate == "captives_reaching_surface" for fact in state.facts.asserted)


def test_c_metrics_on_fabricated_rows() -> None:
    both = {
        "turns": [
            {"scene_turn": 9, "committed_reveals": ["k_sl_3c_c_r2"]},
            {"scene_turn": 10, "committed_reveals": ["k_sl_3c_c_r1"]},
        ]
    }
    gate_only = {
        "turns": [
            {
                "scene_turn": 9,
                "committed_reveals": ["k_sl_3c_c_r2"],
                "story_fact_delta": {"added": ["captives_reaching_surface"]},
            }
        ]
    }
    assert probe.both_c_by_turn_10(both) is True
    assert probe.gate_only_escape(both) is False
    assert probe.both_c_by_turn_10(gate_only) is False
    assert probe.gate_only_escape(gate_only) is True

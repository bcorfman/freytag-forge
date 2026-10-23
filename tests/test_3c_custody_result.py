from __future__ import annotations

from pathlib import Path

import pytest

from bench.core import load_variation, package_and_state
from scripts.ringer.stage7 import three_c_probe as probe
from storygame.runtime.engine import RuntimeEngine

ROOT = Path(__file__).resolve().parents[1]


def _package(arm: str):
    variation = (
        probe.pre_adoption_variation() if arm == "pre-adoption" else load_variation(probe.variation_paths((arm,))[arm])
    )
    return package_and_state(variation, "3C")


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

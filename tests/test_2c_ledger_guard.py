from __future__ import annotations

import copy
import re
from pathlib import Path

import pytest
import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package import load_story_package
from storygame.story_source.compiler import SourceError
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy

PACKAGE = Path("data/stories/continuity-initiative")


class _ScriptedProvider:
    def __init__(self, package) -> None:
        self.package = package
        self.selected: list[str] = []

    def __call__(self, _player_input: str) -> dict[str, object]:
        text = "A concrete authored consequence lands."
        if self.selected:
            knowledge = self.package.knowledge_indexes.by_id[self.selected[0]]
            text = knowledge.delivery_text or knowledge.statement
        return {
            "segments": [{"kind": "narration", "text": text, "grounding_ids": list(self.selected)}],
            "selected_knowledge_ids": list(self.selected),
        }


def _drive(engine: RuntimeEngine, provider: _ScriptedProvider, selection: str | None) -> None:
    provider.selected = [selection] if selection else []
    command = {
        "k_sl_1b_d_r1": "Look under the park bench.",
        "k_sl_1b_b_r2": "Ask the man about Michelle.",
        "k_sl_1b_c_r1": "Open the service gate.",
    }.get(selection, "Act on the strongest available lead.")
    engine.turn(command)


def _true_facts(state: RuntimeState) -> set[str]:
    return {fact.predicate for fact in state.facts.asserted if str(fact.value).lower() == "true"}


@pytest.mark.parametrize(
    ("selection", "expected_fact", "unexpected_fact"),
    [
        ("k_sl_2b_b_r5", "brandon_name_erased", "brandon_name_kept"),
        ("k_sl_2b_b_r4", "brandon_name_kept", "brandon_name_erased"),
    ],
)
def test_2b_outcome_blocks_late_audit_recovery(selection: str, expected_fact: str, unexpected_fact: str) -> None:
    package = load_story_package(PACKAGE)
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)

    prefix = [
        "k_sl_1a_a_r1",
        "k_sl_1a_b_r0",
        None,
        None,
        "k_sl_1a_b_r1",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        "k_sl_1b_d_r1",
        "k_sl_1b_b_r2",
        "k_sl_1b_c_r1",
        None,
        None,
        None,
        None,
        None,
        "k_sl_1c_a_r1",
        "k_sl_1c_b_r1",
        "k_sl_1c_c_copy_numbers",
        "k_sl_2a_b_r1",
        None,
        None,
        None,
        None,
        None,
        "k_sl_2a_c_r5",
    ]
    for item in prefix:
        if item == "k_sl_1a_b_r1":
            world = world_for(package, state.facts)
            assert world.move("kristin_laptop", "truck_passenger_seat").ok
            assert world.move("kristin", "truck_driver_seat").ok
        _drive(engine, provider, item)

    assert state.current_scene_id == "2B"
    for item in ["k_sl_2b_a_r1", None, None, None, None, None, None, selection]:
        _drive(engine, provider, item)
        facts = _true_facts(state)
        assert "audit_recovery_ready" not in facts
        if item == selection:
            assert expected_fact in facts
            assert unexpected_fact not in facts


def test_loader_documents_unproducible_positive_ledger_gate(tmp_path: Path) -> None:
    root = compiled_story_copy(tmp_path)

    scene_source = root / "source" / "scenes" / "2C.yaml"
    scene = yaml.safe_load(scene_source.read_text(encoding="utf-8"))
    reveal = next(item for item in scene["reveals"] if item["storylet_id"] == "SL-2C-C")
    sibling = copy.deepcopy(reveal["variants"]["r1"])
    sibling["realization_id"] = "SL-2C-C-R2"
    sibling["claim_id"] = "k_sl_2c_c_r2"
    sibling["when"] = {**sibling["when"], "brandon_name_erased": True}
    reveal["variants"]["r2"] = sibling
    scene_source.write_text(yaml.safe_dump(scene, sort_keys=False, allow_unicode=True), encoding="utf-8")

    match_source = root / "source" / "scenes" / "2C.match.yaml"
    match = yaml.safe_load(match_source.read_text(encoding="utf-8"))
    match["claims"]["k_sl_2c_c_r2"] = copy.deepcopy(match["claims"]["k_sl_2c_c_r1"])
    match_source.write_text(yaml.safe_dump(match, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(
        SourceError,
        match=re.escape(
            "scene 2C reveal 'k_sl_2c_c_r2' requires 'brandon_name_erased', which scene entry does not guarantee "
            "and the scene cannot produce"
        ),
    ):
        load_compiled_copy(root)

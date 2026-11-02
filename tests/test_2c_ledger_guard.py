from __future__ import annotations

import copy
import re
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package import StoryPackageError, load_story_package

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
    engine.turn("Act on the strongest available lead.")


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
        "k_sl_1b_d_r1",
        "k_sl_1b_b_r1",
        "k_sl_1b_c_r1",
        None,
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
    root = tmp_path / "package"
    shutil.copytree(PACKAGE, root)

    knowledge_source = root / "knowledge.yaml"
    catalog = yaml.safe_load(knowledge_source.read_text(encoding="utf-8"))
    original = next(item for item in catalog["knowledge"] if item["id"] == "k_sl_2c_c_r1")
    sibling = copy.deepcopy(original)
    sibling["id"] = "k_sl_2c_c_r2"
    sibling["requires"] = [*sibling["requires"], {"fact_id": "brandon_name_erased", "equals": True}]
    sibling["source"]["realization_id"] = "SL-2C-C-R2"
    catalog["knowledge"].append(sibling)
    knowledge_source.write_text(yaml.safe_dump(catalog, sort_keys=False, allow_unicode=True), encoding="utf-8")

    routes_source = root / "storylet-routes.yaml"
    routes = yaml.safe_load(routes_source.read_text(encoding="utf-8"))
    route = next(route for route in routes["storylets"] if route["id"] == "SL-2C-C")
    realization = copy.deepcopy(route["realization_options"][0])
    realization["id"] = "SL-2C-C-R2"
    route["realization_options"].append(realization)
    routes_source.write_text(yaml.safe_dump(routes, sort_keys=False, allow_unicode=True), encoding="utf-8")

    with pytest.raises(
        StoryPackageError,
        match=re.escape(
            "scene 2C reveal 'k_sl_2c_c_r2' requires 'brandon_name_erased', which scene entry does not guarantee "
            "and the scene cannot produce"
        ),
    ):
        load_story_package(root)

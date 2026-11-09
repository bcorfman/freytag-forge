from __future__ import annotations

import json
import shutil
from pathlib import Path
from unittest.mock import patch

import yaml

from storygame.audit_budget import (
    _PLAYER_INPUT,
    _state_for,
    deep_turn_budget,
    report,
)
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.story_package.loader import load_story_package
from tests.test_audit_budget import LIGHTHOUSE

REAL_PACKAGE = Path("data/stories/continuity-initiative")
FIXTURE = Path("tests/fixtures/deep_turn_budget.json")


def _branch_package(tmp_path: Path, *, contradictory: bool) -> Path:
    root = tmp_path / "lighthouse"
    shutil.copytree(LIGHTHOUSE, root)

    knowledge_path = root / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    knowledge["facts"].append({"id": "branch_state", "purpose": "Which branch is active."})
    knowledge["facts"].append({"id": "branch_true_known", "purpose": "The true branch is known."})
    knowledge["facts"].append({"id": "branch_false_known", "purpose": "The false branch is known."})
    knowledge["knowledge"][0]["establishes"].append({"op": "assert", "fact_id": "branch_state", "value": True})
    branch_entries = [
        {
            "id": "k_branch_true",
            "statement": "Ada saw the true branch.",
            "entity_ids": ["brass_key"],
            "aliases": ["true branch"],
            "audience": {"kind": "public", "player_visible": True},
            "available_in_scenes": ["1A"],
            "requires": [{"fact_id": "branch_state", "equals": True}],
            "establishes": [{"op": "assert", "fact_id": "branch_true_known", "value": True}],
            "source": {
                "kind": "storylet_realization",
                "storylet_id": "SL-1A-A",
                "realization_id": "r0",
            },
        },
        {
            "id": "k_branch_false",
            "statement": "Ada saw the false branch.",
            "entity_ids": ["brass_key"],
            "aliases": ["false branch"],
            "audience": {"kind": "public", "player_visible": True},
            "available_in_scenes": ["1A"],
            "establishes": [{"op": "assert", "fact_id": "branch_false_known", "value": True}],
            "source": {
                "kind": "storylet_realization",
                "storylet_id": "SL-1A-A",
                "realization_id": "r0",
            },
        },
    ]
    if contradictory:
        branch_entries[1]["requires"] = [{"fact_id": "branch_state", "equals": False}]
    knowledge["knowledge"].extend(branch_entries)
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

    world_path = root / "world.yaml"
    world = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    world["facts"].append("branch_state")
    world["facts"].append("branch_true_known")
    world["facts"].append("branch_false_known")
    world_path.write_text(yaml.safe_dump(world, sort_keys=False), encoding="utf-8")

    routes_path = root / "storylet-routes.yaml"
    routes = yaml.safe_load(routes_path.read_text(encoding="utf-8"))
    routes["storylets"][0]["realization_options"][0]["operations"].extend(
        [
            {"op": "assert", "fact_id": "branch_state", "value": True},
            {"op": "assert", "fact_id": "branch_true_known", "value": True},
            {"op": "assert", "fact_id": "branch_false_known", "value": True},
        ]
    )
    routes_path.write_text(yaml.safe_dump(routes, sort_keys=False), encoding="utf-8")
    return root


def _prompt_text(package: Path, scene_id: str) -> str:
    state, _ = _state_for(load_story_package(package), scene_id, one_per_storylet=False)
    provider = ItemFactsProvider(
        worker_url="https://worker.example/turn",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )
    with patch.object(
        CloudflareTurnProvider,
        "_request_item_facts",
        return_value={"refers": [], "same_as": {}, "kind": {}},
    ):
        provider.prepare_turn(_PLAYER_INPUT)
    prompt = provider.assemble_turn_prompt(_PLAYER_INPUT)
    return prompt["system"] + provider._section_user_prompt(prompt["context"])


def test_contradictory_requires_count_once_in_all_alternates(tmp_path: Path) -> None:
    contradictory = deep_turn_budget(_branch_package(tmp_path / "contradictory", contradictory=True), "1A")
    non_contradictory = deep_turn_budget(_branch_package(tmp_path / "non-contradictory", contradictory=False), "1A")

    assert contradictory["narration_chars_all_alternates"] < non_contradictory["narration_chars_all_alternates"]
    assert contradictory["narration_chars"] == non_contradictory["narration_chars"]


def test_non_contradictory_alternates_still_count_control(tmp_path: Path) -> None:
    result = deep_turn_budget(_branch_package(tmp_path, contradictory=False), "1A")

    assert result["narration_chars_all_alternates"] > result["narration_chars"]


def test_real_1a_all_alternates_prompt_omits_the_branch_statement() -> None:
    prompt = _prompt_text(REAL_PACKAGE, "1A")
    package = load_story_package(REAL_PACKAGE)
    statements = {
        entry.id: entry.statement
        for entry in package.knowledge.knowledge
        if entry.id in {"k_sl_1a_j_r1", "k_sl_1a_j_r2", "k_sl_1a_j_r3"}
    }

    assert statements["k_sl_1a_j_r2"] not in prompt
    assert statements["k_sl_1a_j_r1"] in prompt
    assert statements["k_sl_1a_j_r3"] in prompt


def test_real_package_pins_are_unchanged_control() -> None:
    pinned = json.loads(FIXTURE.read_text(encoding="utf-8"))["scenes"]
    rows = {row["scene_id"]: row for row in report(REAL_PACKAGE)}

    assert pinned["1A"] == {"narration_chars": 5485, "narration_chars_all_alternates": 5597}
    for scene_id, expected in pinned.items():
        assert rows[scene_id]["narration_chars"] <= expected["narration_chars"]
        assert rows[scene_id]["narration_chars_all_alternates"] <= expected["narration_chars_all_alternates"]

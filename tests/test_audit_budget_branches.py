from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from storygame.audit_budget import (
    _PLAYER_INPUT,
    _state_for,
    deep_turn_budget,
    report,
)
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import DELETE, compiled_story_copy, patch_source

REAL_PACKAGE = Path("data/stories/continuity-initiative")
FIXTURE = Path("tests/fixtures/deep_turn_budget.json")


def _branch_package(tmp_path: Path, *, contradictory: bool) -> Path:
    root = compiled_story_copy(tmp_path)
    source = root / "source"
    patch_source(source, "scenes/1A.yaml", "facts.branch_state", {"purpose": "Which branch is active."})
    patch_source(source, "scenes/1A.yaml", "facts.branch_true_known", {"purpose": "The true branch is known."})
    patch_source(source, "scenes/1A.yaml", "facts.branch_false_known", {"purpose": "The false branch is known."})
    patch_source(
        source,
        "scenes/1A.yaml",
        "reveals[sl_1a_a].variants.r1.commits.branch_state",
        True,
    )
    branch_variants = [
        {
            "realization_id": "SL-1A-A-R2",
            "intent": "Record the true branch.",
            "when": {"branch_state": True},
            "commits": {"branch_true_known": True},
            "helps_exit": [],
            "from_outline": ["1A.1"],
            "claim_id": "k_branch_true",
            "says": "Ada saw the true branch.",
            "entities": ["kristin"],
            "reach": [],
            "relevance": {"entity_ids": [], "priority": 0},
            "audience": {"kind": "public", "character_ids": [], "player_visible": True},
            "voiceable": True,
            "repeatable": False,
            "text": "Ada saw the true branch.",
            "earn_when": "looks for the true branch",
        },
        {
            "realization_id": "SL-1A-A-R3",
            "intent": "Record the false branch.",
            "when": {"branch_state": False},
            "commits": {"branch_false_known": True},
            "helps_exit": [],
            "from_outline": ["1A.1"],
            "claim_id": "k_branch_false",
            "says": "Ada saw the false branch.",
            "entities": ["kristin"],
            "reach": [],
            "relevance": {"entity_ids": [], "priority": 0},
            "audience": {"kind": "public", "character_ids": [], "player_visible": True},
            "voiceable": True,
            "repeatable": False,
            "text": "Ada saw the false branch.",
            "earn_when": "looks for the false branch",
        },
    ]
    for key, variant in zip(("r2", "r3"), branch_variants, strict=True):
        patch_source(source, "scenes/1A.yaml", f"reveals[sl_1a_a].variants.{key}", variant)
    patch_source(
        source,
        "scenes/1A.match.yaml",
        "claims.k_branch_true",
        {"aliases": ["true branch"], "action_evidence": [["see"]], "must_convey": [["true branch"]]},
    )
    patch_source(
        source,
        "scenes/1A.match.yaml",
        "claims.k_branch_false",
        {"aliases": ["false branch"], "action_evidence": [["see"]], "must_convey": [["false branch"]]},
    )
    if contradictory:
        patch_source(source, "scenes/1A.yaml", "reveals[sl_1a_a].variants.r3.when", {"branch_state": False})
    else:
        patch_source(source, "scenes/1A.yaml", "reveals[sl_1a_a].variants.r3.when", DELETE)
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

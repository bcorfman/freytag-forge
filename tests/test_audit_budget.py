from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest
import yaml

from storygame.audit_budget import deep_turn_budget, report
from storygame.story_package.loader import load_story_package

LIGHTHOUSE = Path("tests/fixtures/stories/lighthouse-keeper")
REAL_PACKAGE = Path("data/stories/continuity-initiative")
FIXTURE = Path("tests/fixtures/deep_turn_budget.json")
KNOWN_OVER_BUDGET = frozenset({"3A", "3B", "3C"})  # O8 in .plans/richer-3a-open-issues-plan.md.


def _package(tmp_path: Path, *, alternate: bool = False, with_knowledge: bool = True) -> Path:
    root = tmp_path / "lighthouse"
    shutil.copytree(LIGHTHOUSE, root)
    knowledge_path = root / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    knowledge["facts"].append({"id": "deep_statement_known", "purpose": "Ada knows the deep statement."})
    knowledge["facts"].append({"id": "deep_statement_alt_known", "purpose": "Ada knows the alternate statement."})
    knowledge["knowledge"][0]["establishes"] = [{"op": "assert", "fact_id": "deep_statement_known", "value": True}]
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

    world_path = root / "world.yaml"
    world = yaml.safe_load(world_path.read_text(encoding="utf-8"))
    world["facts"].append("deep_statement_known")
    world["facts"].append("deep_statement_alt_known")
    world_path.write_text(yaml.safe_dump(world, sort_keys=False), encoding="utf-8")

    routes_path = root / "storylet-routes.yaml"
    routes = yaml.safe_load(routes_path.read_text(encoding="utf-8"))
    routes["storylets"][0]["realization_options"][0]["operations"] = [
        {"op": "assert", "fact_id": "deep_statement_known", "value": True}
    ]
    routes["canonical_bridge_events"][0]["activation"]["all_facts_true"] = ["deep_statement_known"]
    routes_path.write_text(yaml.safe_dump(routes, sort_keys=False), encoding="utf-8")

    pacing_path = root / "pacing.yaml"
    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    pacing["transitions"][0]["triggers"][0]["fact_id"] = "deep_statement_known"
    pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")

    handoffs_path = root / "handoffs.yaml"
    handoffs = yaml.safe_load(handoffs_path.read_text(encoding="utf-8"))
    handoffs["deliveries"][0]["fact_id"] = "deep_statement_known"
    handoffs_path.write_text(yaml.safe_dump(handoffs, sort_keys=False), encoding="utf-8")

    if not with_knowledge:
        knowledge["knowledge"][0]["audience"]["player_visible"] = False
        handoffs_path.write_text("deliveries: []\n", encoding="utf-8")
        pacing["transitions"] = []
        pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")
        routes["canonical_bridge_events"] = []
        routes_path.write_text(yaml.safe_dump(routes, sort_keys=False), encoding="utf-8")
        plot_path = root / "plot.md"
        plot_text = plot_path.read_text(encoding="utf-8")
        plot_text = plot_text.replace("transition_ids: [t_1a_1b]", "transition_ids: []")
        plot_text = plot_text.replace(
            "bridge_text:\n  t_1a_1b: Ada carries the lantern into the lamp room.", "bridge_text: {}"
        )
        plot_path.write_text(plot_text, encoding="utf-8")
        knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")
    if alternate:
        knowledge["knowledge"].append(
            {
                "id": "k_find_key_alt",
                "statement": "Ada finds the brass key beneath the bench.",
                "entity_ids": ["brass_key"],
                "aliases": ["brass key beneath bench"],
                "audience": {"kind": "public", "player_visible": True},
                "available_in_scenes": ["1A"],
                "establishes": [{"op": "assert", "fact_id": "deep_statement_alt_known", "value": True}],
                "must_convey": [["brass key"]],
                "source": {
                    "kind": "storylet_realization",
                    "storylet_id": "SL-1A-A",
                    "realization_id": "r1",
                },
            }
        )
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")
    if alternate:
        routes = yaml.safe_load(routes_path.read_text(encoding="utf-8"))
        routes["storylets"][0]["realization_options"].append(
            {
                "id": "r1",
                "dramatic_intent": "Find the key another way.",
                "operations": [{"op": "assert", "fact_id": "deep_statement_alt_known", "value": True}],
            }
        )
        routes_path.write_text(yaml.safe_dump(routes, sort_keys=False), encoding="utf-8")
    return root


def test_established_knowledge_makes_the_deep_prompt_longer(tmp_path: Path) -> None:
    without_knowledge = deep_turn_budget(_package(tmp_path / "without", with_knowledge=False), "1A")
    with_knowledge = deep_turn_budget(_package(tmp_path / "with"), "1A")

    assert with_knowledge["established_entries"] > without_knowledge["established_entries"]
    assert with_knowledge["narration_chars"] > without_knowledge["narration_chars"]


def test_all_alternates_are_reported_and_make_the_prompt_larger(tmp_path: Path) -> None:
    result = deep_turn_budget(_package(tmp_path, alternate=True), "1A")

    assert result["alternate_pairs"] == ["SL-1A-A"]
    assert result["narration_chars_all_alternates"] > result["narration_chars"]


def test_report_is_deterministic(tmp_path: Path) -> None:
    package = _package(tmp_path)

    assert report(package) == report(package)


def test_real_package_ratchet() -> None:
    if not FIXTURE.exists():
        pytest.fail(f"{FIXTURE} is missing; run python -m storygame.audit_budget --write")
    pinned = json.loads(FIXTURE.read_text(encoding="utf-8"))
    rows = report(REAL_PACKAGE)
    actual = {row["scene_id"]: row for row in rows}

    for scene_id, expected in pinned.get("scenes", {}).items():
        assert scene_id in actual, f"fixture scene {scene_id!r} is not in the current package"
        for key in ("narration_chars", "narration_chars_all_alternates"):
            old_pin = expected[key]
            new_value = actual[scene_id][key]
            assert new_value <= old_pin, f"{scene_id}: old pin {old_pin}, new value {new_value}"

    assert all(row["entry_narration_chars"] <= row["narration_chars"] for row in rows), "entry turn exceeds deep turn"

    expected_scenes = {scene.metadata.scene_id for scene in load_story_package(REAL_PACKAGE).scenes}
    missing = expected_scenes - set(pinned.get("scenes", {}))
    assert not missing, f"fixture is missing scenes {sorted(missing)}; run python -m storygame.audit_budget --write"

    over_budget = {scene_id for scene_id, row in actual.items() if row["narration_chars"] > 6500}
    assert over_budget <= KNOWN_OVER_BUDGET

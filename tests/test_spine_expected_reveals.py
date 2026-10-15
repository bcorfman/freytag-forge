from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

FRONTEND_ROOT = Path("frontend/e2e")
PACKAGE_ROOT = Path("data/stories/continuity-initiative")
SCENE_IDS = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def _scene_prompts() -> dict[str, list[str]]:
    source = (FRONTEND_ROOT / "canon-journey.js").read_text()
    scenes: dict[str, list[str]] = {}
    scene_block = re.search(r"export const scenePrompts = \{(?P<body>.*?)\n\};", source, re.DOTALL)
    assert scene_block, "Could not find scenePrompts in canon-journey.js."
    arrays = list(re.finditer(r'"(?P<scene>[123][ABC])"\s*:\s*\[(?P<body>.*?)\]', scene_block.group("body"), re.DOTALL))
    assert {match.group("scene") for match in arrays} == set(SCENE_IDS)
    for match in arrays:
        scene = match.group("scene")
        body = match.group("body")
        strings = list(re.finditer(r'"(?:\\.|[^"\\])*"', body))
        remainder = re.sub(r'"(?:\\.|[^"\\])*"', "", body)
        assert not remainder.strip(" \t\r\n,"), f'The "{scene}" array contains non-string content.'
        scenes[scene] = [json.loads(string.group(0)) for string in strings]
    return scenes


def _knowledge() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


def _matches(knowledge: dict[str, dict], scene: str, command: str) -> set[str]:
    return {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith(f"k_sl_{scene.lower()}")
        and item.get("action_evidence")
        and _matches_all(tuple(tuple(group) for group in item["action_evidence"]), command)
    }


def test_expected_reveal_mapping_has_current_scene_ids_and_matches_prompts() -> None:
    prompts = _scene_prompts()
    expected = json.loads((FRONTEND_ROOT / "spine-expected-reveals.json").read_text())
    knowledge = _knowledge()

    assert set(expected) == set(prompts)
    recomputed = {
        scene: sorted({item_id for prompt in scene_prompts for item_id in _matches(knowledge, scene, prompt)})
        for scene, scene_prompts in prompts.items()
    }
    assert expected == recomputed


def test_expected_reveal_ids_exist_and_include_2c_c_r2() -> None:
    expected = json.loads((FRONTEND_ROOT / "spine-expected-reveals.json").read_text())
    knowledge = _knowledge()

    assert all(item_id in knowledge for ids in expected.values() for item_id in ids)
    assert "k_sl_2c_c_r2" in expected["2C"]

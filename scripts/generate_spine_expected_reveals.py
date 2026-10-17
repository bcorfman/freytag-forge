from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

FRONTEND_ROOT = Path("frontend/e2e")
PACKAGE_ROOT = Path("data/stories/continuity-initiative")
SCENE_IDS = ("1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C")


def scene_prompts() -> dict[str, list[str]]:
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


def knowledge_items() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


def matching_reveals(knowledge: dict[str, dict], scene: str, command: str) -> set[str]:
    return {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith(f"k_sl_{scene.lower()}")
        and item.get("action_evidence")
        and _matches_all(tuple(tuple(group) for group in item["action_evidence"]), command)
    }


def expected_reveals(prompts: dict[str, list[str]], knowledge: dict[str, dict]) -> dict[str, list[str]]:
    """Select player-visible realizations in prompt order, spending each storylet once.

    Package order breaks simultaneous matches, as the scripted walk does. A
    losing reveal needs its own prompt; matching it alone is not a commitment.
    This is an offline expectation, not a simulation of pacing or narration.
    """
    expected = {}
    spent = set()
    for scene, commands in prompts.items():
        selected = []
        for command in commands:
            matches = matching_reveals(knowledge, scene, command)
            for item_id, item in knowledge.items():
                audience = item.get("audience", {})
                if item_id not in matches:
                    continue
                source = item["source"]["storylet_id"]
                if audience.get("kind") == "world_only" or not audience.get("player_visible", False) or source in spent:
                    continue
                selected.append(item_id)
                spent.add(source)
                break
        expected[scene] = sorted(selected)
    return expected


def main() -> None:
    expected = expected_reveals(scene_prompts(), knowledge_items())
    assert "k_sl_2c_c_r2" in expected["2C"]
    (FRONTEND_ROOT / "spine-expected-reveals.json").write_text(json.dumps(expected, indent=2) + "\n")


if __name__ == "__main__":
    main()

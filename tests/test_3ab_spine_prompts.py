from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

FRONTEND_ROOT = Path("frontend/e2e")
PACKAGE_ROOT = Path("data/stories/continuity-initiative")


def _scene_prompts(scene: str, expected_count: int) -> list[str]:
    source = (FRONTEND_ROOT / "canon-journey.js").read_text()
    match = re.search(rf'"{scene}"\s*:\s*\[(?P<body>.*?)\]', source, re.DOTALL)
    assert match, f'Could not find the "{scene}" prompt array in canon-journey.js.'

    body = match.group("body")
    strings = list(re.finditer(r'"(?:\\.|[^"\\])*"', body))
    assert len(strings) == expected_count, (
        f'Expected exactly {expected_count} strings in "{scene}", found {len(strings)}.'
    )
    remainder = re.sub(r'"(?:\\.|[^"\\])*"', "", body)
    assert not remainder.strip(" \t\r\n,"), f'The "{scene}" array contains non-string content.'
    return [json.loads(string.group(0)) for string in strings]


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


def _required_fact_ids(item: dict) -> set[str]:
    return {requirement["fact_id"] for requirement in item.get("requires", [])}


def _established_fact_ids(knowledge: dict[str, dict], item_ids: set[str]) -> set[str]:
    return {fact["fact_id"] for item_id in item_ids for fact in knowledge[item_id].get("establishes", [])}


def _assert_scene_spine(
    knowledge: dict[str, dict],
    scene: str,
    prompts: list[str],
    expected: list[set[str]],
) -> None:
    matched = [_matches(knowledge, scene, prompt) for prompt in prompts]
    assert matched == expected

    established: set[str] = set()
    for prompt_number, item_ids in enumerate(matched, start=1):
        required = {fact_id for item_id in item_ids for fact_id in _required_fact_ids(knowledge[item_id])}
        assert required <= established, (
            f"{scene} prompt {prompt_number} requires facts not established earlier: {sorted(required - established)}"
        )
        established |= _established_fact_ids(knowledge, item_ids)


def test_3a_spine_prompts_match_their_authored_reveals_in_order() -> None:
    knowledge = _knowledge()
    prompts = _scene_prompts("3A", 4)
    _assert_scene_spine(
        knowledge,
        "3A",
        prompts,
        [
            {"k_sl_3a_a_r1"},
            {"k_sl_3a_b_r2"},
            {"k_sl_3a_d_r1"},
            {"k_sl_3a_c_r1"},
        ],
    )


def test_3b_spine_prompts_match_their_authored_reveals_in_order() -> None:
    knowledge = _knowledge()
    prompts = _scene_prompts("3B", 5)
    _assert_scene_spine(
        knowledge,
        "3B",
        prompts,
        [
            {"k_sl_3b_a_r1"},
            {"k_sl_3b_e_r1"},
            {"k_sl_3b_b_r2"},
            {"k_sl_3b_d_r1"},
            {"k_sl_3b_c_r1"},
        ],
    )

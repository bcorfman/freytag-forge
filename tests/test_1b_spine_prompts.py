from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from storygame.runtime.candidate_matcher import _matches_all

FRONTEND_ROOT = Path("frontend/e2e")
PACKAGE_ROOT = Path("data/stories/continuity-initiative")


def _scene_prompts() -> list[str]:
    source = (FRONTEND_ROOT / "canon-journey.js").read_text()
    match = re.search(r'"1B"\s*:\s*\[(?P<body>.*?)\]', source, re.DOTALL)
    assert match, 'Could not find the "1B" prompt array in canon-journey.js.'

    body = match.group("body")
    strings = list(re.finditer(r'"(?:\\.|[^"\\])*"', body))
    assert len(strings) == 4, f'Expected exactly four strings in "1B", found {len(strings)}.'
    remainder = re.sub(r'"(?:\\.|[^"\\])*"', "", body)
    assert not remainder.strip(" \t\r\n,"), 'The "1B" array contains non-string content.'
    return [json.loads(string.group(0)) for string in strings]


def _knowledge() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


def _matches(knowledge: dict[str, dict], command: str) -> set[str]:
    return {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith("k_sl_1b")
        and item.get("action_evidence")
        and _matches_all(tuple(tuple(group) for group in item["action_evidence"]), command)
    }


def test_1b_spine_prompts_match_their_authored_reveals_in_order() -> None:
    prompts = _scene_prompts()
    expected = [
        {"k_sl_1b_a_r2"},
        {"k_sl_1b_b_r1"},
        {"k_sl_1b_a_r1"},
        {"k_sl_1b_c_r1"},
    ]
    knowledge = _knowledge()

    matched = [_matches(knowledge, prompt) for prompt in prompts]
    assert matched == expected

    required = {requirement["fact_id"] for requirement in knowledge["k_sl_1b_c_r1"]["requires"]}
    established = {
        fact["fact_id"]
        for item_ids in matched[:3]
        for item_id in item_ids
        for fact in knowledge[item_id].get("establishes", [])
    }
    assert required <= established

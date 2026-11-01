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
    match = re.search(r'"2A"\s*:\s*\[(?P<body>.*?)\]', source, re.DOTALL)
    assert match, 'Could not find the "2A" prompt array in canon-journey.js.'

    body = match.group("body")
    strings = list(re.finditer(r'"(?:\\.|[^"\\])*"', body))
    assert len(strings) == 4, f'Expected exactly four strings in "2A", found {len(strings)}.'
    remainder = re.sub(r'"(?:\\.|[^"\\])*"', "", body)
    assert not remainder.strip(" \t\r\n,"), 'The "2A" array contains non-string content.'
    return [json.loads(string.group(0)) for string in strings]


def _knowledge() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


def _matches(knowledge: dict[str, dict], command: str) -> set[str]:
    return {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith("k_sl_2a")
        and item.get("action_evidence")
        and _matches_all(tuple(tuple(group) for group in item["action_evidence"]), command)
    }


def test_2a_spine_prompts_match_their_authored_reveals_in_order() -> None:
    prompts = [
        "Drive to the facility perimeter.",
        "Meet the shift supervisor at the facility gate.",
        "Inspect the cooling manifold and ventilation grille.",
        "Diagnose the real cooling-water pressure fault and ventilation problem to the supervisor.",
    ]
    expected = [
        set(),
        set(),
        set(),
        {"k_sl_2a_c_r5"},
    ]
    knowledge = _knowledge()

    matched = [_matches(knowledge, prompt) for prompt in prompts]
    assert matched == expected

    established = {"facility_infiltration_needed"}
    for prompt_number, item_ids in enumerate(matched, start=1):
        required = {
            requirement["fact_id"] for item_id in item_ids for requirement in knowledge[item_id].get("requires", [])
        }
        assert required <= established, (
            f"2A prompt {prompt_number} requires facts not established earlier: {sorted(required - established)}"
        )
        established |= {fact["fact_id"] for item_id in item_ids for fact in knowledge[item_id].get("establishes", [])}

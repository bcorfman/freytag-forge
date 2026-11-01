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
    match = re.search(r'"2B"\s*:\s*\[(?P<body>.*?)\]', source, re.DOTALL)
    assert match, 'Could not find the "2B" prompt array in canon-journey.js.'

    body = match.group("body")
    strings = list(re.finditer(r'"(?:\\.|[^"\\])*"', body))
    assert len(strings) == 4, f'Expected exactly four strings in "2B", found {len(strings)}.'
    remainder = re.sub(r'"(?:\\.|[^"\\])*"', "", body)
    assert not remainder.strip(" \t\r\n,"), 'The "2B" array contains non-string content.'
    return [json.loads(string.group(0)) for string in strings]


def _knowledge() -> dict[str, dict]:
    raw = yaml.safe_load((PACKAGE_ROOT / "knowledge.yaml").read_text())
    return {item["id"]: item for item in raw["knowledge"]}


def _matches(knowledge: dict[str, dict], command: str) -> set[str]:
    return {
        item_id
        for item_id, item in knowledge.items()
        if item_id.startswith("k_sl_2b")
        and item.get("action_evidence")
        and _matches_all(tuple(tuple(group) for group in item["action_evidence"]), command)
    }


def test_2b_spine_prompts_match_their_authored_reveals_in_order() -> None:
    prompts = [
        "Pull Kristin's own JANUS file first and keep Brandon's name in the build record.",
        "Pull Kristin's own JANUS file first and let Brandon erase his name from the build record.",
        "Type one reply to Michelle on the medical terminal.",
        "Read the archive situation and wait for Michelle's route.",
    ]
    expected = [
        {"k_sl_2b_b_r4"},
        {"k_sl_2b_b_r5"},
        {"k_sl_2b_c_r3"},
        set(),
    ]
    knowledge = _knowledge()

    matched = [_matches(knowledge, prompt) for prompt in prompts]
    assert matched == expected

    established: set[str] = set()
    for prompt_number, item_ids in enumerate(matched, start=1):
        required = {
            requirement["fact_id"] for item_id in item_ids for requirement in knowledge[item_id].get("requires", [])
        }
        assert required <= established, (
            f"2B prompt {prompt_number} requires facts not established earlier: {sorted(required - established)}"
        )
        established |= {fact["fact_id"] for item_id in item_ids for fact in knowledge[item_id].get("establishes", [])}

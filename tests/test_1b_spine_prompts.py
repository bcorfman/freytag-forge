from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from storygame.runtime.candidate_matcher import _matches_all
from storygame.runtime.facts import Fact
from tests.test_hidden_bench_discovery import _engine, _fresh_1b_state

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
        {"k_sl_1b_d_r1", "k_sl_1b_e_r1", "k_sl_1b_a_r2"},
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


@pytest.mark.parametrize(
    ("prompt", "expected_id", "recovered", "facts", "active_storylets"),
    (
        ("Examine the photograph beneath the bench.", "k_sl_1b_d_r1", False, (), ("SL-1B-D",)),
        (
            "Show Michelle's photograph to the man and ask who he is.",
            "k_sl_1b_b_r1",
            True,
            (),
            ("SL-1B-B",),
        ),
        (
            "Match the transit token to the handwritten number sequence.",
            "k_sl_1b_a_r1",
            True,
            (),
            ("SL-1B-A",),
        ),
        (
            "Get out through the storm drains and watch how he opens the secured gate.",
            "k_sl_1b_c_r1",
            True,
            ("brandon_identified", "missing_may_be_alive"),
            ("SL-1B-C",),
        ),
    ),
)
def test_1b_spine_prompts_earn_their_intended_runtime_reveals(
    monkeypatch: pytest.MonkeyPatch,
    prompt: str,
    expected_id: str,
    recovered: bool,
    facts: tuple[str, ...],
    active_storylets: tuple[str, ...],
) -> None:
    state = _fresh_1b_state(recovered=recovered)
    state.active_event_ids.update(active_storylets)
    for fact_id in facts:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))

    result = _engine(monkeypatch, state).turn(prompt)

    assert result.selected_knowledge_ids == (expected_id,)
    assert result.selected_knowledge_ids != ("k_sl_1b_e_r1",)

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.story_package.loader import load_story_package
from tests.scene_harness import authored_handoff, scene_engine

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CASES = json.loads(Path("tests/fixtures/scene_commands.json").read_text())


@pytest.mark.parametrize(
    "case",
    [pytest.param(case, id=f"{case['scene']}-{case['expected']}-{index}") for index, case in enumerate(CASES, 1)],
)
def test_scene_commands_reach_their_reveals(case):
    state, engine = scene_engine(
        PACKAGE,
        case["scene"],
        true_facts=tuple(case["true_facts"]),
        turn_index=case["turn_index"],
    )
    handoff = authored_handoff(engine, state, case["command"])
    assert handoff is not None and handoff.candidate.id == case["expected"], case["command"]

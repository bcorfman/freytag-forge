from copy import deepcopy
from pathlib import Path

from bench.judge_input import judge_turns
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_judge_turns_projects_authored_text_and_reveal_visibility() -> None:
    reveal = next(
        item
        for item in PACKAGE.knowledge.knowledge
        if item.delivery_text == "A memory card is taped beneath the KMS drawer. It is Michelle's card."
    )
    turns = [
        {
            "turn_number": 2,
            "scene_id": "1A",
            "authored_handoff_candidate_id": reveal.id,
            "narration": "Kristin searches beneath the drawer.",
            "item_facts_before": {"Michelle's memory card": {"place": "with Kristin"}, "phone": {}},
            "item_facts_after": {"Michelle's memory card": {"place": "with Kristin"}, "phone": {}},
        },
        {
            "turn_number": 3,
            "scene_id": "1A",
            "item_facts_before": {"Michelle's memory card": {"place": "with Kristin"}},
            "item_facts_after": {},
        },
    ]
    original = deepcopy(turns)

    judged = judge_turns(turns, [], PACKAGE)

    assert judged[0]["story_text"] == [reveal.delivery_text]
    assert "Michelle's memory card" not in judged[0]["item_facts_before"]
    assert "Michelle's memory card" in judged[0]["item_facts_after"]
    assert judged[1]["story_text"] == []
    assert judged[1]["item_facts_before"] == turns[1]["item_facts_before"]
    assert "Michelle's memory card" in judged[1]["item_facts_before"]
    assert turns == original


def test_judge_turns_projects_scene_bridge_after_turn() -> None:
    turn = {"turn_number": 13, "scene_id": "1A", "item_facts_before": {}}
    bridge = PACKAGE.scenes[0].metadata.bridge_text["t_1a_1b"]

    judged = judge_turns(
        [turn],
        [{"from_scene": "1A", "to_scene": "1B", "after_turn": 13, "advanced_offline": False}],
        PACKAGE,
    )

    assert judged[0]["story_text"] == [bridge]
    assert turn == {"turn_number": 13, "scene_id": "1A", "item_facts_before": {}}

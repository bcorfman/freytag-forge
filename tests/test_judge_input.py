from copy import deepcopy
from pathlib import Path

from bench.judge_input import judge_turns
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_judge_turns_projects_authored_text_and_reveal_visibility() -> None:
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]
    turns = [
        {
            "turn_number": 2,
            "scene_id": "1A",
            "authored_handoff_candidate_id": reveal.id,
            "narration": f"Kristin searches beneath the drawer. {reveal.delivery_text}",
            "item_facts_before": {"Michelle's memory card": {"place": "with Kristin"}, "phone": {}},
            "item_facts_after": {"Michelle's memory card": {"place": "with Kristin"}, "phone": {}},
        },
        {
            "turn_number": 3,
            "scene_id": "1A",
            "narration": "Kristin waits.",
            "item_facts_before": {"Michelle's memory card": {"place": "with Kristin"}},
            "item_facts_after": {},
        },
    ]
    original = deepcopy(turns)

    judged = judge_turns(turns, [], PACKAGE)

    assert judged[0]["story_text"] == [reveal.delivery_text]
    assert judged[0]["narrator_narration"] == "Kristin searches beneath the drawer."
    assert "Michelle's memory card" not in judged[0]["item_facts_before"]
    assert "Michelle's memory card" in judged[0]["item_facts_after"]
    assert judged[1]["story_text"] == []
    assert judged[1]["narrator_narration"] == "Kristin waits."
    assert judged[1]["item_facts_before"] == turns[1]["item_facts_before"]
    assert "Michelle's memory card" in judged[1]["item_facts_before"]
    assert turns == original


def test_judge_turns_projects_scene_bridge_after_turn() -> None:
    bridge = PACKAGE.scenes[0].metadata.bridge_text["t_1a_1b"]
    turn = {"turn_number": 13, "scene_id": "1A", "narration": bridge, "item_facts_before": {}}

    judged = judge_turns(
        [turn],
        [{"from_scene": "1A", "to_scene": "1B", "after_turn": 13, "advanced_offline": False}],
        PACKAGE,
    )

    assert judged[0]["story_text"] == [bridge]
    assert judged[0]["narrator_narration"] == ""
    assert turn == {"turn_number": 13, "scene_id": "1A", "narration": bridge, "item_facts_before": {}}


def test_judge_turns_strips_delivery_then_bridge_in_reverse_order() -> None:
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]
    bridge = PACKAGE.scenes[0].metadata.bridge_text["t_1a_1b"]
    turn = {
        "turn_number": 13,
        "scene_id": "1A",
        "authored_handoff_candidate_id": reveal.id,
        "narration": f"Kristin starts the truck. {reveal.delivery_text} {bridge}",
        "item_facts_before": {},
    }

    judged = judge_turns(
        [turn],
        [{"from_scene": "1A", "to_scene": "1B", "after_turn": 13, "advanced_offline": False}],
        PACKAGE,
    )

    assert judged[0]["story_text"] == [reveal.delivery_text, bridge]
    assert judged[0]["narrator_narration"] == "Kristin starts the truck."


def test_judge_turns_keeps_narration_when_authored_text_is_not_a_suffix() -> None:
    reveal = PACKAGE.knowledge_indexes.by_id["k_sl_1a_b_r0"]
    narration = f"{reveal.delivery_text} Kristin searches beneath the drawer."
    judged = judge_turns(
        [{"authored_handoff_candidate_id": reveal.id, "narration": narration}],
        [],
        PACKAGE,
    )

    assert judged[0]["narrator_narration"] == narration

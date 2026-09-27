from copy import deepcopy
from pathlib import Path

from bench.item_facts import declared_axes_for_package
from bench.judge_input import judge_turns
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_declared_axes_records_carry_axes_and_old_records_fill_them() -> None:
    state_axes = {"Kristin's laptop": {"closed": ["shut"], "open": []}}
    axes = declared_axes_for_package(
        PACKAGE,
        ["drawer", "workstation chair", "Kristin's laptop", "Michelle's phone"],
        state_axes,
    )
    assert axes["drawer"] == [["open", "closed"]]
    assert axes["workstation chair"] == [["overturned", "upright"]]
    assert axes["Kristin's laptop"] == [["closed", "open"]]
    assert "Michelle's phone" not in axes

    turn = {
        "narration": "Kristin opens the drawer and checks the phone.",
        "item_facts_before": {
            "drawer": {"place": "kitchen", "condition": ["closed", "unlocked"]},
            "Michelle's phone": {"place": "table", "condition": ["undamaged"]},
        },
        "item_facts_after": {
            "drawer": {"place": "kitchen", "condition": ["open", "unlocked"]},
            "Michelle's phone": {"place": "table", "condition": ["undamaged"]},
        },
    }
    judged = judge_turns([turn], [], PACKAGE, state_axes=state_axes)[0]
    assert judged["item_facts_axes"] == {
        "drawer": [["open", "closed"]],
    }
    assert judged["item_facts_before"]["drawer"]["condition"] == ["closed"]
    assert judged["item_facts_after"]["drawer"]["condition"] == ["open"]
    assert judged["item_facts_before"]["Michelle's phone"]["condition"] == []
    assert turn["item_facts_before"]["drawer"]["condition"] == ["closed", "unlocked"]


def test_declared_axes_strip_undeclared_conditions_from_old_records() -> None:
    turn = {
        "narration": "Open the drawer.",
        "item_facts_before": {"drawer": {"place": "kitchen", "condition": ["closed", "unlocked"]}},
        "item_facts_after": {"drawer": {"place": "kitchen", "condition": ["open", "unlocked"]}},
    }

    judged = judge_turns([turn], [], PACKAGE)[0]

    assert judged["item_facts_axes"] == {"drawer": [["open", "closed"]]}
    assert judged["item_facts_before"]["drawer"]["condition"] == ["closed"]
    assert judged["item_facts_after"]["drawer"]["condition"] == ["open"]
    assert turn["item_facts_after"]["drawer"]["condition"] == ["open", "unlocked"]


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


def test_judge_turns_projects_typed_command_and_engine_prefix() -> None:
    turns = [
        {
            "player_input": "The engine walks to the kitchen. Search the workstation.",
            "typed_input": "Search the workstation.",
            "narration": "Kristin searches the workstation.",
        },
        {"player_input": "Search the workstation.", "narration": "Kristin searches it."},
    ]

    judged = judge_turns(turns, [], PACKAGE)

    assert judged[0]["command_typed"] == "Search the workstation."
    assert judged[0]["just_before"] == "The engine walks to the kitchen."
    assert judged[1]["command_typed"] == "Search the workstation."
    assert judged[1]["just_before"] == ""
    assert "command_typed" not in turns[0]


def test_judge_turns_projects_nested_place_contents_and_recorded_override() -> None:
    turn = {
        "scene_id": "1A",
        "narration": "Kristin records the workstation.",
        "item_facts_after": {"workstation": {"place": "outside the house"}},
    }

    contents = judge_turns([turn], [], PACKAGE)[0]["place_contents"]

    assert "workstation" not in contents["kitchen"]
    assert "back door" in contents["kitchen"]
    assert "drawer" not in contents["kitchen"]
    assert "workstation" in contents["outside the house"]
    assert "drawer" in contents["outside the house"]
    assert "Michelle's memory card" not in contents["kitchen"]
    assert turn["item_facts_after"]["workstation"]["place"] == "outside the house"


def test_place_contents_resolves_tracked_names_and_nested_recorded_places() -> None:
    turn = {
        "scene_id": "1A",
        "narration": "Kristin checks the phone and moves the truck.",
        "item_facts_names": {"Kristin": ["Kristin Schweitzer", "Kristin's pocket"]},
        "item_facts_after": {
            "Michelle's phone": {"place": "Kristin"},
            "Kristin": {"place": "kitchen"},
            "note": {"place": "drawer"},
            "Kristin's truck": {"place": "Los Angeles park"},
        },
    }

    contents = judge_turns([turn], [], PACKAGE)[0]["place_contents"]

    assert "Michelle's phone" in contents["Kristin"]
    assert "Michelle's phone" in contents["kitchen"]
    assert "Michelle's phone" in contents["Michelle's house"]
    assert "Kristin" in contents["kitchen"]
    assert "Kristin" in contents["Michelle's house"]
    assert "Kristin Schweitzer" not in contents["kitchen"]
    assert "note" in contents["kitchen"]
    assert "Kristin's laptop" in contents["Los Angeles park"]


def test_place_contents_tracked_character_place_overrides_authored_item_place() -> None:
    turn = {
        "scene_id": "1A",
        "narration": "Kristin checks Michelle's phone.",
        "item_facts_after": {
            "Kristin": {"place": "Kristin's truck"},
            "Michelle's phone": {"place": "Kristin"},
        },
    }

    contents = judge_turns([turn], [], PACKAGE)[0]["place_contents"]

    assert "Michelle's phone" in contents["Kristin's truck"]
    assert "Michelle's phone" not in contents["kitchen"]

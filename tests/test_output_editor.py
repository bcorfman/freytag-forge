from __future__ import annotations

from storygame.llm.output_editor import DeterministicOutputEditor


def test_deterministic_editor_trims_legacy_opening_lines():
    editor = DeterministicOutputEditor()
    opening = [
        "Where you are: Front Steps. A neutral mystery scene.",
        "Cast: Guide, Rival, Witness",
        "The air around the front steps bites with cold rain.",
        "You can see case file and field kit.",
        "Your immediate objective is clear: Find the first lead.",
        "The only exit is to the north.",
    ]

    reviewed = editor.review_opening(opening, "Find the first lead.")
    joined = "\n".join(reviewed).lower()
    assert "where you are:" not in joined
    assert "cast:" not in joined
    assert "neutral mystery scene" not in joined
    assert "the only exit is to" not in joined
    assert len(reviewed) <= 4


def test_deterministic_editor_reduces_goal_repetition_after_first_turn():
    editor = DeterministicOutputEditor()
    goal = "Find the hidden ledger."
    turn_lines = [
        "Archive Room\nDust and records line the shelves.\nYou can see ledger page.\nThe only exit is to the east.\nMina waits here.",
        "You remind yourself: Find the hidden ledger.",
        "A distant bell echoes through the hall.",
    ]

    reviewed = editor.review_turn(turn_lines, goal, turn_index=3, debug=False)
    assert len(reviewed) == 2
    assert all(goal.lower() not in line.lower() for line in reviewed[1:])

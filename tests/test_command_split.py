"""Command splitting contract coverage."""

from pathlib import Path

import pytest

from storygame.runtime.command_split import split_command
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


@pytest.mark.unit
@pytest.mark.parametrize(
    ("command", "expected"),
    [
        (
            "Go out to your truck and bring your laptop inside.",
            ["Go out to your truck.", "Bring your laptop inside."],
        ),
        (
            "Pick up Michelle's phone and put it in your pocket.",
            ["Pick up Michelle's phone.", "Put it in your pocket."],
        ),
        (
            "Put Michelle's phone in your pocket and walk out to the truck.",
            ["Put Michelle's phone in your pocket.", "Walk out to the truck."],
        ),
        (
            "Open Michelle's drawer and take the memory card.",
            ["Open Michelle's drawer.", "Take the memory card."],
        ),
        (
            "Hand Michelle's phone to the man and walk back to the bench.",
            ["Hand Michelle's phone to the man.", "Walk back to the bench."],
        ),
        (
            "Show Kristin's badge to the guard and open the gate.",
            ["Show Kristin's badge to the guard.", "Open the gate."],
        ),
        (
            "Put Michelle’s phone in your pocket and walk out to the truck.",
            ["Put Michelle’s phone in your pocket.", "Walk out to the truck."],
        ),
        (
            "Take Michelle's phone out and throw it hard against the kitchen wall.",
            ["Take Michelle's phone out.", "Throw it hard against the kitchen wall."],
        ),
        (
            "Leave the house and drive to the park with Michelle's phone.",
            ["Leave the house.", "Drive to the park with Michelle's phone."],
        ),
        (
            "Walk over to the man watching you and hand him Michelle's phone.",
            ["Walk over to the man watching you.", "Hand him Michelle's phone."],
        ),
        ("Unplug Michelle's phone and hold it.", ["Unplug Michelle's phone.", "Hold it."]),
        (
            "Open the drawer, take the card, then close the drawer.",
            ["Open the drawer.", "Take the card.", "Close the drawer."],
        ),
        (
            "Plug the memory card into your laptop and read the files.",
            ["Plug the memory card into your laptop.", "Read the files."],
        ),
        (
            "Conceal the memory card and pretend to know nothing.",
            ["Conceal the memory card.", "Pretend to know nothing."],
        ),
        ("Look at the phone and the laptop.", ["Look at the phone and the laptop."]),
        ("Search the kitchen and the living room.", ["Search the kitchen and the living room."]),
        ("Check who has Michelle's phone now.", ["Check who has Michelle's phone now."]),
        (
            "Look around the bench for anything Michelle left.",
            ["Look around the bench for anything Michelle left."],
        ),
        ("Ask Brandon where he and Michelle met.", ["Ask Brandon where he and Michelle met."]),
        ("Look at Kristin's laptop and Michelle's phone.", ["Look at Kristin's laptop and Michelle's phone."]),
        ("Watch Michelle's car drive away.", ["Watch Michelle's car drive away."]),
        ("Ask Michelle's neighbor where she went.", ["Ask Michelle's neighbor where she went."]),
        ("Tell Brandon to wait and watch the gate.", ["Tell Brandon to wait and watch the gate."]),
        ('Say "run and hide" to Brandon.', ['Say "run and hide" to Brandon.']),
        ("Look carefully at Michelle's phone.", ["Look carefully at Michelle's phone."]),
        (
            "Go out to your truck. Bring your laptop inside.",
            ["Go out to your truck. Bring your laptop inside."],
        ),
    ],
)
def test_split_command(command: str, expected: list[str]) -> None:
    assert split_command(command) == expected


@pytest.mark.unit
def test_try_command_accepts_either_parse() -> None:
    result = split_command("Try to open the back door and see if it is locked.")
    assert result in (
        ["Try to open the back door and see if it is locked."],
        ["Try to open the back door.", "See if it is locked."],
    )


def test_engine_provider_receives_split_command() -> None:
    received: list[str] = []

    def provider(command: str) -> dict[str, object]:
        received.append(command)
        return {"segments": [{"kind": "narration", "text": "The move is clear."}]}

    engine = RuntimeEngine(RuntimeState.bootstrap(PACKAGE), provider)
    engine.turn("Go out to your truck and bring your laptop inside.")

    assert received == ["Go out to your truck. Bring your laptop inside."]
    assert engine.last_player_command == received[0]

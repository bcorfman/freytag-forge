from __future__ import annotations

import json
from pathlib import Path

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.seating import board_vehicle
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


class _Response:
    def __init__(self, body: object) -> None:
        self.body = json.dumps(body).encode()

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


def _opening_state():
    state = RuntimeState.bootstrap(PACKAGE)
    return state, world_for(PACKAGE, state.facts)


def test_1a_bootstrap_places_kristin_in_the_kitchen_and_keeps_truck_cargo() -> None:
    _, world = _opening_state()

    assert world.parent("kristin") == "kitchen"
    assert world.parent("kristin_truck") == "outside_house"
    assert world.parent("kristin_laptop") == "truck_passenger_seat"


def test_1a_opening_and_turn_prompts_keep_kitchen_grounding_and_hide_card(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    def open_request(request, **_kwargs: object) -> _Response:
        captured.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"Fixture."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state, _ = _opening_state()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    provider.opening()
    provider("Search the kitchen for signs of a struggle.")

    assert len(captured) == 2
    required_sentences = (
        "Michelle's home is otherwise untouched, but the back door has been forced.",
        "The deadbolt is still thrown.",
        "Michelle is missing, and her tablet and work bag are gone.",
        "Kristin knows Michelle would not leave her kitchen like this.",
        "A drawer on Michelle's workstation has Kristin's initials, KMS, newly carved into it.",
        "Kristin did not carve them.",
    )
    for payload in captured:
        user_prompt = payload["user"]
        assert "workstation is across the kitchen from the back door" in user_prompt
        assert all(sentence in user_prompt for sentence in required_sentences)
        scene_prompt = user_prompt.split("SCENE:\n", 1)[1].split("\n\nCONSTRAINTS:", 1)[0]
        assert "phone" not in scene_prompt.casefold()
        phone_lines = {line.strip() for line in user_prompt.splitlines() if "phone" in line.casefold()}
        assert phone_lines <= {
            "- Say who owns a thing the first time you name it: Michelle's phone, Kristin's laptop.",
            "- Michelle's phone stores only Michelle's things. Kristin's laptop stores only Kristin's things.",
            "- Michelle's phone is on the kitchen floor.",
        }
        assert "- Michelle's phone is on the kitchen floor." in phone_lines
        assert "memory card" not in user_prompt.casefold()
        assert "taped" not in user_prompt.casefold()


def test_1a_entry_text_ends_with_kitchen_entry() -> None:
    assert PACKAGE.scenes[0].metadata.entry_text.rstrip().endswith("let herself into the kitchen.")


def test_1a_boarding_from_the_kitchen_seats_kristin_and_leaves_truck_outside() -> None:
    _, world = _opening_state()

    result = board_vehicle(world, PACKAGE, "Get in Kristin's truck.", lambda *_args: True)

    assert result.steps[0] == "Kristin sat down in the driver's seat."
    assert world.parent("kristin") == "truck_driver_seat"
    assert world.parent("kristin_truck") == "outside_house"


def test_1a_prompts_do_not_expose_the_hidden_card_placement(monkeypatch) -> None:
    captured: list[dict[str, object]] = []

    def open_request(request, **_kwargs: object) -> _Response:
        captured.append(json.loads(request.data))
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"Fixture."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state, _ = _opening_state()
    provider = CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state)

    provider.opening()
    provider("Search the kitchen for signs of a struggle.")

    for payload in captured:
        prompt = payload["user"].casefold()
        assert "memory card" not in prompt
        assert "taped" not in prompt

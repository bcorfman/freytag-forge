from __future__ import annotations

import json
from pathlib import Path

import yaml

from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

OLD_OPENING = (
    "Michelle's text came in a little after 4:00am, lost among the emergency alerts while Kristin finished a late-night shift. "  # noqa: E501
    "She missed it by minutes. When she read it, her stomach dropped. Every call back failed. Kristin ran for her truck "  # noqa: E501
    "and drove as hard as the streets allowed, past sirens, ambulances, police cars, and intersections blocked for no reason "  # noqa: E501
    "anyone would explain. Was she hurt? Taken? Gone? Not knowing was the worst of it. She found the back door forced and "  # noqa: E501
    "let herself into the kitchen."
)
GLANCE = (
    "The kitchen was wrong at a glance. Michelle's chair lay tipped over at her workstation across the room, and her tablet "  # noqa: E501
    "and work bag were nowhere in sight. A mug sat on the workstation beside a stack of manuscript pages. The calendar and "  # noqa: E501
    "the lake photograph hung by the refrigerator, where they always had. Kristin was too frantic to read any of it yet. "  # noqa: E501
    "She called Michelle's name."
)
STEADY = (
    "Kristin makes herself stop and look properly. Michelle's phone is still here - damaged a bit but still working. Then she sees the back door. "  # noqa: E501
    "The splinters around the frame point outward, away from the house. A door forced from outside would splinter inward. "  # noqa: E501
    "Someone broke this one from inside to make it look like a break-in. It looks staged."
)
WITHHELD = [
    "splinter",
    "outward",
    "lukewarm",
    "warm",
    "glasses",
    "Saturday",
    "birthday",
    "KMS",
    "initials",
    "carved",
    "gap",
    "drawer",
    "phone",
    "card",
    "deadbolt",
]


class _Response:
    def __init__(self, payload: object) -> None:
        self.payload = payload

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode()


def _neutral_provider(_command: str) -> dict[str, object]:
    return {"segments": [{"kind": "narration", "text": "The house remains quiet."}]}


def _texts(proposal: object) -> tuple[str, ...]:
    return tuple(segment.text for segment in proposal.segments)


def _has_fact(state: RuntimeState, fact_id: str, value: bool) -> bool:
    expected = str(value).lower()
    return Fact(predicate=fact_id, subject="story", value=expected) in state.facts.asserted


def _engine(monkeypatch) -> tuple[RuntimeState, RuntimeEngine]:
    captured: list[str] = []
    engine = _cloudflare_engine(monkeypatch, captured)
    engine.opening()
    return engine.state, engine


def _cloudflare_engine(monkeypatch, captured: list[str]) -> RuntimeEngine:
    def open_request(request, **_kwargs: object) -> _Response:
        captured.append(request.data.decode())
        return _Response({"narration": '{"segments":[{"kind":"narration","text":"The house remains quiet."}]}'})

    monkeypatch.setattr("storygame.runtime.cloudflare.urlopen", open_request)
    state = RuntimeState.bootstrap(PACKAGE)
    return RuntimeEngine(
        state,
        CloudflareTurnProvider(worker_url="https://worker.example/turn", token="", state=state),
    )


def test_entry_text_keeps_the_old_opening_and_adds_the_glance() -> None:
    entry = PACKAGE.scenes[0].metadata.entry_text
    assert entry.startswith(OLD_OPENING)
    assert GLANCE in entry
    assert entry.endswith("\n\n")


def test_the_glance_names_the_room_and_withholds_every_meaning() -> None:
    entry = PACKAGE.scenes[0].metadata.entry_text
    glance = entry.split(OLD_OPENING, 1)[1].strip()
    assert all(word in glance for word in ("workstation", "chair", "tablet", "calendar"))
    assert not any(word in glance.casefold() for word in WITHHELD)
    lowered = entry.casefold()
    assert all(word not in lowered for word in ("phone", "drawer", "kms"))


def test_kristin_steadies_event_is_declared() -> None:
    event = next(event for event in PACKAGE.pacing.events if event.id == "kristin_steadies_1a")
    assert event.scene_id == "1A"
    assert event.trailing is True
    assert event.at_turn == 3
    assert [(condition.fact_id, condition.equals) for condition in event.when] == [
        ("michelle_abduction_suspicion", False)
    ]
    assert [(effect.fact_id, effect.equals) for effect in event.effects] == [("michelle_abduction_suspicion", True)]
    assert len(event.realizations) == 1
    assert event.realizations[0].verbatim is True
    assert event.realizations[0].text == STEADY
    routes = yaml.safe_load(Path("data/stories/continuity-initiative/storylet-routes.yaml").read_text(encoding="utf-8"))
    review = next(item for item in routes["pacing_event_review"] if item["event_id"] == event.id)
    assert review["scene_id"] == "1A"
    assert review["at_turn"] == 3
    assert review["effect"] == {"op": "assert", "fact_id": "michelle_abduction_suspicion", "value": True}
    assert review["status"] == "approved"


def test_kristin_steadies_at_turn_three_when_nothing_earned_it(monkeypatch) -> None:
    state, engine = _engine(monkeypatch)
    turns = [engine.turn("Wait and observe.") for _ in range(3)]
    assert STEADY not in _texts(turns[0])
    assert STEADY not in _texts(turns[1])
    assert _texts(turns[2])[-1] == STEADY
    assert sum(text == STEADY for turn in turns for text in _texts(turn)) == 1
    assert _has_fact(state, "michelle_abduction_suspicion", True)


def test_examining_the_door_early_earns_the_deduction_and_the_beat_stays_silent_control(monkeypatch) -> None:
    state, engine = _engine(monkeypatch)
    turns = [engine.turn(command) for command in ("Inspect the back door.", "Wait and observe.", "Wait and observe.")]
    all_text = " ".join(text for turn in turns for text in _texts(turn))
    assert all_text.count("The splinters around the frame point outward") == 1
    assert STEADY not in all_text
    assert _has_fact(state, "michelle_abduction_suspicion", True)


def test_orienting_commands_do_not_earn_the_deduction_on_turn_one_control(monkeypatch) -> None:
    for command in ("Look around.", "Examine the room.", "Search the house for Michelle.", "Call out for Michelle."):
        _, engine = _engine(monkeypatch)
        assert not any("splinters" in text.casefold() for text in _texts(engine.turn(command)))


def test_the_drawer_hint_names_only_the_carving(monkeypatch) -> None:
    delivery = next(
        item for item in PACKAGE.deliveries if item.scene_id == "1A" and item.fact_id == "continuity_initiative_known"
    )
    assert delivery.cue_text == "Kristin's initials, KMS, are carved into a drawer of Michelle's workstation."
    assert "gap" not in delivery.cue_text
    assert "lower edge" not in delivery.cue_text
    _, engine = _engine(monkeypatch)
    texts = _texts(engine.turn("Look around."))
    assert delivery.cue_text in texts
    assert "gap" not in " ".join(texts).casefold()


def test_the_workstation_is_named_in_the_opening_before_the_hint(monkeypatch) -> None:
    entry = PACKAGE.scenes[0].metadata.entry_text
    assert "workstation" in entry
    delivery = next(
        item for item in PACKAGE.deliveries if item.scene_id == "1A" and item.fact_id == "continuity_initiative_known"
    )
    _, engine = _engine(monkeypatch)
    assert _texts(engine.turn("Look around."))[-1] == delivery.cue_text


def test_setting_facts_gain_the_house_line() -> None:
    assert PACKAGE.scenes[0].metadata.setting_facts == (
        "Sirens carry from the next street.",
        "A dog barks behind the empty house next door.",
        "The rest of the house is quiet. Michelle is not in it.",
    )


def test_the_house_line_reaches_the_narrator_on_a_house_search(monkeypatch) -> None:
    captured: list[str] = []
    engine = _cloudflare_engine(monkeypatch, captured)
    engine.turn("Search the house for Michelle.")
    assert captured
    assert "The rest of the house is quiet. Michelle is not in it." in captured[-1]


def test_scene_1a_budget_pins_are_untouched_control() -> None:
    budget = json.loads(Path("tests/fixtures/deep_turn_budget.json").read_text())
    assert budget["scenes"]["1A"] == {
        "narration_chars": 5485,
        "narration_chars_all_alternates": 5597,
    }

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from storygame.runtime.capture import WorldCapture, build_capture_provider
from storygame.runtime.cloudflare import CloudflareTurnProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.fixed_refusal import _fixed_article_name, refuse_fixed_move
from storygame.runtime.item_facts import ItemFactsProvider
from storygame.runtime.jev_questions import names_other_action, relocates_thing
from storygame.runtime.persistence import RuntimeStateSqliteStore
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, world_for
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _state_and_world():
    state = RuntimeState.bootstrap(PACKAGE)
    world = world_for(PACKAGE, state.facts)
    assert world.move("kristin", "kitchen").ok
    return state, world


def _refusal(answer):
    state, world = _state_and_world()
    return (
        state,
        world,
        refuse_fixed_move(world, state.package, "Carry the workstation to the truck.", lambda *_: answer),
    )


def _provider(state):
    return ItemFactsProvider(
        worker_url="",
        token="",
        state=state,
        item_facts={},
        mode="single_call",
        seed_from_package=True,
        held_by=True,
    )


def _real_scene_1a(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("CLOUDFLARE_WORKER_URL", "https://w.example/t")
    monkeypatch.setenv("CLOUDFLARE_WORKER_TOKEN", "x")
    state = RuntimeState.bootstrap(PACKAGE)
    state.current_scene_id = "1A"
    apply_scene_placements(PACKAGE, state.facts, "1A")
    provider = build_capture_provider(state)
    provider._ensure_scene_seeded()
    return provider, provider._world()


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        ("driver's seat", "the driver's seat"),
        ("workstation", "the workstation"),
        ("back door", "the back door"),
        ("Michelle's phone", "Michelle's phone"),
        ("Kristin's truck", "Kristin's truck"),
    ],
)
def test_fixed_article_name(name, expected):
    assert _fixed_article_name(name) == expected


def test_fixed_move_is_refused_without_changing_world():
    state, world, result = _refusal(True)
    assert result.steps == ("Kristin tried to move the workstation. It is fixed in place and did not move.",)
    assert result.refused == ("workstation",)
    assert world.parent("michelle_workstation") == "kitchen"


def test_fixed_move_false_and_unanswered_do_not_add_steps():
    _, _, false_result = _refusal(False)
    assert false_result.steps == ()
    assert false_result.refused == ()
    _, _, unanswered = _refusal(None)
    assert unanswered.steps == ()
    assert unanswered.issues == ("fixed move question unanswered for 'workstation'",)


def test_only_named_fixed_things_are_asked():
    state, world = _state_and_world()
    asked: list[str] = []

    def answer(_command, name):
        asked.append(name)
        return True

    result = refuse_fixed_move(world, state.package, "Carry my laptop.", answer)
    assert result.steps == ()
    assert asked == []

    result = refuse_fixed_move(world, state.package, "Carry the workstation and back door.", answer)
    assert len(result.steps) == 2
    assert asked == ["back door", "workstation"]


def test_relocates_thing_reads_noul_answer():
    def ask(_state, questions):
        key = next(iter(questions))
        return {key: {"noul": 0.8}}

    assert relocates_thing(ask, "Carry the workstation.", "workstation") is True
    assert (
        relocates_thing(lambda *_: {"relocates_thing": {"noul": 0.2}}, "Read the workstation.", "workstation") is False
    )
    assert relocates_thing(lambda *_: {}, "Read the workstation.", "workstation") is None


def test_capture_fixed_refusal_skips_other_prerequisites():
    state, world = _state_and_world()
    provider = _provider(state)
    requested: list[str] = []

    def ask(_state, questions):
        key = next(iter(questions))
        requested.append(key)
        return {key: {"noul": 0.8}}

    record = WorldCapture(provider, ask, fixed_refusal=True).before_turn("Carry the workstation to the truck.")
    step = "Kristin tried to move the workstation. It is fixed in place and did not move."
    assert record["steps"][0] == step
    assert provider.prior_steps[0] == step
    assert requested == ["relocates_thing"]
    assert world.parent("michelle_workstation") == "kitchen"


def test_capture_default_does_not_ask_relocation():
    state, _ = _state_and_world()
    provider = _provider(state)
    requested: list[str] = []

    def ask(_state, questions):
        key = next(iter(questions))
        requested.append(key)
        return {key: {"noul": 0.8}}

    WorldCapture(provider, ask).before_turn("Carry the workstation to the truck.")
    assert "relocates_thing" not in requested


def test_real_scene_1a_same_area_is_the_legacy_fixed_scope(monkeypatch: pytest.MonkeyPatch):
    provider, world = _real_scene_1a(monkeypatch)

    assert world.area(provider.state.package.protagonist_id) != world.area(world.resolve("workstation"))
    result = refuse_fixed_move(world, provider.state.package, "Carry the workstation to the truck.", lambda *_: True)
    assert result.asked is False


@pytest.mark.parametrize(
    ("command", "name", "expected_steps"),
    [
        (
            "Carry the workstation to the truck.",
            "workstation",
            ("Kristin tried to move the workstation. It is fixed in place and did not move.",),
        ),
        (
            "Detach the driver's seat from the truck.",
            "driver's seat",
            ("Kristin tried to move the driver's seat. It is fixed in place and did not move.",),
        ),
        (
            "Extract the drawer from the workstation.",
            "drawer",
            (
                "Kristin tried to move the drawer. It is fixed in place and did not move.",
                "Kristin tried to move the workstation. It is fixed in place and did not move.",
            ),
        ),
    ],
)
def test_real_scene_1a_in_scope_refuses_fixed_moves(monkeypatch: pytest.MonkeyPatch, command, name, expected_steps):
    provider, world = _real_scene_1a(monkeypatch)
    result = refuse_fixed_move(
        world,
        provider.state.package,
        command,
        lambda *_: True,
        in_scope=lambda item_id: provider._name_in_scene_scope(world, world.name(item_id)),
    )

    assert result.steps == expected_steps
    assert any(name in step for step in result.steps)


def test_capture_real_scene_1a_fixed_refusal_precedes_other_questions(monkeypatch: pytest.MonkeyPatch):
    provider, world = _real_scene_1a(monkeypatch)
    requested: list[str] = []

    def ask(_state, questions):
        requested.extend(questions)
        return {key: {"noul": 1.0} for key in questions}

    with patch.object(CloudflareTurnProvider, "_request", return_value={"refers": ["workstation"], "same_as": {}}):
        capture = WorldCapture(provider, ask, fixed_refusal=True)
        record = capture.before_turn("Carry the workstation to the truck.")

    step = "Kristin tried to move the workstation. It is fixed in place and did not move."
    assert record["steps"][0] == step
    assert provider.prior_steps[:1] == (step,)
    assert provider.observation_request is None
    prompt = provider.assemble_turn_prompt("Carry the workstation to the truck.")
    rendered = prompt.get("user") or provider._section_user_prompt(prompt["context"])
    assert "Just before this: Kristin tried to move the workstation." in rendered
    assert any(key.split(":", 1)[0] == "relocates_thing" for key in requested)
    assert record["fixed_refusal_steps"] == [step]
    assert record["taking_steps"] == []
    assert record["boarding_steps"] == []
    assert record["seating_steps"] == []
    assert world.parent("michelle_workstation") == "kitchen"


def test_real_scene_1a_false_fixed_refusal_does_not_prepend_prompt(monkeypatch: pytest.MonkeyPatch):
    provider, _ = _real_scene_1a(monkeypatch)

    def ask(_state, questions):
        key = next(iter(questions))
        return {key: {"noul": 0.0}}

    with patch.object(CloudflareTurnProvider, "_request", return_value={"refers": ["workstation"], "same_as": {}}):
        capture = WorldCapture(provider, ask, fixed_refusal=True)
        capture.before_turn("Examine the workstation.")

    prompt = provider.assemble_turn_prompt("Examine the workstation.")
    rendered = prompt.get("user") or provider._section_user_prompt(prompt["context"])
    assert "Just before this:" not in rendered


def _engine_1a(monkeypatch: pytest.MonkeyPatch, classifier, *, engine_refusal: bool):
    provider, _ = _real_scene_1a(monkeypatch)
    assert provider._world().move("kristin", "kitchen").ok
    monkeypatch.setattr(CloudflareTurnProvider, "_request", lambda *_args: {"refers": [], "same_as": {}})
    capture = WorldCapture(provider, classifier, fixed_refusal=True, engine_refusal=engine_refusal)
    calls: list[str] = []

    def narrator(command: str) -> dict[str, object]:
        calls.append(command)
        return {"segments": [{"kind": "narration", "text": "The search continues."}]}

    return RuntimeEngine(provider.state, narrator, capture=capture), calls, provider


def test_engine_refusal_makes_no_provider_call(monkeypatch: pytest.MonkeyPatch):
    engine, calls, _ = _engine_1a(
        monkeypatch,
        lambda _state, questions: {next(iter(questions)): {"noul": 0.0 if "names_other_action" in questions else 1.0}},
        engine_refusal=True,
    )

    result = engine.turn("Carry the workstation to the truck.")

    assert calls == []
    assert result.narration == "Kristin tries to move the workstation, but it is fixed in place and does not budge."
    assert result.game_break is None
    assert result.story_complete is False


def test_engine_refusal_consumes_no_turn(monkeypatch: pytest.MonkeyPatch):
    engine, calls, _ = _engine_1a(
        monkeypatch,
        lambda _state, questions: {next(iter(questions)): {"noul": 0.0 if "names_other_action" in questions else 1.0}},
        engine_refusal=True,
    )
    engine.state.staged_cue_fact_id = "continuity_initiative_known"
    before = engine.state.snapshot()

    engine.turn("Carry the workstation to the truck.")

    assert engine.state.turn_index == before.turn_index
    assert engine.state.facts == before.facts
    engine.turn("Search the kitchen.")
    assert calls == ["Search the kitchen."]
    assert engine.state.last_turn_delivery.cue_fact_id == "continuity_initiative_known"
    assert engine.state.delivered_cue_ids.count("continuity_initiative_known") == 1


def test_engine_refusal_unanswered_classifier_narrates_normally(monkeypatch: pytest.MonkeyPatch):
    engine, calls, _ = _engine_1a(
        monkeypatch,
        lambda _state, questions: {},
        engine_refusal=True,
    )

    result = engine.turn("Carry the workstation to the truck.")

    assert calls == ["Carry the workstation to the truck."]
    assert result.narration == "The search continues."
    assert "fixed move question unanswered" in engine.capture.last_before["fixed_refusal_issues"][0]


def test_engine_refusal_off_by_default(monkeypatch: pytest.MonkeyPatch):
    engine, calls, _ = _engine_1a(
        monkeypatch,
        lambda _state, questions: {next(iter(questions)): {"noul": 1.0}},
        engine_refusal=False,
    )

    engine.turn("Carry the workstation to the truck.")

    assert calls == ["Carry the workstation to the truck."]
    assert engine.capture.last_before["steps"][0].startswith("Kristin tried to move the workstation.")


def test_mixed_refusal_appends_clarification(monkeypatch: pytest.MonkeyPatch):
    engine, calls, _ = _engine_1a(
        monkeypatch,
        lambda _state, questions: {next(iter(questions)): {"noul": 1.0}},
        engine_refusal=True,
    )

    result = engine.turn("Hoist the workstation, then open my laptop.")

    assert calls == []
    assert result.narration.endswith("Nothing else in that command was done. Say what you want to do next.")


def test_simple_refusal_has_no_clarification(monkeypatch: pytest.MonkeyPatch):
    engine, calls, _ = _engine_1a(
        monkeypatch,
        lambda _state, questions: {next(iter(questions)): {"noul": 0.0 if "names_other_action" in questions else 1.0}},
        engine_refusal=True,
    )

    result = engine.turn("Carry the workstation to the truck.")

    assert calls == []
    assert result.narration == "Kristin tries to move the workstation, but it is fixed in place and does not budge."


def test_unanswered_other_action_appends_clarification(monkeypatch: pytest.MonkeyPatch):
    engine, calls, _ = _engine_1a(
        monkeypatch,
        lambda _state, questions: {"relocates_thing": {"noul": 1.0}} if "relocates_thing" in questions else {},
        engine_refusal=True,
    )

    result = engine.turn("Hoist the workstation, then open my laptop.")

    assert calls == []
    assert result.narration.endswith("Nothing else in that command was done. Say what you want to do next.")
    assert "other-action question unanswered" in engine.capture.last_before["fixed_refusal_issues"]


def test_names_other_action_question_joins_refused_names(monkeypatch: pytest.MonkeyPatch):
    provider, _ = _real_scene_1a(monkeypatch)
    assert provider._world().move("kristin", "kitchen").ok
    requested: list[tuple[str, dict, dict]] = []

    def ask(state, questions):
        key = next(iter(questions))
        requested.append((key, questions, state))
        return {
            key: {"noul": 1.0 if key.split(":", 1)[0] == "relocates_thing" and "Extract" in state["command"] else 0.0}
            for key in questions
        }

    capture = WorldCapture(provider, ask, fixed_refusal=True, engine_refusal=True)
    capture.before_turn("Extract the drawer from the workstation.")
    assert [key for key, _, _ in requested].count("names_other_action") == 1
    key, payload, question_state = requested[-1]
    assert key == "names_other_action"
    assert payload[key]["type"] == "noul"
    assert question_state["thing"] == "drawer and workstation"

    requested.clear()
    capture.before_turn("Open the workstation.")
    assert "names_other_action" not in [key for key, _, _ in requested]


def test_refused_turn_survives_save_and_load(monkeypatch: pytest.MonkeyPatch, tmp_path):
    engine, calls, _provider = _engine_1a(
        monkeypatch,
        lambda _state, questions: {next(iter(questions)): {"noul": 0.0 if "names_other_action" in questions else 1.0}},
        engine_refusal=True,
    )
    before = engine.state.snapshot()
    engine.turn("Carry the workstation to the truck.")
    assert engine.state.snapshot() == before

    store = RuntimeStateSqliteStore(tmp_path / "runtime.sqlite")
    store.save("session", engine.state)
    restored = store.load("session", PACKAGE)
    assert restored.facts == before.facts
    assert restored.turn_index == before.turn_index

    next_provider = build_capture_provider(restored)
    next_capture = WorldCapture(
        next_provider,
        lambda _state, questions: {next(iter(questions)): {"noul": 0.0}},
        fixed_refusal=True,
        engine_refusal=True,
    )
    next_engine = RuntimeEngine(
        restored,
        lambda _command: {"segments": [{"kind": "narration", "text": "The search continues."}]},
        capture=next_capture,
    )
    next_engine.turn("Search the kitchen.")
    assert calls == []
    assert next_engine.state.turn_index == before.turn_index + 1


def test_relocates_thing_criteria_cover_lift_then_lower_and_source():
    captured: dict[str, object] = {}

    def ask(_state, questions):
        captured.update(questions)
        return {"relocates_thing": {"noul": 0.0}}

    relocates_thing(ask, "Lift the workstation, then lower it back into place.", "workstation")
    criteria = captured["relocates_thing"]["criteria"]
    assert "puts it back where it was" in criteria["true"]
    assert "taken from or put on" in criteria["false"]


def test_relocates_thing_wording_covers_repositioning_and_use():
    captured: dict[str, object] = {}

    def ask(_state, questions):
        captured.update(questions)
        return {"relocates_thing": {"noul": 0.0}}

    relocates_thing(ask, "Reposition the workstation.", "workstation")
    payload = captured["relocates_thing"]
    instructions = payload["instructions"]
    false_criterion = payload["criteria"]["false"]
    for word in ("tilts", "rotates", "rolls", "nudges", "repositions"):
        assert word in instructions
    assert "a door swung open or shut" in false_criterion
    assert "a drawer slid open or shut" in false_criterion


def test_names_other_action_wording_covers_shared_verb():
    captured: dict[str, object] = {}

    def ask(_state, questions):
        captured.update(questions)
        return {"names_other_action": {"noul": 1.0}}

    names_other_action(ask, "Carry the workstation and my bag outside.", "workstation")
    payload = captured["names_other_action"]
    assert "one verb" in payload["instructions"]

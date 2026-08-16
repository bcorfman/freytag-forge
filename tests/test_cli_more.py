from __future__ import annotations

import builtins
from pathlib import Path
from random import Random

import pytest

from storygame import cli as cli_module
from storygame.cli import (
    _action_from_proposal,
    _build_narrator,
    _context_goal_for_turn,
    _dialogue_contains_code_artifact,
    _dialogue_fact_conflict,
    _freeform_unavailable_lines,
    _joined_with_and,
    _opening_story_editor,
    _preview_state_delta,
    _proposal_mode_for_action,
    _public_event_message,
    _sanitize_narration_for_player,
    _semantic_actions_for_action,
    _setup_phase_lines,
    _structured_turn_proposal_for_action,
    _suppress_repeated_goal_copy,
    _targeted_conversation_requires_npc_reply,
    main,
    remember_opening_introductions,
    run_replay,
    run_turn,
)
from storygame.engine.parser import Action, ActionKind, parse_command
from storygame.engine.state import Event
from tests.fast_fixtures import make_cached_story_state as build_default_state
from tests.narrator_stubs import StubNarrator


class _PassThroughEditor:
    def review_opening(self, lines, active_goal):  # noqa: ANN001
        return lines

    def review_turn(self, lines, active_goal, turn_index, debug=False):  # noqa: ANN001
        return lines


def test_cli_policy_helpers_cover_narrative_turn_variants() -> None:
    assert _proposal_mode_for_action(parse_command("go to foyer")) == "physical"
    assert _proposal_mode_for_action(parse_command("north")) == "scene"
    assert _proposal_mode_for_action(parse_command("look")) == "investigation"
    assert _proposal_mode_for_action(parse_command("talk daria")) == "scene"

    assert _action_from_proposal("go", {"intent": "go", "targets": ["north"]}).kind.value == "move"
    assert _action_from_proposal("take", {"intent": "take", "targets": ["key"]}).kind.value == "take"
    assert (
        _action_from_proposal("use", {"intent": "use", "targets": ["key"], "arguments": {"target": "lock"}}).target
        == "key:lock"
    )
    assert _action_from_proposal("?", {"intent": "unknown"}).kind.value == "unknown"

    assert _context_goal_for_turn("look", "goal", 0) == "goal"
    assert _context_goal_for_turn("what is my objective?", "goal", 2) == "goal"
    assert _context_goal_for_turn("look", "goal", 2) == ""
    assert _suppress_repeated_goal_copy(["The immediate objective is clear.", "Keep moving."], "look", "goal") == [
        "Keep moving."
    ]


def test_cli_proposal_and_dialogue_guards_cover_bounded_effects() -> None:
    state = build_default_state(seed=602, genre="mystery")
    room_id = state.player.location
    item_id = state.world.rooms[room_id].item_ids[0]
    events = [
        Event(
            type="take",
            entities=(item_id,),
            delta_progress=0.1,
            delta_tension=0.2,
            metadata={
                "fact_ops": (
                    {"op": "assert", "fact": ("holding", "player", item_id)},
                    {"op": "retract", "fact": ("room_item", room_id, item_id)},
                )
            },
        )
    ]
    delta = _preview_state_delta(events)
    assert delta["assert"] and delta["retract"] and len(delta["numeric_delta"]) == 2
    assert _public_event_message("query") == ""
    assert _dialogue_contains_code_artifact({"text": "getStringExtra is unavailable."})
    assert not _dialogue_contains_code_artifact({"text": ""})
    assert _dialogue_fact_conflict(state, "daria_stone", "I wear a red coat.", "appearance")
    assert _targeted_conversation_requires_npc_reply(parse_command("talk daria"), {"targets": ["daria_stone"]})


def test_cli_control_plane_and_pending_confirmation_messages_are_covered() -> None:
    state = build_default_state(seed=603)
    rng = Random(603)
    _state, lines, *_ = run_turn(state, "/save", rng, StubNarrator())
    assert "Usage: save" in lines[0]
    _state, lines, *_ = run_turn(state, "/load", rng, StubNarrator())
    assert "Usage: load" in lines[0]
    pending = state.clone()
    pending.pending_high_impact_command = "break the seal"
    _state, lines, *_ = run_turn(pending, "maybe", rng, StubNarrator())
    assert "PROCEED" in lines[0]
    assert _freeform_unavailable_lines("backend offline")[0].endswith("backend offline")
    assert _action_from_proposal("help", {"intent": "help"}).kind.value == "help"
    assert _action_from_proposal("talk", {"intent": "talk", "targets": ["daria"]}).kind.value == "talk"


def test_cli_semantic_action_projection_covers_take_and_use() -> None:
    state = build_default_state(seed=604)
    room_id = state.player.location
    item_id = state.world.rooms[room_id].item_ids[0]
    take = Action(ActionKind.TAKE, target=item_id, raw=f"take {item_id}")
    take_event = Event(type="take", entities=(item_id,))
    assert _semantic_actions_for_action(state, take, [take_event])[0]["action_type"] == "take_item"
    assert _structured_turn_proposal_for_action(state, take, [take_event])["semantic_actions"]

    held_item = state.player.inventory[0]
    use = Action(ActionKind.USE, target=f"{held_item}:lock", raw="use item on lock")
    use_event = Event(type="use", entities=(held_item, "lock"))
    assert _semantic_actions_for_action(state, use, [use_event])[0]["action_type"] == "use_item"


def test_cli_opening_introduction_tracking_is_idempotent() -> None:
    state = build_default_state(seed=605)
    npc = next(iter(state.world.npcs.values()))
    paragraph = [f"{npc.name} waits nearby."]
    remember_opening_introductions(state, paragraph)
    remember_opening_introductions(state, paragraph)
    assert state.world_package["introduced_npcs"].count(npc.id) == 1


class _StubSetupDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001
        return lines


def test_ordinary_turn_returns_only_generated_narrative() -> None:
    state = build_default_state(seed=601)
    room = state.world.rooms[state.player.location]

    _next_state, lines, *_ = run_turn(
        state,
        "look",
        Random(601),
        StubNarrator("The dusk gathers around the choice before you."),
    )

    assert lines == ["You focus on the details and search for a usable clue."]
    assert room.name not in lines[0]
    assert room.description not in lines[0]


class _DropNarrationDirector:
    def compose_opening(self, state):  # noqa: ANN001
        return list(state.world_package.get("story_plan", {}).get("setup_paragraphs", ()))

    def review_turn(self, state, lines, events, debug=False):  # noqa: ANN001, ARG002
        return [line for line in lines if "llm narration" not in line.lower()]


class _RaisingSaveStore:
    def save_run(self, *args, **kwargs):  # noqa: ANN002, ANN003
        raise RuntimeError("boom-save")

    def load_run(self, slot: str):  # noqa: ARG002
        raise RuntimeError("boom-load")


def test_cli_helper_formatters_and_message_filters() -> None:
    edited = _opening_story_editor(
        [
            "Where you are: Front Steps, neutral mystery scene",
            "You were tasked with.",
            "Cast: x",
        ]
    )
    assert any("forced to take one final case" in line.lower() for line in edited)
    assert all("neutral mystery scene" not in line.lower() for line in edited)

    assert _joined_with_and([]) == ""
    assert _joined_with_and(["a"]) == "a"
    assert _joined_with_and(["a", "b"]) == "a and b"
    assert _joined_with_and(["a", "b", "c"]) == "a, b, and c"

    assert _public_event_message("") == ""
    assert _public_event_message("unknown_command").startswith("I didn't understand")
    assert _public_event_message("move_success") == ""
    assert _public_event_message("A human sentence.") == "A human sentence."

    assert _sanitize_narration_for_player("Hook beat at room.", debug=False) == ""
    assert _sanitize_narration_for_player("Hook beat at room.", debug=True) == "Hook beat at room."
    assert _sanitize_narration_for_player("review the case file", debug=False, raw_input="review the case file") == ""


def test_run_turn_uses_llm_proposal_for_semantic_inside_move() -> None:
    state = build_default_state(seed=4054, genre="mystery")

    class _NavigationPlanner:
        calls = 0

        def propose(self, state, raw_input):  # noqa: ANN001
            self.calls += 1
            return (
                {"speaker": "narrator", "text": "You head inside.", "tone": "in_world"},
                {
                    "intent": "move",
                    "targets": ["inside"],
                    "arguments": {},
                    "proposed_effects": ["move:inside"],
                },
            )

    planner = _NavigationPlanner()

    next_state, lines, _raw, _beat, continued = run_turn(
        state,
        "GO INSIDE",
        Random(4054),
        StubNarrator("You go inside through the mansion entrance and enter the foyer."),
        freeform_adapter=planner,
    )

    assert continued is True
    assert planner.calls == 1
    assert next_state.player.location == "foyer"
    assert lines == ["You head inside."]


def test_build_narrator_invalid_mode_raises() -> None:
    with pytest.raises(ValueError, match="Narrator mode"):
        _build_narrator("invalid")


def test_run_turn_save_and_load_generic_exception_paths() -> None:
    state = build_default_state(seed=701)
    save_store = _RaisingSaveStore()

    _next, lines, _raw, _beat, _continued = run_turn(
        state,
        "/save slot1",
        Random(701),
        StubNarrator(),
        save_store=save_store,
        output_editor=_PassThroughEditor(),
        story_director=_StubSetupDirector(),
    )
    assert any("Failed to save" in line for line in lines)

    _next, lines, _raw, _beat, _continued = run_turn(
        state,
        "/load slot1",
        Random(701),
        StubNarrator(),
        save_store=save_store,
        output_editor=_PassThroughEditor(),
        story_director=_StubSetupDirector(),
    )
    assert any("Failed to load" in line for line in lines)


def test_run_turn_preserves_llm_narration_when_director_drops_it() -> None:
    state = build_default_state(seed=704)
    _next, lines, _raw, _beat, _continued = run_turn(
        state,
        "look",
        Random(704),
        StubNarrator("LLM narration: you notice fresh boot prints by the archive door."),
        output_editor=_PassThroughEditor(),
        story_director=_DropNarrationDirector(),
    )
    assert lines == ["You focus on the details and search for a usable clue."]


def test_run_replay_breaks_on_quit_branch() -> None:
    end_state = run_replay(seed=702, commands=["/quit", "look"], narrator=StubNarrator())
    assert end_state.turn_index == 0


def test_setup_phase_lines_uses_default_director(monkeypatch) -> None:
    state = build_default_state(seed=703)
    monkeypatch.setattr(cli_module, "StoryDirector", lambda mode: _StubSetupDirector())  # noqa: ARG005
    lines = _setup_phase_lines(state)
    assert len(lines) >= 3


def test_main_covers_default_transcript_and_autosave_paths(tmp_path, monkeypatch) -> None:
    replay_path = tmp_path / "commands.txt"
    replay_path.write_text("look\n", encoding="utf-8")
    autosave_db = tmp_path / "autosave.sqlite"

    monkeypatch.setattr(cli_module, "_build_narrator", lambda mode: StubNarrator())  # noqa: ARG005
    monkeypatch.setattr(cli_module, "build_output_editor", lambda: _PassThroughEditor())
    monkeypatch.setattr(cli_module, "StoryDirector", lambda mode, editor: _StubSetupDirector())  # noqa: ARG005

    main(
        [
            "--seed",
            "7",
            "--replay",
            str(replay_path),
            "--autosave-slot",
            "auto",
            "--save-db",
            str(autosave_db),
        ]
    )
    default_transcript = Path("runs") / "replay_seed_7.txt"
    assert default_transcript.exists()
    default_transcript.unlink()

    inputs = iter(["look", "quit"])
    transcript = tmp_path / "live.txt"
    monkeypatch.setattr(builtins, "input", lambda _=None: next(inputs))
    main(
        [
            "--seed",
            "8",
            "--transcript",
            str(transcript),
            "--autosave-slot",
            "auto",
            "--save-db",
            str(autosave_db),
        ]
    )
    assert transcript.exists()

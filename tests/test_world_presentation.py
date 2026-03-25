from __future__ import annotations

from random import Random

from storygame.cli import _followed_npc_ids, _room_lines, _room_lines_with_followers, run_turn
from storygame.engine.facts import protagonist_profile
from storygame.engine.freeform import RuleBasedFreeformProposalAdapter
from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state
from storygame.llm.adapters import SilentNarrator
from storygame.llm.context import build_narration_context


def test_room_lines_include_room_identity_and_navigation():
    state = build_default_state(seed=31, genre="fantasy", tone="epic")
    lines = _room_lines(state)
    room = state.world.rooms[state.player.location]

    assert room.name in lines
    assert room.description in lines
    assert "exit" in lines.lower()


def test_starting_state_avoids_meta_room_text_and_starts_with_kit():
    state = build_default_state(seed=35, genre="mystery")
    room = state.world.rooms[state.player.location]

    assert "move the story toward resolution" not in room.description.lower()
    assert "neutral mystery scene" not in room.description.lower()
    assert "field_kit" in state.player.inventory
    assert "field_kit" not in room.item_ids


def test_mystery_starting_state_seeds_canonical_protagonist_name_fact():
    state = build_default_state(seed=351, genre="mystery")

    assert protagonist_profile(state)["name"] == "Detective Elias Wren"
    assert state.world_facts.holds("player_name", "Detective Elias Wren")


def test_context_filters_inventory_to_actionable_items():
    state = build_default_state(seed=32, genre="thriller")
    context = build_narration_context(state, parse_command("look"), "hook")
    payload = context.as_dict()

    assert "field_kit" in payload["inventory"]
    assert payload["npc_facts"]


def test_talk_sets_flag_for_present_npc_and_message_is_world_facing():
    state = build_default_state(seed=33, genre="adventure")
    room = state.world.rooms[state.player.location]
    npc_id = room.npc_ids[0]

    next_state, events = apply_action(state, parse_command(f"talk {npc_id}"), Random(33))
    talk_messages = [event.message_key for event in events if event.type == "talk"]

    assert talk_messages
    assert next_state.player.flags.get(f"talked_{npc_id}") is True
    assert isinstance(talk_messages[0], str)
    assert talk_messages[0].strip()


def test_unknown_non_command_routes_to_freeform_roleplay():
    state = build_default_state(seed=34, genre="suspense")
    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "ask about the latest clue",
        Random(34),
        SilentNarrator(),
        debug=False,
        freeform_adapter=RuleBasedFreeformProposalAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    assert next_state.turn_index == 1
    assert lines


def test_room_presentation_uses_short_on_move_and_long_on_look():
    state = build_default_state(seed=36, genre="mystery")
    direction = sorted(state.world.rooms[state.player.location].exits.keys())[0]
    destination = state.world.rooms[state.player.location].exits[direction]

    moved_state, move_lines, _action_raw, _beat_type, _continued = run_turn(
        state,
        direction,
        Random(36),
        SilentNarrator(),
        debug=False,
    )
    cache = moved_state.world_package["room_presentation_cache"][destination]
    assert cache["short"] in move_lines[0]
    assert cache["long"] not in move_lines[0]

    looked_state, look_lines, _action_raw, _beat_type, _continued = run_turn(
        moved_state,
        "look around",
        Random(37),
        SilentNarrator(),
        debug=False,
    )
    look_cache = looked_state.world_package["room_presentation_cache"][destination]
    assert look_cache["long"] in look_lines[0]


def test_room_presentation_short_description_uses_complete_clause_not_ellipsis_on_move():
    state = build_default_state(seed=361, genre="mystery")

    moved_state, move_lines, _action_raw, _beat_type, _continued = run_turn(
        state,
        "north",
        Random(361),
        SilentNarrator(),
        debug=False,
    )

    destination = moved_state.player.location
    cache = moved_state.world_package["room_presentation_cache"][destination]

    assert (
        cache["short"]
        == "The foyer opens beneath a dim chandelier, with wet tiles, shuttered portraits, and a long hall ahead."
    )
    assert "..." not in cache["short"]
    assert move_lines[0].startswith(
        "Mansion Foyer\nThe foyer opens beneath a dim chandelier, with wet tiles, shuttered portraits, and a long hall ahead."
    )


def test_move_room_block_announces_follower_before_npc_presence_line() -> None:
    state = build_default_state(seed=362, genre="mystery")

    moved_state, move_lines, _action_raw, _beat_type, _continued = run_turn(
        state,
        "north",
        Random(362),
        SilentNarrator(),
        debug=False,
    )

    text = move_lines[0]
    assert "Daria follows you." in text
    assert "Daria Stone" in text
    assert text.index("Daria follows you.") < text.index("Daria Stone")
    assert moved_state.player.location == "foyer"


def test_followed_npc_helpers_detect_assistant_transition() -> None:
    state = build_default_state(seed=363, genre="mystery")
    moved_state, _events = apply_action(state, parse_command("north"), Random(363))

    followed = _followed_npc_ids(state, moved_state)
    assert followed == ("daria_stone",)

    room_block = _room_lines_with_followers(moved_state, long_form=False, followed_npc_ids=followed)
    assert "Daria follows you." in room_block


def test_followed_npc_helpers_return_empty_without_room_change() -> None:
    state = build_default_state(seed=364, genre="mystery")

    followed = _followed_npc_ids(state, state)

    assert followed == ()
    room_block = _room_lines_with_followers(state, long_form=False, followed_npc_ids=followed)
    assert "follows you." not in room_block


def test_same_room_followup_turn_does_not_repeat_room_block():
    state = build_default_state(seed=37, genre="mystery")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "take the ledger page",
        Random(37),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert beat_type != "setup_scene"
    room = next_state.world.rooms[next_state.player.location]
    assert not any(line.startswith(room.name + "\n") for line in lines)
    assert not any(room.description in line for line in lines)
    assert any("clue noted:" in line.lower() for line in lines)


def test_mystery_room_block_mentions_arrival_car() -> None:
    state = build_default_state(seed=381, genre="mystery")

    room_block = _room_lines(state, long_form=True)

    assert "sedan" in room_block.lower()
    assert "left it" in room_block.lower()


def test_mystery_room_block_describes_player_owned_arrival_car_consistently() -> None:
    state = build_default_state(seed=382, genre="mystery")

    room_block = _room_lines(state, long_form=True)

    assert "you left it" in room_block.lower()
    assert "dropped you off" not in room_block.lower()


def test_mystery_room_block_falls_back_to_generic_car_line_without_player_arrival_facts() -> None:
    state = build_default_state(seed=383, genre="mystery")
    state.world_facts.retract_fact("item_owner", "arrival_sedan", "player")
    state.world_facts.retract_fact("item_driver", "arrival_sedan", "player")

    room_block = _room_lines(state, long_form=True)

    assert "a dark sedan waits nearby." in room_block.lower()
    assert "you left it" not in room_block.lower()
    assert "dropped you off" not in room_block.lower()


def test_vehicle_room_line_uses_fact_backed_phrasing_outside_start_room() -> None:
    state = build_default_state(seed=384, genre="mystery")
    side_room = state.world.rooms["foyer"]
    side_room.item_ids = tuple(dict.fromkeys((*side_room.item_ids, "arrival_sedan")))
    state.world_facts.assert_fact("room_item", "foyer", "arrival_sedan")
    state.player.location = "foyer"
    state.world_facts.retract_fact("at", "player", "front_steps")
    state.world_facts.assert_fact("at", "player", "foyer")

    room_block = _room_lines(state, long_form=True)

    assert "you left it" in room_block.lower()
    assert "dropped you off" not in room_block.lower()


def test_same_room_freeform_reply_does_not_repeat_room_block():
    class _AppearanceReplyAdapter:
        def propose(self, state, raw_input):  # noqa: ANN001
            return (
                {"speaker": "daria_stone", "text": "A crisp blouse and dark skirt. I dressed for business, not comfort.", "tone": "in_world"},
                {
                    "intent": "ask_about",
                    "targets": ["daria_stone"],
                    "arguments": {"topic": "appearance", "planner_source": "llm"},
                    "proposed_effects": [],
                },
            )

    state = build_default_state(seed=38, genre="mystery")

    next_state, lines, _action_raw, beat_type, continued = run_turn(
        state,
        "Daria, what are you wearing?",
        Random(38),
        SilentNarrator(),
        debug=False,
        freeform_adapter=_AppearanceReplyAdapter(),
    )

    assert continued is True
    assert beat_type == "freeform_roleplay"
    room = next_state.world.rooms[next_state.player.location]
    assert next_state.turn_index == 1
    assert not any(line.startswith(room.name + "\n") for line in lines)
    assert not any(room.description in line for line in lines)
    assert any(line.startswith('Daria Stone says: "') for line in lines)


def test_take_allows_unique_partial_item_reference_in_room():
    state = build_default_state(seed=39, genre="mystery")
    room = state.world.rooms[state.player.location]
    room.item_ids = ("route_key",)

    next_state, lines, _action_raw, _beat_type, continued = run_turn(
        state,
        "take key",
        Random(39),
        SilentNarrator(),
        debug=False,
    )

    assert continued is True
    assert "route_key" in next_state.player.inventory
    assert any("route key" in line.lower() for line in lines)

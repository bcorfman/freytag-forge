from __future__ import annotations

from random import Random

from storygame.cli import _room_lines, run_turn
from storygame.engine.parser import parse_command
from storygame.engine.rules import apply_action
from storygame.engine.world import build_default_state
import storygame.engine.mystery as mystery
from storygame.llm.adapters import SilentNarrator
from storygame.llm.context import build_narration_context


def test_room_lines_prioritize_clues_and_summarize_junk():
    state = build_default_state(seed=31)

    lines = _room_lines(state)

    assert "sea_map" in lines
    assert "old_coin" not in lines
    assert "Junk nearby:" in lines


def test_narration_context_filters_junk_inventory_items():
    state = build_default_state(seed=32)
    rng = Random(32)

    state = apply_action(state, parse_command("take old coin"), rng)[0]
    state = apply_action(state, parse_command("take sea map"), rng)[0]

    context = build_narration_context(state, parse_command("look"), "hook")
    payload = context.as_dict()

    assert "sea_map" in payload["inventory"]
    assert "old_coin" not in payload["inventory"]


def test_npc_knowledge_is_bounded_by_role_and_sources():
    state = build_default_state(seed=33)
    rng = Random(33)

    ferryman_state, ferryman_events = apply_action(state, parse_command("talk ferryman"), rng)
    assert ferryman_state.player.flags.get("talked_ferryman") is True
    ferryman_text = next(event.message_key for event in ferryman_events if event.type == "talk").lower()
    assert "rumor" in ferryman_text
    assert "conviction docket" not in ferryman_text

    state = apply_action(state, parse_command("north"), rng)[0]
    state = apply_action(state, parse_command("take bronze key"), rng)[0]
    state = apply_action(state, parse_command("east"), rng)[0]
    _, keeper_events = apply_action(state, parse_command("talk keeper"), rng)
    keeper_text = next(event.message_key for event in keeper_events if event.type == "talk").lower()
    assert "archive record" in keeper_text
    assert "harbor levy ledgers" in keeper_text


def test_first_turn_shows_caseboard_with_facts_questions_and_leads():
    state = build_default_state(seed=34)
    next_state, lines, _action, _beat, continued = run_turn(
        state,
        "look",
        Random(34),
        SilentNarrator(),
    )

    assert continued is True
    assert next_state.turn_index == 1
    text = "\n".join(lines)
    assert "Caseboard:" in text
    assert "Known facts:" in text
    assert "Open questions:" in text
    assert "Active leads:" in text


def test_mystery_helpers_partition_items_and_junk():
    state = build_default_state(seed=40)
    harbor = state.world.rooms["harbor"]

    actionable, junk_count = mystery.room_item_groups(state, harbor)
    assert "old_coin" not in actionable
    assert junk_count >= 1

    state.player.inventory = ("sea_map", "old_coin")
    assert "old_coin" not in mystery.filtered_inventory(state)
    assert "sea_map" in mystery.filtered_inventory(state)


def test_mystery_item_messages_reflect_item_role():
    state = build_default_state(seed=41)
    evidence = state.world.items["moonstone"]
    clue = state.world.items["sea_map"]
    tool = state.world.items["bell_pin"]
    junk = state.world.items["old_coin"]

    assert mystery.take_item_message(evidence).startswith("Evidence secured")
    assert mystery.take_item_message(clue).startswith("Clue noted")
    assert mystery.take_item_message(tool).startswith("Tool acquired")

    junk.kind = "junk"
    assert mystery.take_item_message(junk) == "take_success"


def test_npc_talks_change_with_player_progress():
    state = build_default_state(seed=42)
    state.player.inventory = tuple(
        item
        for item in ("bronze_key", "sea_map", "glass_lens", "moonstone")
        if item in state.world.items
    )
    state.player.flags["talked_keeper"] = True

    ferryman = state.world.npcs["ferryman"]
    oracle = state.world.npcs["oracle"]

    assert "loudest near" in mystery.npc_talk_message(state, ferryman, True).lower()
    assert "names without records are only rumors" not in mystery.npc_talk_message(state, oracle, True).lower()

    assert mystery.npc_talk_message(state, oracle, False).startswith(
        "Witness account: once the relay is exposed"
    )
    state.player.flags["transmitter_exposed"] = True
    assert "publish the codebook" in mystery.npc_talk_message(state, oracle, False).lower()


def test_caseboard_updates_with_flags_and_locations():
    state = build_default_state(seed=43)
    base = "\n".join(mystery.caseboard_lines(state))
    assert "Correlate ledger evidence" not in base
    assert "False emergency tones" in base

    state.player.inventory = ("bronze_key", "sea_map", "glass_lens", "moonstone")
    state.player.location = "archives"
    state.player.flags["transmitter_exposed"] = True
    state.player.flags["talked_keeper"] = True
    state.player.flags["frame_braced"] = True
    state.player.flags["relay_route_confirmed"] = True
    with_moonstone = "\n".join(mystery.caseboard_lines(state))
    assert "official chain" in with_moonstone.lower()
    assert "Use moonstone in the sanctuary to expose the relay." not in with_moonstone


def test_caseboard_shows_default_lead_when_everything_in_progressed():
    state = build_default_state(seed=44)
    state.player.location = "harbor"
    state.player.inventory = ("bronze_key", "sea_map", "glass_lens")
    state.player.flags["relay_route_confirmed"] = False

    lines = "\n".join(mystery.caseboard_lines(state))
    assert "Correlate ledger evidence with signal codebook and publish the chain." in lines


def test_item_message_handles_unknown_metadata_as_generic_take_success():
    state = build_default_state(seed=45)
    clue = state.world.items["sea_map"]
    clue.clue_text = ""
    clue.kind = "clue"
    assert mystery.take_item_message(clue) == "take_success"


def test_actionable_items_allow_quest_and_unknown_ids():
    state = build_default_state(seed=46)
    sea_map = state.world.items["sea_map"]
    sea_map.tags = ("quest",)
    state.player.inventory = ("missing_thing", "sea_map")
    assert mystery.is_actionable_item(sea_map) is True
    assert "sea_map" in mystery.filtered_inventory(state)
    assert mystery.filtered_inventory(state)[0] == "sea_map"

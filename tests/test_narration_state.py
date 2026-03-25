from __future__ import annotations

from storygame.llm.narration_state import (
    _actor_aliases,
    _item_aliases,
    _movement_fact_ops,
    _normalize_phrase,
    _normalized_appearance_phrase,
    _resolve_actor,
    _resolve_suffix_entity,
    _room_aliases,
    _sorted_aliases,
    _take_fact_ops,
    dialogue_fact_conflict,
    extract_dialogue_fact_ops,
    extract_narration_fact_ops,
)
from storygame.engine.state import Npc
from storygame.engine.world import build_default_state


def test_extract_narration_fact_ops_tracks_player_take_and_move() -> None:
    state = build_default_state(seed=501, genre="mystery")
    state.world.rooms[state.player.location].item_ids = state.world.rooms[state.player.location].item_ids + ("route_key",)

    ops = extract_narration_fact_ops(
        state,
        "You take the route key. You move to Mansion Foyer.",
    )

    assert {"op": "assert", "fact": ("holding", "player", "route_key")} in ops
    assert {"op": "assert", "fact": ("at", "player", "foyer")} in ops


def test_extract_narration_fact_ops_tracks_unique_first_name_alias_and_dedupes() -> None:
    state = build_default_state(seed=502, genre="mystery")
    state.world.rooms[state.player.location].item_ids = state.world.rooms[state.player.location].item_ids + ("route_key",)

    ops = extract_narration_fact_ops(
        state,
        "Daria takes the route key. Daria takes the route key.",
    )

    assert ops == [{"op": "assert", "fact": ("holding", "daria_stone", "route_key")}]


def test_extract_narration_fact_ops_requires_full_name_when_first_name_is_ambiguous() -> None:
    state = build_default_state(seed=503, genre="mystery")
    state.world.npcs["daria_quill"] = Npc(
        id="daria_quill",
        name="Daria Quill",
        description="Another investigator with a wary stare.",
        dialogue="Stay alert.",
    )

    ambiguous_ops = extract_narration_fact_ops(state, "Daria moves to Mansion Foyer.")
    full_name_ops = extract_narration_fact_ops(state, "Daria Stone moves to Mansion Foyer.")

    assert ambiguous_ops == []
    assert full_name_ops == [{"op": "assert", "fact": ("npc_at", "daria_stone", "foyer")}]


def test_extract_narration_fact_ops_ignores_unknown_actor_and_non_matching_clause() -> None:
    state = build_default_state(seed=504, genre="mystery")

    ops = extract_narration_fact_ops(
        state,
        "A shadow shifts near the wall. Someone whispers about the storm.",
    )

    assert ops == []


def test_narration_state_helper_alias_maps_cover_unique_and_ambiguous_names() -> None:
    state = build_default_state(seed=505, genre="mystery")
    state.world.npcs["daria_quill"] = Npc(
        id="daria_quill",
        name="Daria Quill",
        description="Another investigator with a wary stare.",
        dialogue="Stay alert.",
    )

    aliases = _actor_aliases(state)

    assert aliases["you"] == "player"
    assert aliases["daria stone"] == "daria_stone"
    assert "daria" not in aliases


def test_narration_state_helper_item_and_room_aliases_strip_articles_and_names() -> None:
    state = build_default_state(seed=506, genre="mystery")
    state.world.items["route_key"].name = "The Route Key"

    item_aliases = _item_aliases(state)
    room_aliases = _room_aliases(state)

    assert item_aliases["the route key"] == "route_key"
    assert item_aliases["route key"] == "route_key"
    assert room_aliases["outside the mansion"] == "front_steps"
    assert room_aliases["foyer"] == "foyer"


def test_narration_state_helper_resolvers_and_phrase_normalization() -> None:
    state = build_default_state(seed=507, genre="mystery")
    actor_aliases = _actor_aliases(state)
    item_aliases = _item_aliases(state)

    normalized = _normalize_phrase("Daria Stone! Takes: the route-key.")
    actor_id = _resolve_actor("daria stone moves to foyer", actor_aliases)
    item_id = _resolve_suffix_entity("you take the route key", item_aliases)

    assert normalized == "daria stone takes the route-key"
    assert actor_id == "daria_stone"
    assert item_id == "route_key"


def test_narration_state_helper_resolvers_return_empty_for_unknown_aliases() -> None:
    state = build_default_state(seed=509, genre="mystery")

    assert _resolve_actor("someone moves to foyer", _actor_aliases(state)) == ""
    assert _resolve_suffix_entity("you take the moon key", _item_aliases(state)) == ""


def test_extract_narration_fact_ops_tracks_npc_take_and_player_room_id_move() -> None:
    state = build_default_state(seed=510, genre="mystery")
    state.world.rooms[state.player.location].item_ids = state.world.rooms[state.player.location].item_ids + ("route_key",)

    ops = extract_narration_fact_ops(
        state,
        "Daria Stone takes the route key. You move to foyer.",
    )

    assert {"op": "assert", "fact": ("holding", "daria_stone", "route_key")} in ops
    assert {"op": "assert", "fact": ("at", "player", "foyer")} in ops


def test_narration_state_helper_sorted_aliases_prefers_longer_names_first() -> None:
    aliases = {"daria": "daria_stone", "daria stone": "daria_stone", "you": "player"}

    assert _sorted_aliases(aliases) == ("daria stone", "daria", "you")


def test_extract_narration_fact_ops_returns_empty_for_blank_input() -> None:
    state = build_default_state(seed=511, genre="mystery")

    assert extract_narration_fact_ops(state, "   ") == []


def test_narration_state_helper_room_aliases_include_room_ids() -> None:
    state = build_default_state(seed=512, genre="mystery")
    aliases = _room_aliases(state)

    assert aliases["front steps"] == "front_steps"
    assert aliases["outside the mansion"] == "front_steps"


def test_narration_state_helper_fact_op_builders_match_expected_shapes() -> None:
    assert _take_fact_ops("player", "route_key") == [{"op": "assert", "fact": ("holding", "player", "route_key")}]
    assert _movement_fact_ops("player", "foyer") == [{"op": "assert", "fact": ("at", "player", "foyer")}]
    assert _movement_fact_ops("daria_stone", "foyer") == [{"op": "assert", "fact": ("npc_at", "daria_stone", "foyer")}]


def test_narration_state_helper_aliases_include_a_and_an_article_variants() -> None:
    state = build_default_state(seed=508, genre="mystery")
    state.world.items["route_key"].name = "A Brass Key"
    state.world.items["ledger_page"].name = "An Old Note"

    item_aliases = _item_aliases(state)

    assert item_aliases["a brass key"] == "route_key"
    assert item_aliases["brass key"] == "route_key"
    assert item_aliases["an old note"] == "ledger_page"
    assert item_aliases["old note"] == "ledger_page"


def test_normalized_appearance_phrase_handles_articles_quotes_and_empty_matches() -> None:
    assert _normalized_appearance_phrase("I'm wearing the crisp white blouse.") == "a crisp white blouse"
    assert _normalized_appearance_phrase("I am wearing 'a dark coat'.") == "a dark coat"
    assert _normalized_appearance_phrase("I am wearing   ") == ""
    assert _normalized_appearance_phrase("The room feels colder now.") == ""


def test_extract_dialogue_fact_ops_tracks_new_npc_appearance_and_skips_duplicates() -> None:
    state = build_default_state(seed=513, genre="mystery")
    committed_appearance = state.world_facts.query("npc_appearance", "daria_stone", None)[0][2]

    new_ops = extract_dialogue_fact_ops(
        state,
        "daria_stone",
        "I'm wearing a dark wool coat.",
        "appearance",
    )
    duplicate_ops = extract_dialogue_fact_ops(
        state,
        "daria_stone",
        f"I'm wearing {committed_appearance}.",
        "clothing",
    )

    assert new_ops == [{"op": "assert", "fact": ("npc_appearance", "daria_stone", "a dark wool coat")}]
    assert duplicate_ops == []


def test_extract_dialogue_fact_ops_rejects_unknown_speaker_wrong_topic_and_missing_phrase() -> None:
    state = build_default_state(seed=514, genre="mystery")

    assert extract_dialogue_fact_ops(state, "", "I'm wearing a dark coat.", "appearance") == []
    assert extract_dialogue_fact_ops(state, "daria_stone", "I'm wearing a dark coat.", "ledger") == []
    assert extract_dialogue_fact_ops(state, "daria_stone", "The case is getting stranger.", "appearance") == []


def test_dialogue_fact_conflict_detects_real_mismatch_but_allows_match_subset_and_missing_fact() -> None:
    state = build_default_state(seed=515, genre="mystery")
    committed_appearance = state.world_facts.query("npc_appearance", "daria_stone", None)[0][2]

    assert dialogue_fact_conflict(state, "daria_stone", "I'm wearing a simple dark dress.", "appearance")
    assert not dialogue_fact_conflict(
        state,
        "daria_stone",
        f"I'm wearing {committed_appearance}.",
        "appearance",
    )
    assert not dialogue_fact_conflict(
        state,
        "daria_stone",
        f"I'm wearing the same outfit as before: {committed_appearance}.",
        "appearance",
    )
    assert not dialogue_fact_conflict(state, "unknown", "I'm wearing a dark coat.", "appearance")
    assert not dialogue_fact_conflict(state, "daria_stone", "I'm wearing a dark coat.", "ledger")

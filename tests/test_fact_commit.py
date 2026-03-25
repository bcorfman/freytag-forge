from __future__ import annotations

import pytest

from storygame.engine.fact_commit import InvariantValidator, ProjectionUpdater, ValidatedFactCommitter
from storygame.engine.facts import FactStore
from storygame.engine.state import GameState, Item, PlayerState, Room, WorldState
from storygame.engine.world import build_default_state


def _simple_state() -> GameState:
    rooms = {
        "foyer": Room(
            id="foyer",
            name="Foyer",
            description="A cold foyer.",
            exits={"north": "study"},
            locked_exits={"east": "brass_key"},
            item_ids=("case_file",),
            npc_ids=("daria_stone",),
        ),
        "study": Room(
            id="study",
            name="Study",
            description="A cluttered study.",
            exits={"south": "foyer"},
        ),
    }
    world = WorldState(
        rooms=rooms,
        items={"case_file": Item(id="case_file", name="Case File", description="A damp file.", kind="clue")},
        npcs={},
    )
    state = GameState(
        seed=1,
        player=PlayerState(location="foyer", inventory=(), flags={"story_replan_required": False}),
        world=world,
        world_facts=FactStore(
            {
                ("at", "player", "foyer"),
                ("path", "north", "foyer", "study"),
                ("path", "south", "study", "foyer"),
                ("locked", "east", "foyer", "brass_key"),
                ("room_item", "foyer", "case_file"),
                ("npc_at", "daria_stone", "foyer"),
                ("assistant_name", "Daria Stone"),
                ("player_name", "Detective Elias Wren"),
                ("player_background", "A methodical detective."),
                ("npc_role", "Daria Stone", "assistant"),
                ("active_goal", "Inspect the foyer."),
            }
        ),
        active_goal="Inspect the foyer.",
    )
    ProjectionUpdater().refresh_from_facts(state)
    return state


def test_commit_updates_unique_player_location_and_projection() -> None:
    state = build_default_state(seed=31, genre="mystery")
    destination = next(room_id for room_id in state.world.rooms if room_id != state.player.location)

    ValidatedFactCommitter().commit(
        state,
        [{"op": "assert", "fact": ("at", "player", destination)}],
        source="test",
    )

    assert state.world_facts.query("at", "player", None) == (("at", "player", destination),)
    assert state.player.location == destination


def test_commit_updates_unique_item_container_and_projection() -> None:
    state = build_default_state(seed=32, genre="mystery")
    room_id, item_id = next(
        (candidate_room_id, room.item_ids[0]) for candidate_room_id, room in state.world.rooms.items() if room.item_ids
    )

    ValidatedFactCommitter().commit(
        state,
        [{"op": "assert", "fact": ("holding", "player", item_id)}],
        source="test",
    )

    assert state.world_facts.query("holding", None, item_id) == (("holding", "player", item_id),)
    assert state.world_facts.query("room_item", None, item_id) == ()
    assert item_id in state.player.inventory
    assert item_id not in state.world.rooms[room_id].item_ids


def test_commit_updates_unique_active_goal_and_projection() -> None:
    state = build_default_state(seed=33, genre="mystery")
    next_goal = "Press the strongest lead from the case file."

    ValidatedFactCommitter().commit(
        state,
        [{"op": "assert", "fact": ("active_goal", next_goal)}],
        source="test",
    )

    assert state.world_facts.query("active_goal", None) == (("active_goal", next_goal),)
    assert state.active_goal == next_goal


def test_commit_rejects_conflicting_roles_for_the_same_name() -> None:
    state = build_default_state(seed=34, genre="mystery")
    assistant_name = state.world_facts.query("assistant_name", None)[0][1]
    state.world_facts.assert_fact("npc_role", assistant_name, "suspect")

    with pytest.raises(ValueError, match="conflicting canonical roles"):
        ValidatedFactCommitter().commit(state, (), source="test")


def test_commit_replaces_unique_profile_and_room_item_facts_and_updates_metrics() -> None:
    state = _simple_state()

    normalized = ValidatedFactCommitter().commit(
        state,
        [
            {"op": "assert", "fact": ("assistant_name", "Mara Vale")},
            {"op": "assert", "fact": ("player_name", "Detective Mara Vale")},
            {"op": "assert", "fact": ("player_background", "An exacting investigator.")},
            {"op": "assert", "fact": ("npc_role", "Daria Stone", "witness")},
            {"op": "assert", "fact": ("active_goal", "Question Daria in the study.")},
            {"op": "assert", "fact": ("room_item", "study", "case_file")},
            {"op": "numeric_delta", "key": "suspicion", "delta": 0.25},
        ],
        source="test",
    )

    assert {"op": "retract", "fact": ("assistant_name", "Daria Stone")} in normalized
    assert {"op": "retract", "fact": ("player_name", "Detective Elias Wren")} in normalized
    assert {"op": "retract", "fact": ("player_background", "A methodical detective.")} in normalized
    assert {"op": "retract", "fact": ("npc_role", "Daria Stone", "assistant")} in normalized
    assert {"op": "retract", "fact": ("active_goal", "Inspect the foyer.")} in normalized
    assert {"op": "retract", "fact": ("room_item", "foyer", "case_file")} in normalized
    assert state.world.rooms["study"].item_ids == ("case_file",)
    assert state.world.rooms["foyer"].item_ids == ()
    assert state.fact_metrics["suspicion"] == pytest.approx(0.25)
    assert state.active_goal == "Question Daria in the study."


def test_commit_retracts_player_flag_to_explicit_false() -> None:
    state = _simple_state()
    state.player.flags["story_replan_required"] = True
    state.world_facts.assert_fact("flag", "player", "story_replan_required")

    ValidatedFactCommitter().commit(
        state,
        [{"op": "retract", "fact": ("flag", "player", "story_replan_required")}],
        source="test",
    )

    assert state.player.flags["story_replan_required"] is False


def test_validator_rejects_multiple_player_locations() -> None:
    state = _simple_state()
    state.world_facts.assert_fact("at", "player", "study")

    with pytest.raises(ValueError, match="player location"):
        InvariantValidator().validate_pre_commit(state, ())


def test_validator_rejects_multiple_npc_locations() -> None:
    state = _simple_state()
    state.world_facts.assert_fact("npc_at", "daria_stone", "study")

    with pytest.raises(ValueError, match="multiple locations"):
        InvariantValidator().validate_pre_commit(state, ())


def test_validator_rejects_multiple_active_goals() -> None:
    state = _simple_state()
    state.world_facts.assert_fact("active_goal", "Search the study.")

    with pytest.raises(ValueError, match="active_goal"):
        InvariantValidator().validate_pre_commit(state, ())


def test_validator_rejects_unsupported_fact_op() -> None:
    state = _simple_state()

    with pytest.raises(ValueError, match="Unsupported fact op"):
        InvariantValidator().validate_pre_commit(state, ({"op": "mystery", "fact": ("x",)},))


def test_commit_raises_when_validator_returns_unknown_runtime_op() -> None:
    class _StubValidator:
        def validate_pre_commit(self, state, ops):  # noqa: ANN001, ARG002
            return ({"op": "mystery"},)

    class _StubProjectionUpdater:
        def refresh_from_facts(self, state):  # noqa: ANN001, ARG002
            raise AssertionError("projection refresh should not run for invalid runtime ops")

    with pytest.raises(ValueError, match="Unsupported fact op 'mystery'"):
        ValidatedFactCommitter(
            validator=_StubValidator(),
            projection_updater=_StubProjectionUpdater(),
        ).commit(_simple_state(), (), source="test")

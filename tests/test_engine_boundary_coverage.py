"""Focused regression coverage for deterministic engine boundary contracts."""

from __future__ import annotations

import pytest

from storygame.engine.consequences import _condition_bindings, _ops_for_rule, apply_consequences
from storygame.engine.interfaces import RuleModel
from storygame.engine.npc import (
    AdaptiveTraitUpdate,
    accept_task,
    cancel_task,
    complete_task,
    ensure_default_role_contracts,
    fail_task,
    offer_task,
    progress_task,
    record_epistemic_fact,
    update_adaptive_trait,
)
from storygame.engine.presentation import (
    filtered_inventory,
    npc_reference_name,
    room_arrival_lines,
    story_status_lines,
    take_item_message,
)
from storygame.engine.semantic_actions import commit_semantic_action
from storygame.engine.triggers import _last_trigger_turn, _matches_action, _trigger_eligible, evaluate_triggers
from storygame.plot.dramatic_policy import infer_beat_role, infer_dramatic_question, phase_for_progress
from tests.fast_fixtures import make_event, make_tiny_state


def _trigger(**overrides: object) -> dict[str, object]:
    trigger: dict[str, object] = {
        "trigger_id": "test_trigger",
        "kind": "action",
        "enabled": True,
        "once": True,
        "cooldown_turns": 0,
        "min_turn": 0,
        "action_types": ["take_item"],
        "actor_ids": ["player"],
        "target_ids": [],
        "item_ids": ["key"],
        "location_ids": [],
        "required_facts": [],
        "forbidden_facts": [],
        "effects": {
            "assert": [{"fact": ("flag", "player", "triggered")}],
            "retract": [{"fact": ("flag", "player", "started")}],
            "numeric_delta": [{"key": "tension", "delta": 0.1}],
            "reasons": ["test"],
            "emit_message": "triggered",
        },
    }
    trigger.update(overrides)
    return trigger


def test_trigger_evaluator_commits_declared_effect_metadata_and_rejects_ineligible_paths() -> None:
    state = make_tiny_state()
    action = make_event(
        "semantic_action",
        metadata={"action_type": "take_item", "actor_id": "player", "target_id": "", "item_id": "key"},
    )

    events = evaluate_triggers(state, (_trigger(),), (action,))

    assert events[0].metadata["fact_ops"] == [
        {"op": "assert", "fact": ("flag", "player", "triggered")},
        {"op": "retract", "fact": ("flag", "player", "started")},
        {"op": "assert", "fact": ("trigger_fired", "test_trigger")},
    ]
    state.world_facts.assert_fact("trigger_fired", "test_trigger")
    assert evaluate_triggers(state, (_trigger(),), (action,)) == []
    assert evaluate_triggers(state, (_trigger(enabled=False),), (action,)) == []
    assert evaluate_triggers(state, (_trigger(action_types=["move_to"]),), (action,)) == []
    assert evaluate_triggers(state, (_trigger(kind="turn", min_turn=2),), ()) == []


def test_trigger_evaluator_honors_turn_scope_facts_and_cooldown() -> None:
    state = make_tiny_state()
    state.turn_index = 3
    state.world_facts.assert_fact("flag", "player", "needed")
    turn_trigger = _trigger(
        kind="turn",
        once=False,
        min_turn=2,
        location_ids=[state.player.location],
        required_facts=[("flag", "player", "needed")],
        forbidden_facts=[("flag", "player", "blocked")],
    )

    assert len(evaluate_triggers(state, (turn_trigger,), ())) == 1
    state.append_event(make_event("trigger", turn_index=3, metadata={"trigger_id": "test_trigger"}))
    assert evaluate_triggers(state, (_trigger(cooldown_turns=2),), ()) == []
    state.world_facts.assert_fact("flag", "player", "blocked")
    assert evaluate_triggers(state, (turn_trigger,), ()) == []


def test_trigger_matcher_and_eligibility_reject_each_declared_constraint() -> None:
    state = make_tiny_state()
    action = make_event(
        "semantic_action",
        metadata={
            "action_type": "take_item",
            "actor_id": "player",
            "target_id": "target",
            "item_id": "key",
            "location_id": "room",
        },
    )

    assert not _matches_action(_trigger(), make_event("move"))
    for field, value in (
        ("action_types", ["move_to"]),
        ("actor_ids", ["guide"]),
        ("target_ids", ["other"]),
        ("item_ids", ["other"]),
        ("location_ids", ["other"]),
    ):
        assert not _matches_action(_trigger(**{field: value}), action)
    assert _matches_action(_trigger(target_ids=["target"], location_ids=["room"]), action)
    assert _last_trigger_turn(state, "test_trigger") is None
    state.append_event(make_event("trigger", turn_index=1, metadata={"trigger_id": "test_trigger"}))
    assert _last_trigger_turn(state, "test_trigger") == 1
    assert not _trigger_eligible(_trigger(required_facts=[("flag", "player", "missing")]), state, (action,))
    state.world_facts.assert_fact("flag", "player", "blocked")
    assert not _trigger_eligible(_trigger(forbidden_facts=[("flag", "player", "blocked")]), state, (action,))
    assert not _trigger_eligible(_trigger(kind="turn", location_ids=["elsewhere"]), state, ())


def test_semantic_actions_and_room_presentation_cover_success_and_rejections() -> None:
    state = make_tiny_state()
    item_id = "key"
    room_id = state.player.location

    take = commit_semantic_action(
        state,
        {
            "action_id": "take",
            "action_type": "take_item",
            "actor_id": "player",
            "target_id": "",
            "item_id": item_id,
            "location_id": "",
        },
    )
    move = commit_semantic_action(
        state,
        {
            "action_id": "move",
            "action_type": "move_to",
            "actor_id": "player",
            "target_id": "",
            "item_id": "",
            "location_id": room_id,
        },
    )

    assert take.metadata["fact_ops"][1]["fact"] == ("holding", "player", item_id)
    assert move.metadata["fact_ops"][0]["fact"] == ("at", "player", room_id)
    state.world_facts.assert_fact("path", "north", room_id, room_id)
    routed_move = commit_semantic_action(
        state,
        {
            "action_id": "route",
            "action_type": "move_to",
            "actor_id": "player",
            "target_id": "",
            "item_id": "",
            "location_id": "north",
        },
    )
    generic = commit_semantic_action(
        state,
        {
            "action_id": "wave",
            "action_type": "wave",
            "actor_id": "player",
            "target_id": "guide",
            "item_id": "",
            "location_id": "",
        },
    )
    assert routed_move.metadata["location_id"] == room_id
    assert generic.metadata["fact_ops"] == []
    assert room_arrival_lines(state, room_id, first_visit=True)[0].startswith("A Tiny Room:")
    with pytest.raises(ValueError, match="supports player"):
        commit_semantic_action(
            state,
            {
                "action_id": "no",
                "action_type": "take_item",
                "actor_id": "guide",
                "target_id": "",
                "item_id": item_id,
                "location_id": room_id,
            },
        )
    with pytest.raises(ValueError, match="requires a location"):
        commit_semantic_action(
            state,
            {
                "action_id": "no",
                "action_type": "move_to",
                "actor_id": "player",
                "target_id": "",
                "item_id": "",
                "location_id": "",
            },
        )
    with pytest.raises(ValueError, match="not available"):
        commit_semantic_action(
            state,
            {
                "action_id": "missing",
                "action_type": "take_item",
                "actor_id": "player",
                "target_id": "",
                "item_id": "missing",
                "location_id": room_id,
            },
        )


def test_npc_epistemic_adaptive_and_task_lifecycle_contracts() -> None:
    state = make_tiny_state()
    ensure_default_role_contracts(state)
    record_epistemic_fact(state, "guide", "knows", "the key is real")
    update_adaptive_trait(state, AdaptiveTraitUpdate(npc_id="guide", trait="trust", value=0.75))
    offer_task(state, "guide", "check_door", "player")
    accept_task(state, "guide", "check_door")
    progress_task(state, "guide", "check_door")
    fail_task(state, "guide", "check_door", "the door is barred")

    assert state.world_facts.holds("knows", "guide", "the key is real")
    assert state.world_facts.holds("npc_adaptive_trait", "guide", "trust", "0.75")
    assert state.world_facts.holds("task_consequence", "check_door", "the door is barred")
    with pytest.raises(ValueError, match="cannot transition"):
        cancel_task(state, "guide", "check_door")
    with pytest.raises(ValueError, match="unsupported epistemic"):
        record_epistemic_fact(state, "guide", "imagines", "anything")


def test_npc_completed_task_requires_a_result() -> None:
    state = make_tiny_state()
    offer_task(state, "guide", "find_key", "player")
    accept_task(state, "guide", "find_key")

    with pytest.raises(ValueError, match="require a result"):
        complete_task(state, "guide", "find_key", "")
    complete_task(state, "guide", "find_key", "the key is under the mat")
    assert state.world_facts.holds("task_result", "find_key", "the key is under the mat")


def test_consequence_bindings_and_operations_preserve_variable_constraints() -> None:
    state = make_tiny_state()
    state.world_facts.assert_fact("linked", "guide", "key")
    rule = RuleModel.model_validate(
        {
            "rule_id": "link_rule",
            "when": {
                "all": [{"predicate": "linked", "args": ["$actor", "$item"]}],
                "not": [{"predicate": "blocked", "args": ["$actor"]}],
            },
            "then": {
                "assert": [["knows", "$actor", "$item"]],
                "retract": [["linked", "$actor", "$item"]],
                "numeric_delta": [{"key": "pressure", "delta": 1}],
            },
        }
    )

    bindings = _condition_bindings(state, rule)
    assert bindings == ({"$actor": "guide", "$item": "key"},)
    assert _ops_for_rule(rule, bindings[0]) == [
        {"op": "assert", "fact": ("knows", "guide", "key")},
        {"op": "retract", "fact": ("linked", "guide", "key")},
        {"op": "numeric_delta", "key": "pressure", "delta": 1.0},
    ]
    state.world_facts.assert_fact("blocked", "guide")
    assert _condition_bindings(state, rule) == ()
    assert _condition_bindings(make_tiny_state(), rule) == ()
    with pytest.raises(ValueError, match="exceeded"):
        apply_consequences(make_tiny_state(), max_rounds=0)


def test_presentation_helpers_keep_fact_backed_inventory_and_names_readable() -> None:
    state = make_tiny_state()
    npc = state.world.npcs["guide"]
    npc.name = "Detective Guide"
    state.player.inventory = ("key",)
    state.world.items["key"].kind = "evidence"
    state.world.items["key"].clue_text = "The key bears fresh scratches."

    assert npc_reference_name(state, npc) == "Detective Guide"
    assert npc_reference_name(state, npc) == "Guide"
    assert filtered_inventory(state) == ("key",)
    assert take_item_message(state.world.items["key"]).startswith("Evidence secured")
    assert any("Current objective" in line for line in story_status_lines(state))


@pytest.mark.parametrize(
    ("phase", "approach", "pressure", "expected"),
    [
        ("falling_action", "observe", "guarded", "aftermath"),
        ("climax", "observe", "guarded", "confrontation"),
        ("rising_action", "coerce", "critical", "escalation"),
        ("exposition", "rapport", "guarded", "orientation"),
        ("rising_action", "reposition", "guarded", "pressure"),
    ],
)
def test_dramatic_policy_covers_role_and_question_variants(
    phase: str, approach: str, pressure: str, expected: str
) -> None:
    assert infer_beat_role(phase, approach, pressure) == expected
    assert infer_beat_role("resolution", "observe", "guarded") == "closure"
    assert phase_for_progress(0.2, " crisis ") == "crisis"
    assert "Guide" in infer_dramatic_question(goal="", approach="coerce", intent="ask", target_name="Guide")
    assert "Guide" in infer_dramatic_question(goal="", approach="rapport", intent="talk", target_name="Guide")
    assert "current lead" not in infer_dramatic_question(goal="", approach="observe", intent="wait")

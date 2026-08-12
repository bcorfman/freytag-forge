from __future__ import annotations

import pytest

from storygame.engine.npc import (
    AdaptiveTraitUpdate,
    NpcActionRequest,
    RoleContract,
    accept_task,
    cancel_task,
    complete_task,
    fail_task,
    install_role_contract,
    offer_task,
    progress_task,
    record_epistemic_fact,
    role_facts,
    update_adaptive_trait,
    validate_npc_action,
)
from storygame.engine.world import build_tiny_state


def test_role_contract_is_fact_backed_and_adaptive_traits_are_bounded() -> None:
    state = build_tiny_state(501)
    install_role_contract(
        state,
        RoleContract(
            npc_id="daria_stone",
            role="assistant",
            goals=("keep the investigation fair",),
            capabilities=("advise", "investigate"),
            limitations=("cannot enter the locked wing",),
            initiative_policy="when_evidence_changes",
            advisory_style="measured",
            permitted_autonomy=("offer_task",),
            stable_traits=("observant",),
            adaptive_traits={"trust": 0.4, "urgency": 0.2},
        ),
    )

    assert state.world_facts.holds("npc_role", "daria_stone", "assistant")
    assert state.world_facts.holds("npc_stable_trait", "daria_stone", "observant")
    assert state.world_facts.holds("npc_adaptive_trait", "daria_stone", "trust", "0.4")
    update_adaptive_trait(state, AdaptiveTraitUpdate(npc_id="daria_stone", trait="trust", value=0.7))
    assert state.world_facts.holds("npc_adaptive_trait", "daria_stone", "trust", "0.7")
    with pytest.raises(ValueError):
        update_adaptive_trait(state, AdaptiveTraitUpdate(npc_id="daria_stone", trait="trust", value=1.1))


def test_task_lifecycle_requires_commitments_and_is_fact_backed() -> None:
    state = build_tiny_state(502)
    offer_task(state, "daria_stone", "verify_ledger", "player")
    assert state.world_facts.holds("task", "daria_stone", "verify_ledger", "offered")
    accept_task(state, "daria_stone", "verify_ledger")
    assert state.world_facts.holds("task", "daria_stone", "verify_ledger", "accepted")
    complete_task(state, "daria_stone", "verify_ledger", "ledger confirmed")
    assert state.world_facts.holds("task", "daria_stone", "verify_ledger", "completed")
    assert state.world_facts.holds("task_result", "verify_ledger", "ledger confirmed")
    with pytest.raises(ValueError, match="cannot transition"):
        accept_task(state, "daria_stone", "verify_ledger")


def test_npc_action_validation_checks_role_knowledge_location_and_resources() -> None:
    state = build_tiny_state(503)
    install_role_contract(
        state,
        RoleContract(
            npc_id="daria_stone",
            role="assistant",
            capabilities=("treat",),
            limitations=(),
            stable_traits=(),
            adaptive_traits={},
        ),
    )
    state.world_facts.assert_fact("knows", "daria_stone", "signal")
    request = NpcActionRequest(
        actor_id="daria_stone",
        action="treat",
        target_id="player",
        required_knowledge=("signal",),
    )
    assert validate_npc_action(state, request).accepted
    state.world_facts.retract_fact("knows", "daria_stone", "signal")
    assert not validate_npc_action(state, request).accepted


def test_epistemic_facts_and_role_projection_are_explicit() -> None:
    state = build_tiny_state(504)
    record_epistemic_fact(state, "daria_stone", "believes", "signal")
    record_epistemic_fact(state, "daria_stone", "may_infer", "route")
    projection = role_facts(state, "daria_stone")
    assert state.world_facts.holds("believes", "daria_stone", "signal")
    assert state.world_facts.holds("may_infer", "daria_stone", "route")
    assert projection["role"] == "assistant"
    with pytest.raises(ValueError, match="unsupported epistemic"):
        record_epistemic_fact(state, "daria_stone", "guesses", "signal")


def test_companion_rival_adviser_medic_and_navigator_share_role_machinery() -> None:
    state = build_tiny_state(505)
    role_ids = dict(
        zip(
            ("companion", "rival", "adviser", "medic", "navigator"),
            tuple(state.world.npcs)[:5],
            strict=True,
        )
    )
    for role, npc_id in role_ids.items():
        install_role_contract(
            state,
            RoleContract(npc_id=npc_id, role=role, capabilities=("observe",), stable_traits=()),
        )
        assert validate_npc_action(
            state,
            NpcActionRequest(
                actor_id=npc_id,
                action="observe",
                scene_location=state.world_facts.query("npc_at", npc_id, None)[0][2],
            ),
        ).accepted


def test_task_fail_cancel_and_action_rejections_are_deterministic() -> None:
    state = build_tiny_state(506)
    offer_task(state, "daria_stone", "check_signal", "player")
    accept_task(state, "daria_stone", "check_signal")
    progress_task(state, "daria_stone", "check_signal")
    fail_task(state, "daria_stone", "check_signal", "the trail went cold")
    assert state.world_facts.holds("task_consequence", "check_signal", "the trail went cold")

    offer_task(state, "daria_stone", "bring_note", "player")
    cancel_task(state, "daria_stone", "bring_note")
    assert state.world_facts.holds("task", "daria_stone", "bring_note", "cancelled")
    assert not validate_npc_action(
        state,
        NpcActionRequest(actor_id="daria_stone", action="unknown_action"),
    ).accepted
    with pytest.raises(ValueError, match="unknown observer"):
        record_epistemic_fact(state, "missing_npc", "knows", "signal")

"""Fact-backed NPC roles, epistemic state, actions, and delegated work.

The module deliberately keeps presentation details out of the authority path:
role and task facts are canonical, while the typed models are boundary
contracts for authoring and runtime proposals.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from storygame.engine.fact_commit import ValidatedFactCommitter
from storygame.engine.facts import npc_location, player_location
from storygame.engine.perception import ObservationResolver


class RoleContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    npc_id: str = Field(min_length=1, max_length=80)
    role: str = Field(min_length=1, max_length=60)
    goals: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    initiative_policy: str = "scene_prompted"
    advisory_style: str = "direct"
    permitted_autonomy: tuple[str, ...] = ()
    stable_traits: tuple[str, ...] = ()
    adaptive_traits: dict[str, float] = Field(default_factory=dict)
    relationship_to_player: str = "neutral"


class AdaptiveTraitUpdate(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    npc_id: str = Field(min_length=1, max_length=80)
    trait: str = Field(min_length=1, max_length=60)
    value: float = Field(ge=0.0, le=1.0)


class NpcActionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    actor_id: str = Field(min_length=1, max_length=80)
    action: str = Field(min_length=1, max_length=80)
    target_id: str = ""
    required_knowledge: tuple[str, ...] = ()
    required_resource: str = ""
    scene_location: str = ""
    autonomous: bool = False
    required_task: str = ""


class NpcActionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    accepted: bool
    reason: str
    actor_id: str
    action: str


_TASK_STATUSES = ("offered", "accepted", "in_progress", "completed", "failed", "cancelled")
_TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled"}
_EPISTEMIC_PREDICATES = {"knows", "believes", "suspects", "conceals", "may_infer"}


def _commit(state, ops: list[dict[str, object]], source: str = "npc_policy") -> None:
    ValidatedFactCommitter().commit(state, ops, source=source)


def install_role_contract(state, contract: RoleContract) -> None:
    """Install one complete role contract as canonical facts."""
    if contract.npc_id not in state.world.npcs:
        raise ValueError(f"unknown NPC '{contract.npc_id}'")
    ops: list[dict[str, object]] = [
        {"op": "retract", "fact": fact}
        for fact in state.world_facts.query("npc_role", contract.npc_id, None)
    ]
    ops.append({"op": "assert", "fact": ("npc_role", contract.npc_id, contract.role)})
    for predicate, values in (
        ("npc_goal", contract.goals),
        ("npc_capability", contract.capabilities),
        ("npc_limitation", contract.limitations),
        ("npc_stable_trait", contract.stable_traits),
        ("npc_autonomy", contract.permitted_autonomy),
    ):
        ops.extend({"op": "assert", "fact": (predicate, contract.npc_id, value)} for value in values)
    ops.extend(
        [
            {"op": "assert", "fact": ("npc_initiative", contract.npc_id, contract.initiative_policy)},
            {"op": "assert", "fact": ("npc_advisory_style", contract.npc_id, contract.advisory_style)},
        ]
    )
    for trait, value in contract.adaptive_traits.items():
        _validate_trait_value(value)
        ops.append(
            {"op": "assert", "fact": ("npc_adaptive_trait", contract.npc_id, trait, _format_value(value))}
        )
    ops.extend(
        {"op": "retract", "fact": fact}
        for fact in state.world_facts.query("npc_relationship", contract.npc_id, "player", None)
    )
    ops.append(
        {"op": "assert", "fact": ("npc_relationship", contract.npc_id, "player", contract.relationship_to_player)}
    )
    _commit(state, ops, "npc_role_bootstrap")


def update_adaptive_trait(state, update: AdaptiveTraitUpdate) -> None:
    """Replace a declared adaptive trait; no undeclared trait can appear."""
    _validate_trait_value(update.value)
    existing = state.world_facts.query("npc_adaptive_trait", update.npc_id, update.trait, None)
    if not existing:
        raise ValueError(f"adaptive trait '{update.trait}' is not declared")
    ops = [{"op": "retract", "fact": fact} for fact in existing]
    ops.append(
        {"op": "assert", "fact": ("npc_adaptive_trait", update.npc_id, update.trait, _format_value(update.value))}
    )
    _commit(state, ops)


def record_epistemic_fact(state, observer: str, kind: str, proposition: str) -> None:
    """Record one explicit knowledge/belief boundary for an actor."""
    normalized_kind = kind.strip().lower()
    if normalized_kind not in _EPISTEMIC_PREDICATES:
        raise ValueError(f"unsupported epistemic state '{kind}'")
    if observer != "player" and observer not in state.world.npcs:
        raise ValueError(f"unknown observer '{observer}'")
    if not proposition.strip():
        raise ValueError("epistemic propositions must not be empty")
    _commit(state, [{"op": "assert", "fact": (normalized_kind, observer, proposition.strip())}])


def offer_task(state, actor_id: str, task_id: str, offered_by: str) -> None:
    _require_npc(state, actor_id)
    if state.world_facts.query("task", actor_id, task_id, None):
        raise ValueError(f"task '{task_id}' already exists")
    _commit(
        state,
        [
            {"op": "assert", "fact": ("task", actor_id, task_id, "offered")},
            {"op": "assert", "fact": ("task_offer", task_id, offered_by, actor_id)},
        ],
    )


def accept_task(state, actor_id: str, task_id: str) -> None:
    _transition_task(state, actor_id, task_id, "offered", "accepted")


def progress_task(state, actor_id: str, task_id: str) -> None:
    _transition_task(state, actor_id, task_id, "accepted", "in_progress")


def complete_task(state, actor_id: str, task_id: str, result: str) -> None:
    if not result.strip():
        raise ValueError("completed tasks require a result")
    current = _task_status(state, actor_id, task_id)
    if current not in {"accepted", "in_progress"}:
        raise ValueError(f"task '{task_id}' cannot transition from {current} to completed")
    _transition_task(state, actor_id, task_id, current, "completed")
    _commit(state, [{"op": "assert", "fact": ("task_result", task_id, result.strip())}])


def fail_task(state, actor_id: str, task_id: str, consequence: str = "") -> None:
    _transition_task(state, actor_id, task_id, "in_progress", "failed")
    if consequence.strip():
        _commit(state, [{"op": "assert", "fact": ("task_consequence", task_id, consequence.strip())}])


def cancel_task(state, actor_id: str, task_id: str) -> None:
    current = _task_status(state, actor_id, task_id)
    if current in _TERMINAL_TASK_STATUSES:
        raise ValueError(f"task '{task_id}' cannot transition from {current}")
    _transition_task(state, actor_id, task_id, current, "cancelled")


def validate_npc_action(state, request: NpcActionRequest) -> NpcActionDecision:
    """Validate an NPC action without mutating facts."""
    actor_id = request.actor_id.strip()
    action = request.action.strip().lower()
    if actor_id not in state.world.npcs:
        return _rejected(actor_id, action, "unknown NPC")
    capabilities = {fact[2].lower() for fact in state.world_facts.query("npc_capability", actor_id, None)}
    if action not in capabilities:
        return _rejected(actor_id, action, "role does not permit this capability")
    known = {fact[2] for fact in state.world_facts.query("knows", actor_id, None)}
    missing = tuple(value for value in request.required_knowledge if value not in known)
    if missing:
        return _rejected(actor_id, action, "required knowledge is unavailable")
    actor_room = npc_location(state, actor_id)
    required_room = request.scene_location.strip() or player_location(state)
    if actor_room != required_room:
        return _rejected(actor_id, action, "NPC is not in the required scene")
    if request.target_id:
        observation = ObservationResolver(state).resolve(actor_id, request.target_id)
        if not observation.perceptible:
            return _rejected(actor_id, action, "target is not visible to the NPC")
    if request.required_resource and not state.world_facts.holds("holding", actor_id, request.required_resource):
        return _rejected(actor_id, action, "required resource is unavailable")
    if request.required_task:
        status = _task_status(state, actor_id, request.required_task)
        if status not in {"accepted", "in_progress"}:
            return _rejected(actor_id, action, "required obligation is not active")
    if request.autonomous and action not in {
        fact[2].lower() for fact in state.world_facts.query("npc_autonomy", actor_id, None)
    }:
        return _rejected(actor_id, action, "autonomous behavior is not permitted")
    return NpcActionDecision(accepted=True, reason="accepted", actor_id=actor_id, action=action)


def role_facts(state, npc_id: str) -> dict[str, object]:
    """Return a bounded, fact-backed role projection for model context."""
    return {
        "role": _first(state, "npc_role", npc_id) or "",
        "goals": tuple(fact[2] for fact in state.world_facts.query("npc_goal", npc_id, None)),
        "capabilities": tuple(fact[2] for fact in state.world_facts.query("npc_capability", npc_id, None)),
        "limitations": tuple(fact[2] for fact in state.world_facts.query("npc_limitation", npc_id, None)),
        "initiative_policy": _first(state, "npc_initiative", npc_id) or "",
        "advisory_style": _first(state, "npc_advisory_style", npc_id) or "",
        "relationship_to_player": _first_relationship(state, npc_id),
        "stable_traits": tuple(fact[2] for fact in state.world_facts.query("npc_stable_trait", npc_id, None)),
        "adaptive_traits": {
            fact[2]: float(fact[3]) for fact in state.world_facts.query("npc_adaptive_trait", npc_id, None, None)
        },
    }


def ensure_default_role_contracts(state) -> None:
    """Give package-created NPCs a minimal role contract without story branches."""
    for npc_id, npc in state.world.npcs.items():
        if not state.world_facts.query("npc_role", npc_id, None):
            named_roles = state.world_facts.query("npc_role", npc.name, None)
            role = named_roles[0][2] if named_roles else "participant"
            ops: list[dict[str, object]] = [
                {"op": "assert", "fact": ("npc_role", npc_id, role)},
                {"op": "assert", "fact": ("npc_initiative", npc_id, "scene_prompted")},
                {"op": "assert", "fact": ("npc_advisory_style", npc_id, "direct")},
                {"op": "assert", "fact": ("npc_adaptive_trait", npc_id, "trust", "0.5")},
            ]
            ops.extend(
                {"op": "assert", "fact": ("npc_stable_trait", npc_id, trait)}
                for trait in npc.tags
            )
            _commit(state, ops, "npc_role_bootstrap")


def _transition_task(state, actor_id: str, task_id: str, expected: str, target: str) -> None:
    current = _task_status(state, actor_id, task_id)
    if current != expected:
        raise ValueError(f"task '{task_id}' cannot transition from {current} to {target}")
    _commit(
        state,
        [
            {"op": "retract", "fact": ("task", actor_id, task_id, current)},
            {"op": "assert", "fact": ("task", actor_id, task_id, target)},
        ],
    )


def _task_status(state, actor_id: str, task_id: str) -> str:
    facts = state.world_facts.query("task", actor_id, task_id, None)
    if not facts:
        raise ValueError(f"unknown task '{task_id}'")
    return facts[0][3]


def _require_npc(state, npc_id: str) -> None:
    if npc_id not in state.world.npcs:
        raise ValueError(f"unknown NPC '{npc_id}'")


def _first(state, predicate: str, npc_id: str) -> str | None:
    facts = state.world_facts.query(predicate, npc_id, None)
    return facts[0][2] if facts else None


def _first_relationship(state, npc_id: str) -> str:
    facts = state.world_facts.query("npc_relationship", npc_id, "player", None)
    return facts[0][3] if facts else ""


def _validate_trait_value(value: float) -> None:
    if not 0.0 <= float(value) <= 1.0:
        raise ValueError("adaptive trait values must remain bounded between 0 and 1")


def _format_value(value: float) -> str:
    return f"{float(value):.6g}"


def _rejected(actor_id: str, action: str, reason: str) -> NpcActionDecision:
    return NpcActionDecision(accepted=False, reason=reason, actor_id=actor_id, action=action)

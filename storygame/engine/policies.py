from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from storygame.engine.interfaces import load_policy_bundle

PredicateFamily = Literal[
    "world",
    "perception",
    "knowledge",
    "relationships",
    "tasks",
    "traces",
    "dramatic",
]


class PredicatePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(min_length=1)
    arity: int = Field(ge=1)
    arg_types: tuple[str, ...] = ()
    invariants: tuple[str, ...] = ()
    family: PredicateFamily
    commit_sources: tuple[str, ...]
    normalization: Literal["trim", "identifier", "literal"]
    derived_update_owner: str = Field(min_length=1)
    proposal_allowed: bool = True


class IntentEffectPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    family: str
    aliases: tuple[str, ...]
    bounded_effects: tuple[str, ...]


_INTENT_POLICIES = (
    IntentEffectPolicy(
        family="movement", aliases=("move", "go", "walk", "travel", "head"), bounded_effects=("move_to",)
    ),
    IntentEffectPolicy(
        family="examination",
        aliases=("examine", "inspect", "search", "study", "read"),
        bounded_effects=("observe", "discover"),
    ),
    IntentEffectPolicy(
        family="communication",
        aliases=("talk", "ask", "tell", "say", "question", "greet"),
        bounded_effects=("dialogue", "relationship"),
    ),
    IntentEffectPolicy(
        family="manipulation", aliases=("use", "open", "close", "activate", "repair"), bounded_effects=("state_change",)
    ),
    IntentEffectPolicy(
        family="transfer", aliases=("take", "get", "give", "drop", "hand"), bounded_effects=("transfer_item",)
    ),
    IntentEffectPolicy(
        family="concealment", aliases=("hide", "conceal", "cover", "stash"), bounded_effects=("conceal",)
    ),
    IntentEffectPolicy(
        family="assistance", aliases=("help", "assist", "support", "follow"), bounded_effects=("relationship", "task")
    ),
    IntentEffectPolicy(
        family="opposition",
        aliases=("threaten", "attack", "oppose", "resist", "challenge"),
        bounded_effects=("relationship", "condition"),
    ),
    IntentEffectPolicy(
        family="waiting", aliases=("wait", "rest", "listen", "pause"), bounded_effects=("advance_time",)
    ),
)
_INTENT_ALIAS_MAP = {alias: policy.family for policy in _INTENT_POLICIES for alias in policy.aliases}
_IDENTIFIER = re.compile(r"[^a-z0-9_:-]+")


class PredicatePolicyRegistry:
    def __init__(self, policies: tuple[PredicatePolicy, ...], rule_ids: tuple[str, ...]) -> None:
        self._policies = {policy.name: policy for policy in policies}
        self.rule_ids = rule_ids

    @classmethod
    def for_genre(cls, genre: str = "") -> PredicatePolicyRegistry:
        bundle = load_policy_bundle(genre)
        policies = tuple(PredicatePolicy.model_validate(item) for item in bundle["predicates"])
        return cls(policies, tuple(item["rule_id"] for item in bundle["rules"]))

    def get(self, predicate: str) -> PredicatePolicy | None:
        return self._policies.get(predicate)

    def validate(self, fact: tuple[str, ...], source: str = "proposal") -> tuple[str, ...]:
        if not fact or not str(fact[0]).strip():
            raise ValueError("unauthorized predicate: empty predicate")
        predicate_name = str(fact[0]).strip()
        policy = self.get(predicate_name)
        proposal_source_allowed = bool(
            policy is not None and source == "proposal" and "intent" in policy.commit_sources
        )
        if (
            policy is None
            or not policy.proposal_allowed
            or (source not in policy.commit_sources and not proposal_source_allowed)
        ):
            raise ValueError(f"unauthorized predicate '{predicate_name}' for source '{source}'")
        if len(fact) - 1 != policy.arity:
            raise ValueError(f"predicate '{predicate_name}' expects {policy.arity} terms, got {len(fact) - 1}")
        return (predicate_name, *(self._normalize(term, policy.normalization) for term in fact[1:]))

    @staticmethod
    def _normalize(value: Any, mode: str) -> str:
        normalized = str(value).strip()
        if mode == "identifier":
            normalized = _IDENTIFIER.sub("_", normalized.lower()).strip("_")
        return normalized


def validate_proposed_fact_ops(
    state: Any,
    ops: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    registry: PredicatePolicyRegistry,
) -> tuple[dict[str, Any], ...]:
    del state  # Validation is intentionally side-effect free; commit owns state checks.
    normalized: list[dict[str, Any]] = []
    for op in ops:
        operation = str(op.get("op", "")).strip()
        if operation not in {"assert", "retract"}:
            raise ValueError(f"proposal policy rejects operation '{operation}'")
        raw_fact = tuple(op.get("fact", ()))
        normalized.append({"op": operation, "fact": registry.validate(raw_fact)})
    return tuple(normalized)


def normalize_intent_family(intent: str) -> str:
    normalized = re.sub(r"[^a-z0-9_]+", " ", intent.strip().lower()).strip()
    if normalized in _INTENT_ALIAS_MAP:
        return _INTENT_ALIAS_MAP[normalized]
    first_word = normalized.split(" ", 1)[0] if normalized else ""
    return _INTENT_ALIAS_MAP.get(first_word, "manipulation")


def resolve_visible_aliases(state: Any, phrase: str, kind: str = "item") -> tuple[str, ...]:
    """Return all visible canonical matches; callers must clarify when >1."""
    normalized = re.sub(r"[^a-z0-9]+", "_", phrase.strip().lower()).strip("_")
    if not normalized:
        return ()
    room_id = state.world_facts.query("at", "player", None)
    current_room = room_id[0][2] if room_id else state.player.location
    candidates = (
        tuple(fact[2] for fact in state.world_facts.query("room_item", current_room, None))
        if kind == "item"
        else tuple(fact[1] for fact in state.world_facts.query("npc_at", None, current_room))
    )
    matches: list[str] = []
    for entity_id in candidates:
        entity = state.world.items.get(entity_id) if kind == "item" else state.world.npcs.get(entity_id)
        labels = (entity_id, entity.name if entity is not None else "")
        for label in labels:
            label_normalized = re.sub(r"[^a-z0-9]+", "_", str(label).lower()).strip("_")
            if normalized == label_normalized or normalized in label_normalized.split("_"):
                matches.append(entity_id)
                break
    return tuple(dict.fromkeys(matches))


def intent_policy(family: str) -> IntentEffectPolicy:
    for policy in _INTENT_POLICIES:
        if policy.family == family:
            return policy
    raise ValueError(f"Unknown intent-effect policy family '{family}'.")

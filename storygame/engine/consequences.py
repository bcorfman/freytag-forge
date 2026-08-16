"""Deterministic post-direct-effect causal rule execution."""

from __future__ import annotations

from typing import Any

from storygame.engine.fact_commit import ValidatedFactCommitter
from storygame.engine.interfaces import RuleModel, load_policy_bundle
from storygame.engine.policies import PredicatePolicyRegistry, validate_proposed_fact_ops
from storygame.engine.state import Event, GameState


def _term_matches(term: str, value: str, bindings: dict[str, str]) -> bool:
    if not term.startswith("$"):
        return term == value
    bound = bindings.get(term)
    if bound is None:
        bindings[term] = value
        return True
    return bound == value


def _condition_bindings(state: GameState, rule: RuleModel) -> tuple[dict[str, str], ...]:
    bindings: list[dict[str, str]] = [{}]
    for condition in rule.when.all:
        next_bindings: list[dict[str, str]] = []
        for candidate in state.world_facts.query(condition.predicate):
            if len(candidate) != len(condition.args) + 1:
                continue
            for current in bindings:
                trial = dict(current)
                if all(
                    _term_matches(term, value, trial) for term, value in zip(condition.args, candidate[1:], strict=True)
                ):
                    next_bindings.append(trial)
        bindings = next_bindings
        if not bindings:
            return ()

    accepted: list[dict[str, str]] = []
    for binding in bindings:
        rejected = False
        for condition in rule.when.not_conditions:
            for candidate in state.world_facts.query(condition.predicate):
                if len(candidate) != len(condition.args) + 1:
                    continue
                trial = dict(binding)
                if all(
                    _term_matches(term, value, trial) for term, value in zip(condition.args, candidate[1:], strict=True)
                ):
                    rejected = True
                    break
            if rejected:
                break
        if not rejected:
            accepted.append(binding)
    return tuple(sorted(accepted, key=lambda item: tuple(sorted(item.items()))))


def _substitute(fact: tuple[str, ...], bindings: dict[str, str]) -> tuple[str, ...]:
    return tuple(bindings.get(term, term) for term in fact)


def _ops_for_rule(rule: RuleModel, bindings: dict[str, str]) -> list[dict[str, Any]]:
    ops: list[dict[str, Any]] = []
    ops.extend({"op": "assert", "fact": _substitute(fact, bindings)} for fact in rule.then.assert_facts)
    ops.extend({"op": "retract", "fact": _substitute(fact, bindings)} for fact in rule.then.retract_facts)
    ops.extend(
        {"op": "numeric_delta", "key": _substitute((delta.key,), bindings)[0], "delta": delta.delta}
        for delta in rule.then.numeric_delta
    )
    return ops


def apply_consequences(state: GameState, *, max_rounds: int = 8) -> dict[str, Any]:
    """Apply each newly eligible declarative rule binding once, in stable order."""
    bundle = load_policy_bundle(state.story_genre)
    registry = PredicatePolicyRegistry.for_genre(state.story_genre)
    rules = tuple(RuleModel.model_validate(item) for item in bundle["rules"])
    fired: set[tuple[str, tuple[tuple[str, str], ...]]] = set()
    applied: list[str] = []
    events: list[Event] = []

    for _round in range(max_rounds):
        changed = False
        for rule in rules:
            for binding in _condition_bindings(state, rule):
                key = (rule.rule_id, tuple(sorted(binding.items())))
                if key in fired:
                    continue
                fired.add(key)
                raw_ops = _ops_for_rule(rule, binding)
                fact_ops = tuple(op for op in raw_ops if op["op"] != "numeric_delta")
                normalized = validate_proposed_fact_ops(state, fact_ops, registry=registry)
                numeric = tuple(op for op in raw_ops if op["op"] == "numeric_delta")
                ops = (*normalized, *numeric)
                if not ops:
                    continue
                ValidatedFactCommitter().commit(state, ops, source=f"rule:{rule.rule_id}")
                event = Event(
                    type="consequence",
                    message_key=rule.rule_id,
                    entities=tuple(binding[key] for key in sorted(binding)),
                    tags=("consequence", "rule"),
                    turn_index=state.turn_index,
                    metadata={"rule_id": rule.rule_id, "bindings": dict(binding), "fact_ops": list(ops)},
                )
                events.append(event)
                applied.append(rule.rule_id)
                changed = True
        if not changed:
            break
    else:
        raise ValueError(f"Consequence evaluation exceeded {max_rounds} rounds.")

    return {"events": tuple(events), "applied_rule_ids": tuple(applied)}

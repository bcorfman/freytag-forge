"""Deterministic, read-only story rules for reporting situation gaps."""

from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from storygame.runtime.facts import Fact
from storygame.runtime.reveal_eligibility import explain_reveal
from storygame.runtime.state import RuntimeState
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import KnowledgeDefinition, StoryPackage, Transition


@dataclass(frozen=True)
class Flag:
    rule: str
    anchor: str
    subject: str
    summary: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class _Producer:
    kind: str
    text: str
    record_id: str | None


@dataclass(frozen=True)
class _CustodyFinding:
    anchor: str
    transition: Transition
    claim: KnowledgeDefinition
    item_id: str
    character_id: str | None
    state: RuntimeState
    status: Literal["checked", "unchecked", "untested"]


@dataclass(frozen=True)
class CustodyCheck:
    claim_id: str
    item_id: str
    character_id: str | None
    status: Literal["checked", "unchecked", "untested"]

    @property
    def holder_checked(self) -> bool:
        return self.status == "checked"


def _operation_value(operation: object) -> object:
    value = getattr(operation, "value", None)
    return True if value is None else value


def _same_value(left: object, right: object) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return str(left).lower() == str(right).lower()
    return left == right


def _true(facts, fact_id: str) -> bool:
    return any(str(fact.value).lower() == "true" for fact in facts.matching(fact_id, "story"))


def _claim_source(claim: KnowledgeDefinition) -> str:
    source = claim.source
    return source.realization_id or source.storylet_id or source.kind


def _claim_names(claim: KnowledgeDefinition) -> set[str]:
    return set(claim.entity_ids) | set(claim.relevance.entity_ids)


def _transition_claims(package: StoryPackage, transition: Transition) -> list[KnowledgeDefinition]:
    triggers = {(trigger.fact_id, trigger.equals) for trigger in transition.triggers}
    return [
        claim
        for claim in package.knowledge.knowledge
        if any(effect.op == "assert" and (effect.fact_id, effect.value) in triggers for effect in claim.establishes)
    ]


def _anchor_matches(package: StoryPackage, anchor: str) -> list[tuple[str, object]]:
    matches: list[tuple[str, object]] = []
    matches.extend(("pacing event", event) for event in package.pacing.events if event.id == anchor)
    matches.extend(("incident", incident) for incident in package.incidents if incident.id == anchor)
    matches.extend(("transition", transition) for transition in package.pacing.transitions if transition.id == anchor)
    return matches


def _anchor_item(package: StoryPackage, anchor: str) -> tuple[str, object]:
    matches = _anchor_matches(package, anchor)
    if not matches:
        raise ValueError(f"unknown anchor '{anchor}'")
    if len(matches) > 1:
        raise ValueError(f"ambiguous anchor '{anchor}': {', '.join(kind for kind, _ in matches)}")
    return matches[0]


def exit_transitions(package: StoryPackage, anchor: str) -> list[Transition]:
    """Return the authored exits represented by an anchor."""

    kind, item = _anchor_item(package, anchor)
    if kind == "pacing event":
        return sorted(
            (transition for transition in package.pacing.transitions if transition.source_scene_id == item.scene_id),
            key=lambda transition: (transition.priority, transition.id),
        )
    if kind == "incident":
        if item.successor_transition_id is None:
            return []
        return [
            transition for transition in package.pacing.transitions if transition.id == item.successor_transition_id
        ]
    return [item]


def _source_location(root: Path, record_id: str) -> str | None:
    id_value = rf"{re.escape(record_id)}(?=\s*(?:$|[,}}#]))"
    list_id = re.compile(rf"^\s*-\s+id:\s*{id_value}")
    flow_id = re.compile(rf"(?:\{{|,)\s*id:\s*{id_value}")
    mapping_line = re.compile(rf"^\s*{re.escape(record_id)}:\s*(?:#.*)?$")
    paths = sorted(root.rglob("*.yaml"))
    for path in paths:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if list_id.search(line) or flow_id.search(line) or mapping_line.search(line):
                return f"{path.relative_to(root).as_posix()}:{line_number}"
    return None


def _located(root: Path, text: str, record_id: str | None = None) -> str:
    location = _source_location(root, record_id) if record_id else None
    return f"{text} {location}" if location else text


def _reachable_facts(package: StoryPackage, seed_facts: set[str], fired_storylets: set[str]) -> set[str]:
    """Every fact still committable from this state, including Deadline recovery."""

    pacing_facts = {effect.fact_id for event in package.pacing.events for effect in event.effects}
    delivery_facts = {delivery.fact_id for delivery in package.deliveries}
    facts = set(seed_facts) | pacing_facts | delivery_facts
    changed = True
    while changed:
        changed = False
        for route in package.storylet_routes.storylets:
            if route.id in fired_storylets:
                continue
            eligible = all(
                (predicate.fact_id in facts) if predicate.equals is not False else (predicate.fact_id not in seed_facts)
                for predicate in route.activation_conditions
            )
            if not eligible:
                continue
            for realization in route.realizations:
                for operation in realization.operations:
                    if operation.op == "assert" and operation.fact_id not in facts:
                        facts.add(operation.fact_id)
                        changed = True
        for event in package.storylet_routes.bridge_events:
            if event.activation.is_satisfied(frozenset(facts)):
                for operation in event.operations:
                    if operation.op == "assert" and operation.fact_id not in facts:
                        facts.add(operation.fact_id)
                        changed = True
    return facts


def _first_sentence(text: str) -> str:
    match = re.search(r".*?[.!?](?:\s|$)", text.strip(), re.DOTALL)
    return match.group(0).strip() if match else text.strip()


def _baseline(
    package: StoryPackage,
    anchor: str,
    transition: Transition,
    claim: KnowledgeDefinition,
) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    if transition.source_scene_id != state.current_scene_id:
        apply_scene_placements(package, state.facts, transition.source_scene_id)
        state.current_scene_id = transition.source_scene_id

    for predicate in claim.requires:
        state.facts.assert_fact(Fact(predicate=predicate.fact_id, subject="story", value="true"))

    kind, item = _anchor_item(package, anchor)
    if kind == "pacing event":
        for predicate in item.when:
            state.facts.assert_fact(Fact(predicate=predicate.fact_id, subject="story", value="true"))

    established_facts = {effect.fact_id for effect in claim.establishes if effect.op == "assert"}
    for trigger in transition.triggers:
        if trigger.fact_id not in established_facts:
            state.facts.assert_fact(Fact(predicate=trigger.fact_id, subject="story", value="true"))

    apply_world_effects(package, state.facts)
    if claim.source.storylet_id:
        state.active_event_ids.add(claim.source.storylet_id)
    return state


def _candidate_items(package: StoryPackage, state: RuntimeState, claim: KnowledgeDefinition) -> list[str]:
    world = world_for(package, state.facts)
    return sorted(
        entity_id
        for entity_id in _claim_names(claim)
        if world.exists(entity_id) and world.is_item(entity_id) and not world.schema.is_fixed(entity_id)
    )


def _eligible(state: RuntimeState, claim: KnowledgeDefinition) -> bool:
    return explain_reveal(state, "player", claim).reason == "eligible"


def _other_character(world, protagonist_id: str) -> str | None:
    return next(iter(world.characters_together(protagonist_id)), None)


def _custody_findings(package: StoryPackage, anchor: str) -> list[_CustodyFinding]:
    findings: list[_CustodyFinding] = []
    for transition in exit_transitions(package, anchor):
        for claim in _transition_claims(package, transition):
            state = _baseline(package, anchor, transition, claim)
            if not _eligible(state, claim):
                continue
            world = world_for(package, state.facts)
            character_id = _other_character(world, package.world.protagonist_id)
            for item_id in _candidate_items(package, state, claim):
                if not world.holds(package.world.protagonist_id, item_id):
                    continue
                if character_id is None:
                    findings.append(
                        _CustodyFinding(
                            anchor,
                            transition,
                            claim,
                            item_id,
                            None,
                            state,
                            "untested",
                        )
                    )
                    continue
                hypothetical_state = deepcopy(state)
                hypothetical_world = world_for(package, hypothetical_state.facts)
                hypothetical = hypothetical_world.move(item_id, character_id)
                if not hypothetical.ok:
                    continue
                findings.append(
                    _CustodyFinding(
                        anchor,
                        transition,
                        claim,
                        item_id,
                        character_id,
                        state,
                        "checked" if not _eligible(hypothetical_state, claim) else "unchecked",
                    )
                )
    return findings


def custody_checks(package: StoryPackage, anchor: str) -> list[CustodyCheck]:
    """Return the holder checks evaluated for every eligible claim/item pair."""

    return [
        CustodyCheck(
            claim_id=finding.claim.id,
            item_id=finding.item_id,
            character_id=finding.character_id,
            status=finding.status,
        )
        for finding in _custody_findings(package, anchor)
    ]


def _custody_flags(package: StoryPackage, root: Path, anchor: str) -> list[Flag]:
    flags = []
    for finding in _custody_findings(package, anchor):
        if finding.status != "unchecked":
            continue
        claim = finding.claim
        item_id = finding.item_id
        claim_text = claim.delivery_text or claim.statement
        evidence = (
            _located(root, f"Claim {claim.id} establishes the exit fact.", claim.id),
            _located(
                root,
                f"Exit transition {finding.transition.id} requires the fact this claim supports.",
                finding.transition.id,
            ),
            _located(
                root,
                f"holder at baseline: {package.world.protagonist_id}; after the hypothetical move: "
                f"{finding.character_id}; engine verdict: eligible",
            ),
            _located(root, f"claim delivery: {_first_sentence(claim_text)}", claim.id),
        )
        flags.append(
            Flag(
                rule="custody",
                anchor=anchor,
                subject=claim.id,
                summary=(
                    f"Claim {claim.id} names {item_id} but the engine lets the protagonist use it "
                    f"while {finding.character_id} holds it."
                ),
                evidence=evidence,
            )
        )
    return flags


def _co_location_flags(package: StoryPackage, root: Path, anchor: str) -> list[Flag]:
    flags = []
    for transition in exit_transitions(package, anchor):
        for claim in _transition_claims(package, transition):
            state = _baseline(package, anchor, transition, claim)
            if not _eligible(state, claim):
                continue
            world = world_for(package, state.facts)
            protagonist = package.world.protagonist_id
            protagonist_area = world.area(protagonist)
            for item_id in _candidate_items(package, state, claim):
                item_area = world.area(item_id)
                if (
                    item_id in claim.reach_entity_ids
                    or protagonist_area is None
                    or item_area is None
                    or not world.apart(protagonist, item_id)
                ):
                    continue
                evidence = (
                    _located(root, f"Claim {claim.id} names the item for the exit.", claim.id),
                    _located(root, f"protagonist in {protagonist_area}", protagonist_area),
                    _located(root, f"{item_id} in {item_area}", item_id),
                    _located(
                        root,
                        "reach_entity_ids: "
                        + (", ".join(claim.reach_entity_ids) if claim.reach_entity_ids else "none"),
                        claim.id,
                    ),
                )
                flags.append(
                    Flag(
                        rule="co_location",
                        anchor=anchor,
                        subject=claim.id,
                        summary=(
                            f"Claim {claim.id} names {item_id} but is usable while the protagonist is away from it."
                        ),
                        evidence=evidence,
                    )
                )
    return flags


def _producer_records(package: StoryPackage, fact_id: str, value: object = True) -> list[_Producer]:
    producers: list[_Producer] = []
    for event in package.pacing.events:
        if any(effect.fact_id == fact_id and _same_value(effect.equals, value) for effect in event.effects):
            producers.append(_Producer("pacing", f"pacing event {event.id} (turn {event.at_turn})", event.id))
    for claim in package.knowledge.knowledge:
        if any(
            effect.op == "assert" and effect.fact_id == fact_id and _same_value(effect.value, value)
            for effect in claim.establishes
        ):
            producers.append(_Producer("claim", f"claim {claim.id} from {_claim_source(claim)}", claim.id))
    for delivery in package.deliveries:
        if any(cost.fact_id == fact_id and _same_value(_operation_value(cost), value) for cost in delivery.costs):
            producers.append(
                _Producer("delivery", f"fallback handoff for {delivery.fact_id} (scene {delivery.scene_id})", None)
            )
    return producers


def _moving_effects(package: StoryPackage, item_id: str) -> list[tuple[str, object]]:
    return [
        (fact_id, effect)
        for fact_id, effects in package.world.fact_effects.items()
        for effect in effects
        if effect.move == item_id
    ]


def _no_strand_flags(package: StoryPackage, root: Path, anchor: str) -> list[Flag]:
    flags = []
    for finding in _custody_findings(package, anchor):
        if finding.status != "unchecked":
            continue
        transition = finding.transition
        claim = finding.claim
        item_id = finding.item_id
        established = {effect.fact_id for effect in claim.establishes if effect.op == "assert"}
        for trigger in transition.triggers:
            if trigger.fact_id not in established or _true(finding.state.facts, trigger.fact_id):
                continue
            producers = [
                producer
                for producer in _producer_records(package, trigger.fact_id, trigger.equals)
                if not (producer.kind == "claim" and producer.record_id == claim.id)
            ]
            other_claims_only = all(
                producer.kind == "claim"
                and any(
                    candidate.id == producer.record_id and item_id in _claim_names(candidate)
                    for candidate in package.knowledge.knowledge
                )
                for producer in producers
            )
            moves = _moving_effects(package, item_id)
            returnable_moves = [
                (fact_id, effect) for fact_id, effect in moves if not _true(finding.state.facts, fact_id)
            ]
            returns_item = any(effect.parent == package.world.protagonist_id for _, effect in returnable_moves)
            if (
                not other_claims_only
                or any(producer.kind in {"pacing", "delivery"} for producer in producers)
                or returns_item
            ):
                continue
            producer_lines = tuple(
                _located(root, f"Other producer: {producer.text}", producer.record_id) for producer in producers
            ) or (_located(root, f"Other producers for {trigger.fact_id}: none"),)
            move_lines = tuple(
                _located(
                    root,
                    (
                        f"Authored effect for {fact_id} moves {item_id} to {effect.parent}; "
                        f"{fact_id} is already true, so it cannot fire again."
                        if effect.parent == package.world.protagonist_id and _true(finding.state.facts, fact_id)
                        else f"Authored effect for {fact_id} moves {item_id} to {effect.parent}."
                    ),
                )
                for fact_id, effect in moves
            ) or (_located(root, f"Authored effects that move {item_id}: none"),)
            evidence = (
                *producer_lines,
                _located(root, f"Exit transition {transition.id} needs {trigger.fact_id}.", transition.id),
                *move_lines,
                _located(
                    root,
                    f"Not stranded if {trigger.fact_id} is already true before the item is lost.",
                ),
            )
            flags.append(
                Flag(
                    rule="no_strand",
                    anchor=anchor,
                    subject=claim.id,
                    summary=(
                        f"If {finding.character_id} holds {item_id}, nothing else can set {trigger.fact_id}, "
                        f"so the exit {transition.id} can never open."
                    ),
                    evidence=evidence,
                )
            )
    return flags


def _run_custody(package: StoryPackage, root: Path, anchor: str, exits: list[Transition]) -> list[Flag]:
    return _custody_flags(package, root, anchor)


def _run_co_location(package: StoryPackage, root: Path, anchor: str, exits: list[Transition]) -> list[Flag]:
    return _co_location_flags(package, root, anchor)


def _run_no_strand(package: StoryPackage, root: Path, anchor: str, exits: list[Transition]) -> list[Flag]:
    return _no_strand_flags(package, root, anchor)


def _run_single_reveal_strand(package: StoryPackage, root: Path, anchor: str, exits: list[Transition]) -> list[Flag]:
    flags = []
    for transition in exits:
        required = {trigger.fact_id for trigger in transition.triggers}
        for route in package.storylet_routes.storylets:
            if route.scene_id != transition.source_scene_id:
                continue
            for realization in route.realizations:
                committed = {operation.fact_id for operation in realization.operations if operation.op == "assert"}
                committed.update(
                    predicate.fact_id for predicate in route.activation_conditions if predicate.equals is True
                )
                missing = required - _reachable_facts(package, committed, {route.id})
                if not missing:
                    continue
                still_sets = required & committed
                evidence = (
                    _located(
                        root,
                        f"Realization {realization.id} of route {route.id} asserts its effects.",
                        realization.id,
                    ),
                    _located(
                        root,
                        f"Exit transition {transition.id} requires its trigger facts.",
                        transition.id,
                    ),
                    "Required facts still set by the realization: " + (", ".join(sorted(still_sets)) or "none") + ".",
                )
                flags.append(
                    Flag(
                        rule="single_reveal_strand",
                        anchor=anchor,
                        subject=f"{route.id}/{realization.id}",
                        summary=(
                            f"Choosing {realization.id} of {route.id} permanently strands "
                            f"{', '.join(sorted(missing))}, which exit {transition.id} needs."
                        ),
                        evidence=evidence,
                    )
                )
    return flags


RULES: dict[str, Callable] = {
    "custody": _run_custody,
    "co_location": _run_co_location,
    "no_strand": _run_no_strand,
    "single_reveal_strand": _run_single_reveal_strand,
}


def run_gap_rules(root: Path, anchor: str, rules: Iterable[str] | None = None) -> list[Flag]:
    """Load a package and report selected deterministic gap flags."""

    package = load_story_package(root)
    exits = exit_transitions(package, anchor)
    selected = tuple(RULES) if rules is None else tuple(rules)
    unknown = next((rule for rule in selected if rule not in RULES), None)
    if unknown is not None:
        raise ValueError(f"unknown rule '{unknown}'")
    flags = [flag for rule in selected for flag in RULES[rule](package, root, anchor, exits)]
    return sorted(flags, key=lambda flag: (flag.rule, flag.subject, flag.summary))


def render_flags(flags: Iterable[Flag], anchor: str) -> str:
    """Render flags as a stable, read-only Markdown report."""

    flags = tuple(flags)
    lines = [
        f"# Gap flags: {anchor}",
        "",
        "Layer 3 story rules. Flags are reported, never block a build, and are not judgments; read the evidence.",
        "",
    ]
    if not flags:
        lines.append("No flags.")
        return "\n".join(lines) + "\n"
    for flag in flags:
        lines.extend([f"### {flag.rule}: {flag.subject}", "", flag.summary, ""])
        lines.extend(f"- {evidence}" for evidence in flag.evidence)
        lines.append("")
    return "\n".join(lines)

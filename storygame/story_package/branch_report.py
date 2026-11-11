"""Render a deterministic, story-agnostic handoff report for an incident."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProgressionValidator, predicate_matches
from storygame.runtime.world_model import apply_scene_placements, apply_world_effects, world_for
from storygame.story_package.dependencies import Consumer, consumers
from storygame.story_package.gap_rules import _reachable_facts, exit_transitions
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import Incident, KnowledgeDefinition, PacingEvent, StoryPackage, Transition


@dataclass(frozen=True)
class _Branch:
    id: str
    claims: tuple[KnowledgeDefinition, ...] = ()
    event: PacingEvent | None = None
    advantages: tuple[str, ...] = ()
    costs: tuple[str, ...] = ()


@dataclass(frozen=True)
class _EntityState:
    parent: str | None
    area: str | None
    holder: str | None


@dataclass(frozen=True)
class _WorldSnapshot:
    entities: dict[str, _EntityState]
    companions: frozenset[str]


def _first_sentence(text: str) -> str:
    match = re.search(r".*?[.!?](?:\s|$)", text.strip(), re.DOTALL)
    return match.group(0).strip() if match else text.strip()


def _source_location(root: Path, record_id: str) -> str | None:
    """Locate only a source line that defines a record with this id."""

    id_value = rf"{re.escape(record_id)}(?=\s*(?:$|[,}}#]))"
    list_id = re.compile(rf"^\s*-\s+id:\s*{id_value}")
    flow_id = re.compile(rf"(?:\{{|,)\s*id:\s*{id_value}")
    mapping_line = re.compile(rf"^\s*{re.escape(record_id)}:\s*(?:#.*)?$")
    for path in sorted(root.rglob("*")):
        if path.suffix not in {".yaml", ".yml", ".md"} or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line_number, line in enumerate(lines, 1):
            if list_id.search(line) or flow_id.search(line) or mapping_line.search(line):
                return f"{path.relative_to(root).as_posix()}:{line_number}"
    return None


def _source_suffix(root: Path, record_id: str) -> str:
    location = _source_location(root, record_id)
    return f" [source: {location}]" if location else ""


def _value(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else str(value)


def _fact_purposes(package: StoryPackage) -> dict[str, str]:
    return {fact.id: fact.purpose for fact in package.knowledge.facts}


def _claim_text(claim: KnowledgeDefinition) -> str:
    return claim.delivery_text or claim.statement


def _branch_claims(
    package: StoryPackage, storylet_id: str, realization_id: str | None
) -> tuple[KnowledgeDefinition, ...]:
    return tuple(
        claim
        for claim in package.knowledge.knowledge
        if claim.source.storylet_id == storylet_id
        and (realization_id is None or claim.source.realization_id == realization_id)
    )


def _branches(package: StoryPackage, incident: Incident) -> tuple[_Branch, ...]:
    branches = [
        _Branch(
            id=outcome.id,
            claims=_branch_claims(package, outcome.storylet_id, outcome.realization_id),
            advantages=outcome.advantages,
            costs=outcome.costs,
        )
        for outcome in incident.outcomes
    ]
    recovery_claims = _branch_claims(package, incident.recovery_storylet_id, None)
    branches.append(_Branch(id=incident.recovery_storylet_id, claims=recovery_claims))
    event = next(event for event in package.pacing.events if event.id == incident.missed_window_event_id)
    branches.append(_Branch(id=event.id, event=event))
    return tuple(branches)


def _branch_predicates(branch: _Branch) -> tuple[object, ...]:
    predicates: list[object] = []
    for claim in branch.claims:
        predicates.extend(effect for effect in claim.establishes if effect.op == "assert")
    if branch.event is not None:
        predicates.extend(branch.event.effects)
    return tuple(predicates)


def _branch_fact_ids(branch: _Branch) -> tuple[str, ...]:
    return tuple(dict.fromkeys(predicate.fact_id for predicate in _branch_predicates(branch)))


def _branch_trace_fact_ids(branch: _Branch) -> tuple[str, ...]:
    branch_fact_ids = _branch_fact_ids(branch)
    set_fact_ids = set(branch_fact_ids)
    declared_effects = (*branch.advantages, *branch.costs)
    return tuple(fact_id for fact_id in dict.fromkeys((*branch_fact_ids, *declared_effects)) if fact_id in set_fact_ids)


def _true_branch_fact_ids(branch: _Branch) -> set[str]:
    return {
        predicate.fact_id
        for predicate in _branch_predicates(branch)
        if _predicate_value(predicate) is None or str(_predicate_value(predicate)).lower() == "true"
    }


def _predicate_value(predicate: object) -> object:
    value = getattr(predicate, "equals", None)
    return getattr(predicate, "value", None) if hasattr(predicate, "value") else value


def _assert_predicate(facts, predicate: object) -> None:
    value = _predicate_value(predicate)
    if value is None:
        value = True
    value = str(value).lower() if isinstance(value, bool) else str(value)
    facts.assert_fact(Fact(predicate=predicate.fact_id, subject="story", value=value))


def _branch_state(package: StoryPackage, incident: Incident, branch: _Branch) -> RuntimeState:
    state = RuntimeState.bootstrap(package)
    if state.current_scene_id != incident.scene_id:
        apply_scene_placements(package, state.facts, incident.scene_id)
        state.current_scene_id = incident.scene_id
        state.phase = next(
            scene.metadata.freytag_phase for scene in package.scenes if scene.metadata.scene_id == incident.scene_id
        )
    for claim in branch.claims:
        for requirement in claim.requires:
            _assert_predicate(state.facts, requirement)
    if branch.event is not None:
        for condition in branch.event.when:
            _assert_predicate(state.facts, condition)
    for predicate in _branch_predicates(branch):
        _assert_predicate(state.facts, predicate)
    apply_world_effects(package, state.facts)
    for claim in branch.claims:
        if claim.source.storylet_id:
            state.active_event_ids.add(claim.source.storylet_id)
    return state


def _true_fact_ids(state: RuntimeState) -> set[str]:
    return {
        fact.predicate
        for fact in state.facts.asserted
        if fact.subject == "story" and str(fact.value if fact.value is not None else fact.object).lower() == "true"
    }


def _next_transitions(package: StoryPackage, incident: Incident) -> list[Transition]:
    if incident.successor_transition_id is not None:
        return exit_transitions(package, incident.id)
    return sorted(
        (transition for transition in package.pacing.transitions if transition.source_scene_id == incident.scene_id),
        key=lambda transition: (transition.priority, transition.id),
    )


def _transition_result(
    package: StoryPackage,
    branch: _Branch,
    state: RuntimeState,
    transitions: tuple[Transition, ...],
) -> tuple[list[Transition], dict[str, tuple[str, ...]], set[str]]:
    validator = ProgressionValidator(package)
    eligible: list[Transition] = []
    unmet: dict[str, tuple[str, ...]] = {}
    true_facts = _true_fact_ids(state)
    fired_storylets = {claim.source.storylet_id for claim in branch.claims if claim.source.storylet_id}
    reachable = _reachable_facts(package, true_facts, fired_storylets)
    for transition in transitions:
        missing = tuple(
            predicate.fact_id for predicate in transition.triggers if not predicate_matches(predicate, state.facts)
        )
        if not missing and validator.transition_dependencies_available(transition, state.facts):
            eligible.append(transition)
        else:
            unmet[transition.id] = missing
    return eligible, unmet, reachable


def _record_text(record_id: str, text: str, root: Path) -> str:
    return f"`{record_id}`: {text}{_source_suffix(root, record_id)}"


def _consumer_text(items: list[Consumer]) -> str:
    return "; ".join(
        f"{item.text} (scene {item.scene_id})" if item.scene_id is not None else item.text for item in items
    )


def _append_claim_delivery(lines: list[str], root: Path, branch: _Branch) -> None:
    if branch.claims:
        for claim in branch.claims:
            lines.append(f"- Claim {_record_text(claim.id, '“' + _first_sentence(_claim_text(claim)) + '”', root)}")
    elif branch.event is not None and branch.event.realizations:
        lines.append(f"- Pacing realization: “{_first_sentence(branch.event.realizations[0].text)}”")
    else:
        lines.append("- No realization claim is authored for this branch.")


def _append_branch_facts(lines: list[str], package: StoryPackage, branch: _Branch) -> None:
    purposes = _fact_purposes(package)
    predicates = _branch_predicates(branch)
    if not predicates:
        lines.append("- Facts set: none")
    else:
        lines.append("- Facts set:")
        for predicate in predicates:
            lines.append(
                f"  - `{predicate.fact_id}` equals `{_value(_predicate_value(predicate))}` — "
                f"{purposes.get(predicate.fact_id, 'No purpose is declared.')}"
            )
    if not branch.advantages:
        lines.append("- Declared advantages: none")
    else:
        lines.append("- Declared advantages:")
        for fact_id in branch.advantages:
            _append_declared_effect(lines, package, branch, fact_id, "advantage")
    if not branch.costs:
        lines.append("- Declared costs: none")
    else:
        lines.append("- Declared costs:")
        for fact_id in branch.costs:
            _append_declared_effect(lines, package, branch, fact_id, "cost")


def _append_declared_effect(lines: list[str], package: StoryPackage, branch: _Branch, fact_id: str, label: str) -> None:
    purpose = _fact_purposes(package).get(fact_id, "No purpose is declared.")
    set_by_branch = fact_id in _branch_fact_ids(branch)
    readers = consumers(package, fact_id)
    if not set_by_branch:
        lines.append(
            f"  - Result: The branch declares {label} `{fact_id}` ('{purpose}') but the realization does not set it."
        )
    elif not readers:
        lines.append(
            f"  - Result: The branch declares {label} `{fact_id}` ('{purpose}') and sets it, "
            f"but nothing later reads it, so the {label} has no effect."
        )
    else:
        lines.append(f"  - `{fact_id}` ('{purpose}') is set by the realization and read by {_consumer_text(readers)}.")


def _entity_ids(package: StoryPackage) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            [package.world.protagonist_id]
            + [entity.id for entity in package.world.npcs]
            + [entity.id for entity in package.world.groups]
            + [entity.id for entity in package.world.items]
        )
    )


def _snapshot(package: StoryPackage, state: RuntimeState) -> _WorldSnapshot:
    world = world_for(package, state.facts)
    entities = {
        entity_id: _EntityState(world.parent(entity_id), world.area(entity_id), world.holder(entity_id))
        for entity_id in _entity_ids(package)
        if world.exists(entity_id)
    }
    return _WorldSnapshot(entities, frozenset(world.companions(package.world.protagonist_id)))


def _place_text(entity: _EntityState | None) -> str:
    if entity is None:
        return "none"
    if entity.parent is None and entity.area is None:
        return "none"
    if entity.parent == entity.area or entity.parent is None:
        return str(entity.area)
    return f"{entity.parent} in {entity.area}"


def _has_place_or_holder(entity: _EntityState | None) -> bool:
    return entity is not None and any(value is not None for value in (entity.parent, entity.area, entity.holder))


def _entity_label(package: StoryPackage, entity_id: str) -> str:
    if entity_id in {item.id for item in package.world.items}:
        return f"Item `{entity_id}`"
    if entity_id == package.world.protagonist_id:
        return "The protagonist"
    return f"Character or group `{entity_id}`"


def _append_world_changes(
    lines: list[str], package: StoryPackage, before: _WorldSnapshot, after: _WorldSnapshot, transition: Transition
) -> None:
    target_scene = next(scene for scene in package.scenes if scene.metadata.scene_id == transition.target_scene_id)
    protagonist = package.world.protagonist_id
    carried: list[str] = []
    appearing: list[str] = []
    before_protagonist = before.entities.get(protagonist)
    after_protagonist = after.entities.get(protagonist)

    def add_entity_change(
        entity_id: str, before_entity: _EntityState | None, after_entity: _EntityState | None
    ) -> None:
        if before_entity == after_entity:
            return
        if not _has_place_or_holder(before_entity) and _has_place_or_holder(after_entity):
            appearing.append(f"- {_entity_label(package, entity_id)}: {_place_text(after_entity)}.")
            return
        if not _has_place_or_holder(before_entity):
            return
        if entity_id == protagonist:
            normal_arrival = after_entity is not None and after_entity.parent == target_scene.metadata.location_id
            label = (
                "The protagonist arrives at the next scene's location"
                if normal_arrival
                else "Result: The protagonist moves"
            )
            carried.append(f"- {label}: {_place_text(before_entity)} -> {_place_text(after_entity)}.")
            return
        is_item = entity_id in {item.id for item in package.world.items}
        if is_item:
            loss = (
                before_entity.holder == protagonist and after_entity is not None and after_entity.holder != protagonist
            )
            prefix = f"Result: Item `{entity_id}` loses custody" if loss else f"Item `{entity_id}` changes place"
            carried.append(
                f"- {prefix}: {_place_text(before_entity)} -> {_place_text(after_entity)}; "
                f"holder {before_entity.holder or 'none'} -> "
                f"{after_entity.holder if after_entity is not None and after_entity.holder else 'none'}."
            )
        else:
            carried.append(
                f"- Character or group `{entity_id}` moves: "
                f"{_place_text(before_entity)} -> {_place_text(after_entity)}."
            )

    add_entity_change(protagonist, before_protagonist, after_protagonist)
    for entity_id in _entity_ids(package):
        if entity_id == protagonist:
            continue
        add_entity_change(entity_id, before.entities.get(entity_id), after.entities.get(entity_id))
    removed = sorted(before.companions - after.companions)
    added = sorted(after.companions - before.companions)
    for companion_id in removed:
        carried.append(f"- Result: Companion `{companion_id}` is cleared.")
    for companion_id in added:
        if not any(f"`{companion_id}`" in line for line in appearing):
            if not _has_place_or_holder(before.entities.get(companion_id)):
                after_entity = after.entities.get(companion_id)
                if _has_place_or_holder(after_entity):
                    appearing.append(f"- {_entity_label(package, companion_id)}: {_place_text(after_entity)}.")
            else:
                carried.append(f"- Companion `{companion_id}` is added.")

    lines.append("- Carried over from the branch:")
    lines.extend(f"  {item}" for item in carried or ["- none"])
    lines.append("- Appears with the next scene:")
    lines.extend(f"  {item}" for item in appearing or ["- none"])
    if (
        before_protagonist == after_protagonist
        and before.entities == after.entities
        and before.companions == after.companions
    ):
        lines.append("- No world placement, custody, character, group, or companion changes occur.")


def _world_change_keys(package: StoryPackage, before: _WorldSnapshot, after: _WorldSnapshot) -> tuple[str, ...]:
    protagonist = package.world.protagonist_id
    keys: list[str] = []
    before_protagonist = before.entities.get(protagonist)
    after_protagonist = after.entities.get(protagonist)
    if _has_place_or_holder(before_protagonist) and before_protagonist != after_protagonist:
        keys.append(f"protagonist move {_place_text(before_protagonist)} -> {_place_text(after_protagonist)}")
    item_ids = {item.id for item in package.world.items}
    for entity_id in _entity_ids(package):
        if entity_id == protagonist:
            continue
        before_entity = before.entities.get(entity_id)
        after_entity = after.entities.get(entity_id)
        if not _has_place_or_holder(before_entity) or before_entity == after_entity:
            continue
        if entity_id in item_ids:
            label = (
                "loss of custody"
                if before_entity.holder == protagonist
                and after_entity is not None
                and after_entity.holder != protagonist
                else "item move"
            )
        else:
            label = "character/group move"
        keys.append(f"{label} {entity_id} {_place_text(before_entity)} -> {_place_text(after_entity)}")
    keys.extend(f"companion cleared {item}" for item in sorted(before.companions - after.companions))
    return tuple(sorted(keys))


def _fact_consumers_for_read_by(
    package: StoryPackage,
    fact_id: str,
    scene_ids: set[str],
    exit_transition_ids: set[str],
) -> list[Consumer]:
    return [
        consumer
        for consumer in consumers(package, fact_id)
        if consumer.scene_id in scene_ids or (consumer.kind == "gate" and consumer.record_id in exit_transition_ids)
    ]


def _fact_consumers_in_later_scene(
    package: StoryPackage,
    fact_id: str,
    incident_scene_id: str,
    next_scene_id: str,
) -> list[Consumer]:
    scene_order = [scene.metadata.scene_id for scene in package.scenes]
    incident_index = scene_order.index(incident_scene_id)
    next_scene_index = scene_order.index(next_scene_id)
    later_scene_ids = set(scene_order[next_scene_index:])
    return [
        consumer
        for consumer in consumers(package, fact_id)
        if consumer.scene_id in later_scene_ids and scene_order.index(consumer.scene_id) > incident_index
    ]


def _append_handoff(
    lines: list[str],
    package: StoryPackage,
    branch: _Branch,
    state: RuntimeState,
    transition: Transition,
    exit_transition_ids: set[str],
) -> tuple[set[str], tuple[str, ...]]:
    before = _snapshot(package, state)
    apply_scene_placements(package, state.facts, transition.target_scene_id)
    after = _snapshot(package, state)
    if lines and lines[-1]:
        lines.append("")
    lines.append(f"- Handoff from `{transition.source_scene_id}` to `{transition.target_scene_id}`:")
    source_scene = next(scene for scene in package.scenes if scene.metadata.scene_id == transition.source_scene_id)
    bridge_text = source_scene.metadata.bridge_text.get(transition.id)
    lines.append(
        f"- Authored bridge text for this handoff: “{bridge_text}”"
        if bridge_text
        else "- Authored bridge text for this handoff: none is authored."
    )
    _append_world_changes(lines, package, before, after, transition)
    target = next(scene for scene in package.scenes if scene.metadata.scene_id == transition.target_scene_id)
    true_facts = _true_fact_ids(state)
    applicable = [variant for variant in target.metadata.entry_variants if set(variant.requires) <= true_facts]
    inapplicable = [variant for variant in target.metadata.entry_variants if variant not in applicable]
    lines.append(f"- Entry variants that apply in scene `{transition.target_scene_id}`:")
    if applicable:
        lines.extend(f"  - requires {variant.requires}: “{variant.text}”" for variant in applicable)
    else:
        lines.append("  - none")
    lines.append(f"- Entry variants that do not apply in scene `{transition.target_scene_id}`:")
    if inapplicable:
        lines.extend(f"  - requires {variant.requires}: “{variant.text}”" for variant in inapplicable)
    else:
        lines.append("  - none")
    scene_order = [scene.metadata.scene_id for scene in package.scenes]
    target_index = scene_order.index(transition.target_scene_id)
    later_scene_ids = set(scene_order[target_index:])

    def readers_for(fact_id: str) -> list[Consumer]:
        return _fact_consumers_for_read_by(package, fact_id, later_scene_ids, exit_transition_ids)

    lines.append("- Branch fact readers after this scene:")
    for fact_id in _branch_fact_ids(branch):
        readers = readers_for(fact_id)
        lines.append(
            f"  - `{fact_id}` — read by: " + (_consumer_text(readers) if readers else "nothing after this scene") + "."
        )
    return true_facts, _world_change_keys(package, before, after)


def _append_way_out(
    lines: list[str], package: StoryPackage, branch: _Branch, state: RuntimeState, transitions: tuple[Transition, ...]
) -> None:
    if not transitions:
        lines.append("- No next-scene transition is authored, so there is no way out to evaluate.")
        return
    eligible, unmet, reachable = _transition_result(package, branch, state, transitions)
    if eligible:
        lines.append(
            "- A next-scene transition can fire after this branch: "
            + ", ".join(f"`{item.id}`" for item in eligible)
            + "."
        )
        return
    lines.append("- Result: no next-scene transition can fire immediately after this branch.")
    for transition in transitions:
        missing = unmet.get(transition.id, ())
        lines.append(
            f"  - Transition `{transition.id}` has unmet trigger facts: "
            + (
                ", ".join(f"`{fact_id}`" for fact_id in missing)
                if missing
                else "none; a required dependency is unavailable"
            )
        )
    missing_facts = {fact_id for values in unmet.values() for fact_id in values}
    future = sorted(fact_id for fact_id in missing_facts if fact_id in reachable)
    if not future:
        lines.append(
            "- Result: dead end. Nothing authored remains that can establish the unmet trigger facts: "
            + (", ".join(f"`{fact_id}`" for fact_id in sorted(missing_facts)) or "none")
            + "."
        )
    else:
        lines.append("- Authored routes can still establish: " + ", ".join(f"`{fact_id}`" for fact_id in future) + ".")


def _append_evidence(
    lines: list[str], package: StoryPackage, branch: _Branch, transition: Transition | None, state: RuntimeState
) -> None:
    lines.append("- A reader decides whether the next scene follows from this branch; the tool does not decide.")
    if branch.claims:
        delivery = "\n".join(_claim_text(claim) for claim in branch.claims)
    elif branch.event is not None:
        delivery = (
            "\n".join(realization.text for realization in branch.event.realizations) or "No pacing realization text."
        )
    else:
        delivery = "No branch delivery text."
    lines.append(f"- Branch delivery text: “{delivery}”")
    if transition is None:
        lines.append("- Bridge text: unavailable because there is no next scene.")
        lines.append("- Next-scene entry text: unavailable because there is no next scene.")
        return
    source_scene = next(scene for scene in package.scenes if scene.metadata.scene_id == transition.source_scene_id)
    target_scene = next(scene for scene in package.scenes if scene.metadata.scene_id == transition.target_scene_id)
    lines.append(f"- Bridge text: “{source_scene.metadata.bridge_text.get(transition.id, '')}”")
    true_facts = _true_fact_ids(state)
    entry = [target_scene.metadata.entry_text]
    entry.extend(
        variant.text for variant in target_scene.metadata.entry_variants if set(variant.requires) <= true_facts
    )
    lines.append(f"- Next-scene applicable entry text: “{'\n'.join(entry)}”")


def _append_comparison(
    lines: list[str],
    package: StoryPackage,
    branches: tuple[_Branch, ...],
    incident: Incident,
    branch_changes: dict[str, tuple[str, ...]],
) -> None:
    lines.extend(["## Comparison", ""])
    branch_facts = {branch.id: set(_branch_trace_fact_ids(branch)) for branch in branches}
    all_facts = set().union(*branch_facts.values()) if branch_facts else set()
    exit_transitions = tuple(_next_transitions(package, incident))
    later_ids = {
        scene.metadata.scene_id
        for index, scene in enumerate(package.scenes)
        if index
        > next(index for index, item in enumerate(package.scenes) if item.metadata.scene_id == incident.scene_id)
    }
    asymmetric = [
        fact_id for fact_id in sorted(all_facts) if len({fact_id in values for values in branch_facts.values()}) > 1
    ]
    if asymmetric:
        lines.append("Facts set by some branches and not others:")
        for fact_id in asymmetric:
            set_by = [branch_id for branch_id, facts in branch_facts.items() if fact_id in facts]
            readers = _fact_consumers_for_read_by(
                package,
                fact_id,
                later_ids,
                {transition.id for transition in exit_transitions},
            )
            lines.append(
                f"- `{fact_id}` is set by {', '.join(f'`{branch_id}`' for branch_id in set_by)}; "
                f"read by: " + (_consumer_text(readers) if readers else "nothing after this scene") + "."
            )
    else:
        lines.append("No fact is set by some branches and omitted by others.")
    trace_less = [
        branch_id
        for branch_id, facts in branch_facts.items()
        if not any(
            _fact_consumers_in_later_scene(package, fact_id, incident.scene_id, exit_transitions[0].target_scene_id)
            if exit_transitions
            else []
            for fact_id in facts
        )
    ]
    lines.append(
        "Branches that leave no trace in any later scene: "
        + (", ".join(f"`{branch_id}`" for branch_id in trace_less) if trace_less else "none")
        + "."
    )
    all_changes = set().union(*(set(changes) for changes in branch_changes.values()))
    asymmetric_changes = [
        change
        for change in sorted(all_changes)
        if 0 < sum(change in changes for changes in branch_changes.values()) < len(branches)
    ]
    lines.append("")
    if asymmetric_changes:
        lines.append("World moves or custody changes that differ across branches:")
        for change in asymmetric_changes:
            occurs = [branch_id for branch_id, changes in branch_changes.items() if change in changes]
            lines.append(f"- `{change}` occurs in: {', '.join(f'`{branch_id}`' for branch_id in occurs)}.")
    else:
        lines.append("No world move or custody change differs across branches.")


def render_branch_report(root: Path, incident_id: str) -> str:
    """Render the branch behavior and next-scene handoff for one incident."""

    package = load_story_package(root)
    matches = [incident for incident in package.incidents if incident.id == incident_id]
    if not matches:
        pacing_ids = {event.id for event in package.pacing.events}
        if incident_id in pacing_ids:
            raise ValueError(f"anchor '{incident_id}' is a pacing event, not an incident")
        raise ValueError(f"unknown incident '{incident_id}'")
    incident = matches[0]
    branches = _branches(package, incident)
    transitions = tuple(_next_transitions(package, incident))
    target = transitions[0].target_scene_id if transitions else None
    lines = [
        f"# Branch report: {incident.id}{_source_suffix(root, incident.id)}",
        "",
        "Generated from the current story files. Read-only; edit the sources, not this page.",
        f"The incident occurs in scene `{incident.scene_id}`.",
        "",
        "## Next scene",
        "",
        f"- Target scene: `{target}`."
        if target
        else "- No next scene is authored for this incident; handoff analysis is skipped.",
    ]
    branch_changes: dict[str, tuple[str, ...]] = {}
    for branch in branches:
        state = _branch_state(package, incident, branch)
        lines.extend(["", f"## Branch `{branch.id}`", "", "### What it does", ""])
        _append_claim_delivery(lines, root, branch)
        _append_branch_facts(lines, package, branch)
        lines.extend(["", "### Way out", ""])
        _append_way_out(lines, package, branch, state, transitions)
        lines.extend(["", "### Handoff analysis", ""])
        if transitions:
            eligible, _, _ = _transition_result(package, branch, state, transitions)
            transition = eligible[0] if eligible else transitions[0]
            _, branch_changes[branch.id] = _append_handoff(
                lines, package, branch, state, transition, {item.id for item in transitions}
            )
        else:
            lines.append("- Skipped because there is no next scene.")
        lines.extend(["", "### Evidence for judgment", ""])
        _append_evidence(lines, package, branch, transitions[0] if transitions else None, state)
    _append_comparison(lines, package, branches, incident, branch_changes)
    return "\n".join(lines) + "\n"

"""Render a read-only, story-agnostic situation trace."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from storygame.story_package.dependencies import consumers, producers
from storygame.story_package.gap_rules import custody_checks
from storygame.story_package.loader import load_story_package
from storygame.story_package.models import (
    FactPredicate,
    Incident,
    KnowledgeDefinition,
    PacingEvent,
    StoryPackage,
    Transition,
)


def _value_text(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value).lower()


def _condition_text(conditions: Iterable[FactPredicate]) -> str:
    return (
        " and ".join(f"{condition.fact_id} is {_value_text(condition.equals)}" for condition in conditions) or "always"
    )


def _fact_purposes(package: StoryPackage) -> dict[str, str]:
    return {fact.id: fact.purpose for fact in package.knowledge.facts}


def _claim_source(claim: KnowledgeDefinition) -> str:
    source = claim.source
    return source.realization_id or source.storylet_id or source.kind


def _append_fact_consumers(
    lines: list[str], package: StoryPackage, fact_id: str, *, exclude: str | None = None
) -> None:
    lines.append(f"`{fact_id}` is read by:")
    fact_consumers = consumers(package, fact_id, exclude_transition_id=exclude)
    if fact_consumers:
        lines.extend(f"- {consumer.text} [{consumer.kind}]" for consumer in fact_consumers)
    else:
        lines.append("- nothing")


def _append_scene_frame(lines: list[str], package: StoryPackage, scene_id: str) -> None:
    frame = next(frame for frame in package.knowledge.scene_frames if frame.scene_id == scene_id)
    if frame.situation:
        lines.append(f"- Situation in scene {scene_id}: {frame.situation}")
    lines.append(f"- Pressure in scene {scene_id}: {frame.pressure}")


def _append_transition(lines: list[str], package: StoryPackage, transition: Transition) -> None:
    purposes = _fact_purposes(package)
    lines.extend(
        [
            f"Transition `{transition.id}` needs all of:",
            "",
            "| Needs | Meaning | Produced by |",
            "| --- | --- | --- |",
        ]
    )
    for trigger in transition.triggers:
        produced_by = "; ".join(item.text for item in producers(package, trigger.fact_id, trigger.equals))
        lines.append(f"| `{trigger.fact_id}` | {purposes.get(trigger.fact_id, '?')} | {produced_by} |")
    lines.append("")
    for dependency in transition.required_dependencies:
        lines.append(f"It also lists `{dependency}` as a required dependency.")


def _append_claim_checks(
    lines: list[str], package: StoryPackage, anchor: str, transitions: Iterable[Transition]
) -> None:
    trigger_values = {
        (trigger.fact_id, trigger.equals) for transition in transitions for trigger in transition.triggers
    }
    claims = [
        claim
        for claim in package.knowledge.knowledge
        if any((effect.fact_id, effect.value) in trigger_values for effect in claim.establishes)
    ]
    if not claims:
        return
    if lines and lines[-1] != "":
        lines.append("")
    lines.extend(
        [
            "### What the engine checks to deliver these",
            "",
            "| Claim id | What it requires | What thing it requires her to be near |",
            "| --- | --- | --- |",
        ]
    )
    for claim in claims:
        requirements = _condition_text(claim.requires)
        near = ", ".join(f"`{entity_id}`" for entity_id in claim.reach_entity_ids) or "names no thing"
        lines.append(f"| `{claim.id}` | {requirements} | {near} |")
    lines.append("")
    checks = custody_checks(package, anchor)
    if checks:
        for check in checks:
            if check.status == "checked":
                lines.append(
                    f"Claim `{check.claim_id}`: the engine checks whether `{check.character_id}` holds "
                    f"`{check.item_id}` (tested by moving it)."
                )
            elif check.status == "unchecked":
                lines.append(
                    f"Claim `{check.claim_id}`: the engine does not check whether `{check.character_id}` holds "
                    f"`{check.item_id}` (tested by moving it)."
                )
            else:
                lines.append(
                    f"Claim `{check.claim_id}` names `{check.item_id}`; whether the engine checks who holds it "
                    "was not tested here, because no other character is with the protagonist in this anchor's "
                    "starting state."
                )
    else:
        lines.append("No held item is named by these claims.")


def _transitions_for_scene(package: StoryPackage, scene_id: str) -> list[Transition]:
    return sorted(
        (transition for transition in package.pacing.transitions if transition.source_scene_id == scene_id),
        key=lambda transition: (transition.priority, transition.id),
    )


def _route_realization_text(package: StoryPackage, storylet_id: str, realization_id: str) -> str:
    storylet = next(storylet for storylet in package.storylet_routes.storylets if storylet.id == storylet_id)
    realization = next(realization for realization in storylet.realizations if realization.id == realization_id)
    return realization.dramatic_intent


def _append_incident_outcome(lines: list[str], package: StoryPackage, outcome) -> None:
    advantages = ", ".join(f"`{fact_id}`" for fact_id in outcome.advantages)
    costs = ", ".join(f"`{fact_id}`" for fact_id in outcome.costs) or "none"
    lines.extend(
        [
            f"### Outcome `{outcome.id}`",
            f"- Storylet: `{outcome.storylet_id}`",
            f"- Realization `{outcome.realization_id}`: "
            f"{_route_realization_text(package, outcome.storylet_id, outcome.realization_id)}",
            f"- Advantages: {advantages}",
            f"- Costs: {costs}",
        ]
    )


def _render_pacing_event(lines: list[str], package: StoryPackage, event: PacingEvent) -> list[Transition]:
    purposes = _fact_purposes(package)
    lines.extend(
        [
            "## 1. The situation",
            "",
            f"- Pacing event `{event.id}` fires at turn {event.at_turn} when: {_condition_text(event.when)}.",
        ]
    )
    _append_scene_frame(lines, package, event.scene_id)
    for condition in event.when:
        lines.append(
            f"  - `{condition.fact_id}` ({purposes.get(condition.fact_id, '?')}) comes from: "
            + "; ".join(item.text for item in producers(package, condition.fact_id, condition.equals))
        )
    lines.append(f"- It sets: {_condition_text(event.effects)}.")
    if event.realizations:
        lines.append(f"- Line: “{event.realizations[0].text}”")
    else:
        lines.append("- Line: (no authored realization)")
    lines.extend(["", "## 2. Where the situation leads", ""])
    dead_end = True
    for effect in event.effects:
        fact_consumers = consumers(package, effect.fact_id)
        lines.append(f"`{effect.fact_id}` is read by:")
        if fact_consumers:
            for consumer in fact_consumers:
                lines.append(f"- {consumer.text} [{consumer.kind}]")
                dead_end &= consumer.kind == "wording"
        else:
            lines.append("- nothing")
    lines.extend(
        [
            "",
            "Nothing reads it except a line of wording." if dead_end else "It feeds more than wording.",
            "",
            "## 3. What the next scene needs",
            "",
        ]
    )
    transitions = _transitions_for_scene(package, event.scene_id)
    for index, transition in enumerate(transitions):
        if len(transitions) > 1:
            lines.extend([f"### Transition `{transition.id}`", ""])
        _append_transition(lines, package, transition)
        if index != len(transitions) - 1:
            lines.append("")
    if not transitions:
        lines.append("No successor transition is declared.")
    return transitions


def _render_incident(lines: list[str], package: StoryPackage, incident: Incident) -> list[Transition]:
    lines.extend(
        [
            "## 1. The situation",
            "",
            f"- Incident `{incident.id}` occurs in scene `{incident.scene_id}`.",
        ]
    )
    _append_scene_frame(lines, package, incident.scene_id)
    for outcome in incident.outcomes:
        lines.append("")
        _append_incident_outcome(lines, package, outcome)
    lines.extend(
        [
            "",
            f"- Recovery storylet: `{incident.recovery_storylet_id}`",
            f"- Missed-window event: `{incident.missed_window_event_id}`",
            "- Observation claims: "
            + (", ".join(f"`{claim_id}`" for claim_id in incident.observation_knowledge_ids) or "none"),
            "",
            "## 2. Where the situation leads",
            "",
        ]
    )
    facts = []
    for outcome in incident.outcomes:
        facts.extend((*outcome.advantages, *outcome.costs))
    for fact_id in dict.fromkeys(facts):
        _append_fact_consumers(lines, package, fact_id)
    lines.extend(["", "## 3. What the next scene needs", ""])
    transitions = []
    if incident.successor_transition_id is not None:
        transition = next(
            transition for transition in package.pacing.transitions if transition.id == incident.successor_transition_id
        )
        transitions.append(transition)
        _append_transition(lines, package, transition)
    else:
        lines.append("No successor transition is declared.")
    return transitions


def _render_transition(lines: list[str], package: StoryPackage, transition: Transition) -> list[Transition]:
    lines.extend(
        [
            "## 1. The situation",
            "",
            f"- Transition `{transition.id}` goes from scene `{transition.source_scene_id}` to scene "
            f"`{transition.target_scene_id}` at priority {transition.priority}.",
        ]
    )
    _append_scene_frame(lines, package, transition.source_scene_id)
    lines.extend(["", "## 2. Where the situation leads", ""])
    for trigger in transition.triggers:
        _append_fact_consumers(lines, package, trigger.fact_id, exclude=transition.id)
    lines.extend(["", "## 3. What the next scene needs", ""])
    _append_transition(lines, package, transition)
    return [transition]


def render_situation_trace(root: Path, anchor: str) -> str:
    """Render the three-section trace for one package anchor."""
    package = load_story_package(root)
    matches: list[tuple[str, object]] = []
    matches.extend(("pacing event", event) for event in package.pacing.events if event.id == anchor)
    matches.extend(("incident", incident) for incident in package.incidents if incident.id == anchor)
    matches.extend(("transition", transition) for transition in package.pacing.transitions if transition.id == anchor)
    if not matches:
        raise ValueError(f"unknown anchor '{anchor}'")
    if len(matches) > 1:
        raise ValueError(f"ambiguous anchor '{anchor}': {', '.join(kind for kind, _ in matches)}")

    lines = [
        f"# Situation trace: {anchor}",
        "",
        "Generated from the current story files. Read-only; edit the sources, not this page.",
        "Each section traces the situation, where it leads, and what the next scene needs.",
        "",
    ]
    kind, item = matches[0]
    if kind == "pacing event":
        transitions = _render_pacing_event(lines, package, item)
    elif kind == "incident":
        transitions = _render_incident(lines, package, item)
    else:
        transitions = _render_transition(lines, package, item)
    _append_claim_checks(lines, package, anchor, transitions)
    return "\n".join(lines) + "\n"

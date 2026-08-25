"""Typed mutable runtime authority for the V2 engine."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from storygame.authoring.contracts import Beat, CompiledStory
from storygame.runtime.facts import Fact, FactStore
from storygame.runtime.narrative import RuntimeNarrativePackage, RuntimeNarrativeProjection, seed_storylet_facts


@dataclass
class WorldState:
    location: str
    flags: set[str] = field(default_factory=set)
    attributes: dict[str, Any] = field(default_factory=dict)
    items: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass
class BeatRuntime:
    beat_id: str
    completed_tags: set[str] = field(default_factory=set)
    turns_active: int = 0
    stagnant_turns: int = 0


@dataclass(frozen=True)
class RuntimeEvent:
    turn_index: int
    player_input: str
    narration: str
    operations: tuple[dict[str, Any], ...]
    beat_updates: tuple[dict[str, Any], ...]
    prompt_version: str
    prompt_token_estimate: int


@dataclass
class RuntimeState:
    compiled_story: CompiledStory
    world: WorldState
    beat_runtime: dict[str, BeatRuntime]
    narrative_package: RuntimeNarrativePackage | None = None
    turn_index: int = 0
    recent_events: list[RuntimeEvent] = field(default_factory=list)
    story_summary: str = ""
    facts: FactStore = field(default_factory=FactStore)

    @property
    def active_beats(self) -> tuple[Beat, ...]:
        completed = {beat_id for beat_id, runtime in self.beat_runtime.items() if runtime.completed_tags}
        return tuple(
            beat
            for beat in self.compiled_story.beats
            if beat.id not in completed and all(prerequisite in completed for prerequisite in beat.prerequisites)
        )


def bootstrap_runtime_state(compiled_story: CompiledStory | RuntimeNarrativeProjection) -> RuntimeState:
    """Realize a reviewed immutable story into the only mutable V2 state object."""

    narrative_package = None
    if isinstance(compiled_story, RuntimeNarrativeProjection):
        narrative_package = compiled_story.narrative_package
        compiled_story = compiled_story.compiled_story
    if not isinstance(compiled_story, CompiledStory):
        raise TypeError("runtime bootstrap requires a reviewed CompiledStory fixture")
    initial = compiled_story.initial_world_state
    location = initial.get("location")
    if not isinstance(location, str) or not location:
        location = "opening"
    attributes = {key: value for key, value in initial.items() if key not in {"location", "flags", "items"}}
    if compiled_story.opening is not None:
        attributes["opening_facts"] = {
            "location": location,
            "contacts": [contact.model_dump(mode="json") for contact in compiled_story.opening.contacts],
            "public_briefing": list(compiled_story.opening.public_briefing),
            "scene_purpose": compiled_story.opening.scene_purpose,
        }
    flags = {value for value in initial.get("flags", []) if isinstance(value, str)}
    raw_items = initial.get("items", {})
    items = {key: dict(value) for key, value in raw_items.items() if isinstance(key, str) and isinstance(value, dict)}
    for definition in compiled_story.item_definitions:
        item = items.setdefault(definition.id, {})
        item.setdefault("name", definition.name)
        item.setdefault("kind", definition.kind)
        item.setdefault("description", definition.description)
        item.setdefault("affordances", list(definition.affordances))
        item.setdefault("portable", definition.portable)
        item.setdefault("holder", definition.initial_holder)
        if definition.readable is not None:
            item.setdefault("readable", definition.readable.model_dump(mode="json"))
    for document in compiled_story.readable_documents:
        item = items.get(document.item_id)
        if item is not None:
            item.setdefault("readable", document.model_dump(mode="json"))
    facts = _bootstrap_facts(compiled_story, location, attributes, items)
    for flag in flags:
        facts.assert_fact(Fact(predicate="flag", subject="world", object=flag))
    if narrative_package is not None:
        _bootstrap_narrative_facts(narrative_package, facts)
    return RuntimeState(
        compiled_story=compiled_story,
        world=WorldState(location=location, flags=flags, attributes=attributes, items=items),
        beat_runtime={beat.id: BeatRuntime(beat_id=beat.id) for beat in compiled_story.beats},
        narrative_package=narrative_package,
        facts=facts,
    )


def _bootstrap_facts(
    compiled_story: CompiledStory,
    location: str,
    attributes: dict[str, Any],
    items: dict[str, dict[str, Any]],
) -> FactStore:
    facts = FactStore()
    facts.assert_fact(Fact(predicate="at", subject="player", object=location))
    if compiled_story.scene_purpose:
        facts.assert_fact(Fact(predicate="scene_objective", subject="scene", value=compiled_story.scene_purpose))
    if compiled_story.dramatic_question:
        facts.assert_fact(Fact(predicate="dramatic_question", subject="scene", value=compiled_story.dramatic_question))
    facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value=str(compiled_story.initial_pressure)))
    for goal in compiled_story.goals:
        facts.assert_fact(Fact(predicate="goal", subject="player", object=goal.id, value=goal.summary))
    for task in compiled_story.tasks:
        facts.assert_fact(Fact(predicate="task", subject="player", object=task.id, value=task.initial_status))
    for clue in compiled_story.clues:
        facts.assert_fact(Fact(predicate="clue", subject=clue.id, value=clue.summary))
    for relationship in compiled_story.relationships:
        facts.assert_fact(
            Fact(
                predicate="relationship",
                subject=relationship.subject_id,
                object=relationship.target_id,
                value=relationship.relationship,
            )
        )
    for raw_fact in attributes.get("facts", ()):
        try:
            facts.assert_fact(Fact.model_validate(raw_fact))
        except (TypeError, ValueError) as exc:
            raise TypeError(f"compiled story contains an invalid initial fact: {exc}") from exc
    active_goal = attributes.get("active_goal")
    if isinstance(active_goal, str):
        facts.assert_fact(Fact(predicate="active_goal", subject="player", object=active_goal))
    scene_objective = attributes.get("scene_objective")
    if isinstance(scene_objective, str):
        facts.assert_fact(Fact(predicate="scene_objective", subject="scene", value=scene_objective))
    protagonist = attributes.get("protagonist")
    if isinstance(protagonist, dict):
        protagonist_id = protagonist.get("id")
        if isinstance(protagonist_id, str):
            facts.assert_fact(Fact(predicate="identity", subject="player", object=protagonist_id))
        role = protagonist.get("role")
        if isinstance(role, str):
            facts.assert_fact(Fact(predicate="role", subject="player", object=role))
    opening = compiled_story.opening
    if opening is not None:
        for contact in opening.contacts:
            if contact.location == location:
                facts.assert_fact(Fact(predicate="at", subject=contact.id, object=contact.location))
                facts.assert_fact(Fact(predicate="present", subject=contact.id, object=location))
                facts.assert_fact(Fact(predicate="role", subject=contact.id, object=contact.role))
                facts.assert_fact(
                    Fact(predicate="relationship", subject="player", object=f"{contact.id}:{contact.relationship}")
                )
                for knowledge in contact.public_knowledge:
                    facts.assert_fact(Fact(predicate="knows", subject=contact.id, object=knowledge))
                    facts.assert_fact(Fact(predicate="knows", subject="player", object=knowledge))
    opening_contact = attributes.get("opening_contact")
    if opening is not None and opening.contacts or not isinstance(opening_contact, dict):
        opening_contact = None
    if isinstance(opening_contact, dict):
        contact_id = opening_contact.get("id")
        if isinstance(contact_id, str):
            facts.assert_fact(Fact(predicate="at", subject=contact_id, object=location))
            facts.assert_fact(Fact(predicate="present", subject=contact_id, object=location))
            role = opening_contact.get("role")
            if isinstance(role, str):
                facts.assert_fact(Fact(predicate="role", subject=contact_id, object=role))
            relationship = opening_contact.get("relationship")
            if isinstance(relationship, str):
                facts.assert_fact(
                    Fact(predicate="relationship", subject="player", object=f"{contact_id}:{relationship}")
                )
            facts.assert_fact(Fact(predicate="npc_available", subject=contact_id, object=location))
    for item_id, item in items.items():
        holder = item.get("holder")
        if isinstance(holder, str) and holder:
            facts.assert_fact(Fact(predicate="custody", subject=item_id, object=holder))
            if holder == "player":
                facts.assert_fact(Fact(predicate="possession", subject="player", object=item_id))
        for affordance in item.get("affordances", ()):
            if isinstance(affordance, str):
                facts.assert_fact(Fact(predicate="item_affordance", subject=item_id, object=affordance))
        readable = item.get("readable")
        if isinstance(readable, dict):
            for key in readable.get("knowledge", ()):
                if isinstance(key, str):
                    facts.assert_fact(Fact(predicate="unknown", subject="player", object=key))
            disclosures = readable.get("npc_disclosures", {})
            if isinstance(disclosures, dict):
                for speaker, keys in disclosures.items():
                    if isinstance(speaker, str) and isinstance(keys, list | tuple):
                        for key in keys:
                            if isinstance(key, str):
                                facts.assert_fact(Fact(predicate="knows", subject=speaker, object=key))
    return facts


def _bootstrap_narrative_facts(package: RuntimeNarrativePackage, facts: FactStore) -> None:
    """Project reviewed declarations into canonical facts without mutating the package."""

    for truth_id in package.opening_truth_ids:
        if truth_id not in package.protected_truth_ids:
            facts.assert_fact(Fact(predicate="knows", subject="player", object=truth_id))
    for knowledge in package.party_knowledge:
        for truth_id in knowledge.truth_ids:
            facts.assert_fact(Fact(predicate="knows", subject=knowledge.participant_id, object=truth_id))
    for participant in package.participants:
        if participant.initial_location_id is not None:
            facts.assert_fact(Fact(predicate="at", subject=participant.id, object=participant.initial_location_id))
        if participant.public_name is not None:
            facts.assert_fact(Fact(predicate="public_name", subject=participant.id, value=participant.public_name))
        if participant.public_role is not None:
            facts.assert_fact(Fact(predicate="public_role", subject=participant.id, value=participant.public_role))
        if participant.public_description is not None:
            facts.assert_fact(
                Fact(predicate="public_description", subject=participant.id, value=participant.public_description)
            )
        if participant.initial_availability is not None:
            facts.assert_fact(
                Fact(predicate="npc_availability", subject=participant.id, value=participant.initial_availability)
            )
            if participant.initial_availability == "present" and participant.initial_location_id is not None:
                facts.assert_fact(
                    Fact(predicate="present", subject=participant.id, object=participant.initial_location_id)
                )
                facts.assert_fact(
                    Fact(predicate="npc_available", subject=participant.id, object=participant.initial_location_id)
                )
    for subject in package.scene_subjects:
        facts.assert_fact(Fact(predicate="at", subject=subject.id, object=subject.location_id))
        facts.assert_fact(Fact(predicate="scene_subject", subject=subject.id, value=subject.kind))
        facts.assert_fact(Fact(predicate="inspectable", subject=subject.id, value=str(subject.inspectable).lower()))
        facts.assert_fact(Fact(predicate="public_description", subject=subject.id, value=subject.public_description))
        facts.assert_fact(Fact(predicate="subject_discovered", subject=subject.id, value="false"))
    for realization in package.evidence_realizations:
        facts.assert_fact(Fact(predicate="at", subject=realization.id, object=realization.location_id))
        facts.assert_fact(Fact(predicate="evidence_kind", subject=realization.id, value=realization.kind))
        facts.assert_fact(
            Fact(predicate="public_description", subject=realization.id, value=realization.public_description)
        )
        facts.assert_fact(Fact(predicate="evidence_discovered", subject=realization.id, value="false"))
        if realization.custody_holder_id is not None:
            facts.assert_fact(Fact(predicate="custody", subject=realization.id, object=realization.custody_holder_id))
        if realization.scene_subject_id is not None:
            facts.assert_fact(
                Fact(predicate="evidence_subject", subject=realization.id, object=realization.scene_subject_id)
            )
    for encounter in package.group_encounters:
        facts.assert_fact(Fact(predicate="group_at", subject=encounter.id, object=encounter.location_id))
        for participant_id in encounter.participant_ids:
            facts.assert_fact(Fact(predicate="group_member", subject=encounter.id, object=participant_id))
    seed_storylet_facts(package, facts)


def runtime_state_bytes(state: RuntimeState) -> bytes:
    """Stable snapshot used for atomicity checks and later persistence integrity."""
    payload = {
        "compiled_story": state.compiled_story.model_dump(mode="json"),
        "world": {
            "location": state.world.location,
            "flags": sorted(state.world.flags),
            "attributes": state.world.attributes,
            "items": state.world.items,
        },
        "beat_runtime": {
            beat_id: {
                "completed_tags": sorted(runtime.completed_tags),
                "turns_active": runtime.turns_active,
                "stagnant_turns": runtime.stagnant_turns,
            }
            for beat_id, runtime in state.beat_runtime.items()
        },
        "turn_index": state.turn_index,
        "recent_events": [event.__dict__ for event in state.recent_events],
        "story_summary": state.story_summary,
        "facts": state.facts.as_json(),
    }
    return json.dumps(payload, sort_keys=True).encode()

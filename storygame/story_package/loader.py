"""Strict loaders and cross-reference validation for Markdown story packages."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from storygame.story_package.models import (
    FactDelivery,
    KnowledgeCatalog,
    KnowledgeIndexes,
    PacingSource,
    RouteOperation,
    Scene,
    SceneBeat,
    SceneMetadata,
    Storylet,
    StoryletRoutesSource,
    StoryPackage,
    WorldSource,
)


class StoryPackageError(ValueError):
    """A source package is malformed or internally inconsistent."""


_SCENE = re.compile(r"^## Scene ([1-9][A-Z]) .*$", re.MULTILINE)
_SCENE_BEAT = re.compile(r"^### (?P<heading>Scene (?P<id>[1-9][A-Z]\.[1-9])\s+[—-]\s+(?P<title>.+))$", re.MULTILINE)
_STORYLET = re.compile(r"^### (SL-([1-9][A-Z])-[A-Z]) — (.+)$", re.MULTILINE)
_SECTION = re.compile(r"^\*\*([^*]+)\*\*\s*(.*?)(?=^\*\*|^---\s*$|\Z)", re.MULTILINE | re.DOTALL)
_REQUIRED_STORYLET_SECTIONS = {
    "Source beats:",
    "Allowed scene:",
    "Available when",
    "Participants / items",
    "Dramatic purpose",
    "Possible realizations",
    "Effects",
    "Completion",
    "Abort",
    "Protected boundary",
    "Pacing window",
    "Pacing impact",
}


def _yaml(path: Path) -> dict[str, Any]:
    try:
        value = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise StoryPackageError(f"cannot read YAML '{path}': {exc}") from exc
    if not isinstance(value, dict):
        raise StoryPackageError(f"YAML '{path}' must be a mapping")
    return value


def _parse_scenes(text: str) -> tuple[Scene, ...]:
    matches = list(_SCENE.finditer(text))
    if not matches:
        raise StoryPackageError("plot.md contains no playable scene headings")
    scenes = []
    for index, match in enumerate(matches):
        body = text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)].lstrip()
        frontmatter = re.match(r"---\n(.*?)\n---\n", body, re.DOTALL)
        if not frontmatter:
            raise StoryPackageError(f"scene {match.group(1)} lacks YAML frontmatter")
        try:
            metadata = SceneMetadata.model_validate(yaml.safe_load(frontmatter.group(1)))
        except (ValidationError, yaml.YAMLError) as exc:
            raise StoryPackageError(f"invalid frontmatter for scene {match.group(1)}: {exc}") from exc
        if metadata.scene_id != match.group(1):
            raise StoryPackageError(f"heading and frontmatter disagree for scene {match.group(1)}")
        if set(metadata.bridge_text) != set(metadata.transition_ids):
            raise StoryPackageError(f"scene {match.group(1)} bridge_text keys must match transition_ids exactly")
        prose = body[frontmatter.end() :].strip()
        scenes.append(
            Scene(
                metadata=metadata,
                prose=prose,
                beats=_parse_scene_beats(metadata.scene_id, prose),
                opening_beat=_parse_opening_beat(metadata.scene_id, prose),
            )
        )
    return tuple(scenes)


def _beat_anchor(heading: str) -> str:
    """Convert an authored beat heading to the exact anchor used by source links."""

    filtered = (character for character in heading.lower() if character.isalnum() or character in " -")
    return "".join("-" if character == " " else character for character in filtered)


def _parse_scene_beats(scene_id: str, prose: str) -> dict[str, SceneBeat]:
    matches = [match for match in _SCENE_BEAT.finditer(prose) if match.group("id").startswith(f"{scene_id}.")]
    beats: dict[str, SceneBeat] = {}
    for match in matches:
        end = next((other.start() for other in matches if other.start() > match.start()), len(prose))
        beat_prose = prose[match.end() : end].strip()
        beat_id = match.group("id")
        if not beat_prose:
            raise StoryPackageError(f"scene {scene_id} beat {beat_id} has no prose")
        anchor = _beat_anchor(match.group("heading"))
        if anchor in beats:
            raise StoryPackageError(f"scene {scene_id} has duplicate beat anchor '{anchor}'")
        beats[anchor] = SceneBeat(
            id=beat_id,
            anchor=anchor,
            title=match.group("title").strip(),
            prose=beat_prose,
        )
    if not beats:
        raise StoryPackageError(f"scene {scene_id} contains no beat headings")
    return beats


def _parse_opening_beat(scene_id: str, prose: str) -> SceneBeat:
    """Isolate the scene's first authored beat so an opening embellishes canon instead of inventing it."""

    matches = list(_SCENE_BEAT.finditer(prose))
    first = next((match for match in matches if match.group("id") == f"{scene_id}.1"), None)
    if first is None:
        raise StoryPackageError(f"scene {scene_id} lacks an opening beat heading '### Scene {scene_id}.1'")
    end = next((match.start() for match in matches if match.start() > first.start()), len(prose))
    body = prose[first.end() : end].strip()
    if not body:
        raise StoryPackageError(f"scene {scene_id} opening beat has no prose")
    return SceneBeat(
        id=first.group("id"),
        anchor=_beat_anchor(first.group("heading")),
        title=first.group("title").strip(),
        prose=body,
    )


def _turn(value: str) -> int:
    match = re.fullmatch(r"turn\s+(\d+)", value.strip(), re.IGNORECASE)
    if not match:
        raise StoryPackageError(f"invalid turn offset '{value}' (use 'turn N')")
    return int(match.group(1))


def _parse_storylets(text: str, plot_beat_anchors: set[str], plot_scene_ids: set[str]) -> tuple[Storylet, ...]:
    matches = list(_STORYLET.finditer(text))
    if not matches:
        raise StoryPackageError("storylets.md contains no SL-* headings")
    storylets = []
    for index, match in enumerate(matches):
        block = text[match.end() : matches[index + 1].start() if index + 1 < len(matches) else len(text)]
        sections = {name.strip(): value.strip() for name, value in _SECTION.findall(block)}
        missing = _REQUIRED_STORYLET_SECTIONS - sections.keys()
        if missing:
            raise StoryPackageError(f"storylet {match.group(1)} lacks sections: {', '.join(sorted(missing))}")
        allowed = re.search(r"`([1-9][A-Z])`", sections["Allowed scene:"])
        if not allowed or allowed.group(1) != match.group(2):
            raise StoryPackageError(f"storylet {match.group(1)} has invalid allowed scene")
        if match.group(2) not in plot_scene_ids:
            raise StoryPackageError(f"storylet {match.group(1)} references an unknown scene")
        links = tuple(re.findall(r"\]\(plot\.md#([^)]+)\)", sections["Source beats:"]))
        if not links:
            raise StoryPackageError(f"storylet {match.group(1)} lacks plot.md source links")
        unresolved = next((link for link in links if link not in plot_beat_anchors), None)
        if unresolved is not None:
            raise StoryPackageError(
                f"storylet {match.group(1)} links to an unknown plot heading; unresolved beat anchor '{unresolved}'"
            )
        window = dict(re.findall(r"-\s*(earliest|target|latest):\s*`([^`]+)`", sections["Pacing window"]))
        if set(window) != {"earliest", "target", "latest"}:
            raise StoryPackageError(f"storylet {match.group(1)} has an invalid pacing window")
        impact = sections["Pacing impact"].strip("` \n")
        storylets.append(
            Storylet(
                id=match.group(1),
                scene_id=match.group(2),
                title=match.group(3),
                source_links=links,
                sections=sections,
                earliest_turn=_turn(window["earliest"]),
                target_turn=_turn(window["target"]),
                latest_turn=_turn(window["latest"]),
                pacing_impact=impact,
            )
        )
    return tuple(storylets)


def _compile_knowledge_indexes(catalog: KnowledgeCatalog) -> KnowledgeIndexes:
    """Compile deterministic indexes so runtime never interprets author prose."""

    by_id = {item.id: item for item in catalog.knowledge}
    facts_to_knowledge: dict[str, list[str]] = {}
    source_to_knowledge: dict[str, list[str]] = {}
    scene_to_candidates: dict[str, list[str]] = {}
    alias_to_knowledge: dict[str, list[str]] = {}
    audience_to_known_terms: dict[str, list[str]] = {}
    prerequisite_dependents: dict[str, list[str]] = {}
    for item in catalog.knowledge:
        if item.source.kind == "storylet_realization":
            source_key = f"storylet:{item.source.storylet_id}:{item.source.realization_id}"
        elif item.source.kind == "canonical_route_event":
            source_key = f"event:{item.source.canonical_event_id}"
        else:
            source_key = f"entry:{item.available_in_scenes[0]}"
        source_to_knowledge.setdefault(source_key, []).append(item.id)
        for effect in item.establishes:
            facts_to_knowledge.setdefault(effect.fact_id, []).append(item.id)
        for scene_id in item.available_in_scenes:
            scene_to_candidates.setdefault(scene_id, []).append(item.id)
        for alias in item.aliases:
            alias_to_knowledge.setdefault(alias.casefold(), []).append(item.id)
        audience_key = item.audience.kind + ":" + ",".join(item.audience.character_ids)
        audience_to_known_terms.setdefault(audience_key, []).extend((item.statement, *item.aliases))
        for predicate in item.requires:
            prerequisite_dependents.setdefault(predicate.fact_id, []).append(item.id)

    def frozen(values: dict[str, list[str]]) -> dict[str, tuple[str, ...]]:
        return {key: tuple(sorted(set(value))) for key, value in values.items()}

    return KnowledgeIndexes(
        by_id=by_id,
        facts_to_knowledge=frozen(facts_to_knowledge),
        source_to_knowledge=frozen(source_to_knowledge),
        scene_to_candidates=frozen(scene_to_candidates),
        alias_to_knowledge=frozen(alias_to_knowledge),
        audience_to_known_terms={key: tuple(sorted(set(value))) for key, value in audience_to_known_terms.items()},
        prerequisite_dependents=frozen(prerequisite_dependents),
    )


def _validate_knowledge(package: StoryPackage) -> None:
    """Fail closed when a declarative revelation cannot be proven package-local."""

    scenes = {scene.metadata.scene_id for scene in package.scenes}
    entity_groups = (package.world.locations, package.world.npcs, package.world.items)
    entities = {entity.id for group in entity_groups for entity in group}
    facts = package.fact_ids
    catalog = package.knowledge
    if {item.id for item in catalog.facts} != facts or len(catalog.facts) != len(facts):
        raise StoryPackageError("knowledge facts must define every world fact exactly once")
    if {frame.scene_id for frame in catalog.scene_frames} != scenes or len(catalog.scene_frames) != len(scenes):
        raise StoryPackageError("knowledge must declare exactly one safe scene frame per scene")
    routes = {route.id: route for route in package.storylet_routes.storylets}
    canonical_events = {
        event.id: event
        for event in (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events)
    }
    transition_trigger_facts = {
        (transition.source_scene_id, trigger.fact_id)
        for transition in package.pacing.transitions
        for trigger in transition.triggers
    }
    scene_order = {scene.metadata.scene_id: index for index, scene in enumerate(package.scenes)}
    produced_by: dict[str, set[str]] = {}
    for known in catalog.knowledge:
        for effect in known.establishes:
            produced_by.setdefault(effect.fact_id, set()).update(known.available_in_scenes)
    seen_ids: set[str] = set()
    owned_effects: set[tuple[str, str, str, str, object]] = set()
    graph: dict[str, set[str]] = {}
    for item in catalog.knowledge:
        if item.id in seen_ids:
            raise StoryPackageError(f"duplicate knowledge ID '{item.id}'")
        seen_ids.add(item.id)
        if set(item.entity_ids + item.relevance.entity_ids) - entities:
            raise StoryPackageError(f"knowledge '{item.id}' references unknown entities")
        if set(item.available_in_scenes) - scenes:
            raise StoryPackageError(f"knowledge '{item.id}' references an unknown scene")
        required_facts = {predicate.fact_id for predicate in item.requires}
        established_facts = {effect.fact_id for effect in item.establishes}
        if required_facts - facts or established_facts - facts:
            raise StoryPackageError(f"knowledge '{item.id}' references an unknown fact")
        if (
            item.source.kind == "storylet_realization"
            and any(
                effect.op == "assert" and (scene_id, effect.fact_id) in transition_trigger_facts
                for scene_id in item.available_in_scenes
                for effect in item.establishes
            )
            and not item.must_convey
        ):
            raise StoryPackageError(
                f"selectable knowledge '{item.id}' establishes a scene-transition trigger but has no must_convey"
            )
        if item.audience.kind == "characters" and set(item.audience.character_ids) - {
            entity.id for entity in package.world.npcs
        }:
            raise StoryPackageError(f"knowledge '{item.id}' references an unknown audience character")
        if item.source.kind == "storylet_realization":
            route = routes.get(item.source.storylet_id or "")
            if route is None or route.scene_id not in item.available_in_scenes:
                raise StoryPackageError(f"knowledge '{item.id}' has a source unavailable in its scene")
            realization = next((value for value in route.realizations if value.id == item.source.realization_id), None)
            if realization is None:
                raise StoryPackageError(f"knowledge '{item.id}' references an unknown realization")
            route_effects = set(realization.operations)
            if not set(item.establishes).issubset(route_effects):
                raise StoryPackageError(f"knowledge '{item.id}' effects differ from its realization")
        elif item.source.kind == "canonical_route_event":
            event = canonical_events.get(item.source.canonical_event_id or "")
            if event is None or event.scene_id not in item.available_in_scenes:
                raise StoryPackageError(f"knowledge '{item.id}' has an unknown or cross-scene canonical event source")
            if not set(item.establishes).issubset(set(event.operations)):
                raise StoryPackageError(f"knowledge '{item.id}' effects differ from its canonical event")
        else:
            if len(item.available_in_scenes) != 1:
                raise StoryPackageError(f"knowledge '{item.id}' scene entry must name exactly one scene")
            entry_fact = f"scene_{item.available_in_scenes[0].lower()}_entry_known"
            if set(item.establishes) != {RouteOperation(op="assert", fact_id=entry_fact, value=True)}:
                raise StoryPackageError(f"knowledge '{item.id}' scene entry effects differ from its entry fact")
        if {effect.fact_id for effect in item.establishes} & {predicate.fact_id for predicate in item.requires}:
            raise StoryPackageError(f"knowledge '{item.id}' establishes its own prerequisite")
        for predicate in item.requires:
            available = produced_by.get(predicate.fact_id, set())
            reachable = any(
                scene_order[source] <= scene_order[target]
                for source in available
                for target in item.available_in_scenes
            )
            if not reachable:
                raise StoryPackageError(f"knowledge '{item.id}' has an unreachable prerequisite")
        for predicate in item.requires:
            graph.setdefault(predicate.fact_id, set()).update(effect.fact_id for effect in item.establishes)
        for effect in item.establishes:
            key = (
                item.source.storylet_id or "scene_entry",
                item.source.realization_id or item.id,
                effect.op,
                effect.fact_id,
                effect.value,
            )
            if key in owned_effects:
                raise StoryPackageError("knowledge source/effect ownership is ambiguous")
            owned_effects.add(key)
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(fact_id: str) -> None:
        if fact_id in visiting:
            raise StoryPackageError("knowledge prerequisite/reveal cycle")
        if fact_id not in visited:
            visiting.add(fact_id)
            for next_fact in graph.get(fact_id, ()):
                visit(next_fact)
            visiting.remove(fact_id)
            visited.add(fact_id)

    for fact_id in graph:
        visit(fact_id)


def _validate(package: StoryPackage) -> None:
    scenes = {scene.metadata.scene_id: scene for scene in package.scenes}
    entity_groups = (package.world.locations, package.world.npcs, package.world.items)
    entities = {entity.id for group in entity_groups for entity in group}
    if sum(len(group) for group in entity_groups) != len(entities):
        raise StoryPackageError("entity IDs must be unique")
    for group in entity_groups:
        for entity in group:
            if set(entity.fallback_ids) - entities:
                raise StoryPackageError(f"entity '{entity.id}' has an unknown fallback")
    if package.protagonist_id not in {entity.id for entity in package.world.npcs}:
        raise StoryPackageError("protagonist_id must name an NPC")
    for scene in package.scenes:
        unknown = set(scene.metadata.participant_ids + scene.metadata.item_ids) - entities
        if scene.metadata.location_id not in entities:
            unknown.add(scene.metadata.location_id)
        if unknown:
            raise StoryPackageError(f"scene {scene.metadata.scene_id} references unknown entities: {sorted(unknown)}")
    transition_ids = set()
    outgoing: dict[str, list[str]] = {scene_id: [] for scene_id in scenes}
    for transition in package.pacing.transitions:
        if transition.id in transition_ids:
            raise StoryPackageError(f"duplicate transition ID '{transition.id}'")
        transition_ids.add(transition.id)
        if transition.source_scene_id not in scenes or transition.target_scene_id not in scenes:
            raise StoryPackageError(f"transition '{transition.id}' references an unknown scene")
        if {trigger.fact_id for trigger in transition.triggers} - set(package.world.facts):
            raise StoryPackageError(f"transition '{transition.id}' has an unknown trigger predicate")
        if set(transition.required_dependencies) - (entities | set(package.world.facts)):
            raise StoryPackageError(f"transition '{transition.id}' has unknown dependency")
        outgoing[transition.source_scene_id].append(transition.target_scene_id)
    for scene in package.scenes:
        if set(scene.metadata.transition_ids) - transition_ids:
            raise StoryPackageError(f"scene {scene.metadata.scene_id} references an unknown transition")
    pacing_scene_ids = {pacing.scene_id for pacing in package.pacing.scenes}
    if len(pacing_scene_ids) != len(package.pacing.scenes) or pacing_scene_ids != set(scenes):
        raise StoryPackageError("pacing must declare exactly one window per scene")
    windows = {p.scene_id: p for p in package.pacing.scenes}
    handoff_seconds = sum(window.handoff_after_turns for window in package.pacing.scenes) * 60
    if handoff_seconds > package.pacing.budget_seconds:
        raise StoryPackageError(
            f"pacing handoff sum {handoff_seconds} seconds exceeds budget_seconds {package.pacing.budget_seconds}"
        )
    event_ids: set[str] = set()
    for event in package.pacing.events:
        if event.id in event_ids:
            raise StoryPackageError(f"duplicate pacing event ID '{event.id}'")
        event_ids.add(event.id)
        if event.scene_id not in scenes:
            raise StoryPackageError(f"pacing event '{event.id}' references an unknown scene")
        if event.transition_id and event.transition_id not in transition_ids:
            raise StoryPackageError(f"pacing event '{event.id}' references an unknown transition")
        if {effect.fact_id for effect in event.effects} - set(package.world.facts):
            raise StoryPackageError(f"pacing event '{event.id}' has an unknown effect predicate")
        window = windows[event.scene_id]
        if not 0 <= event.at_turn <= window.handoff_after_turns:
            raise StoryPackageError(f"pacing event '{event.id}' escapes its scene pacing window")
        if event.at_turn > window.min_turns:
            raise StoryPackageError(
                f"pacing event '{event.id}' at turn {event.at_turn} in scene {event.scene_id} "
                f"exceeds its min_turns floor {window.min_turns}"
            )
    for storylet in package.storylets:
        if storylet.scene_id not in scenes:
            raise StoryPackageError(f"storylet '{storylet.id}' references unknown scene")
        window = windows[storylet.scene_id]
        within_scene_window = (
            0 <= storylet.earliest_turn <= storylet.target_turn <= storylet.latest_turn
            and storylet.latest_turn <= window.handoff_after_turns
        )
        if not within_scene_window:
            raise StoryPackageError(f"storylet '{storylet.id}' escapes its scene pacing window")
    route_ids = {route.id for route in package.storylet_routes.storylets}
    if route_ids != {storylet.id for storylet in package.storylets}:
        raise StoryPackageError("storylet-routes must declare exactly the storylets in storylets.md")
    if package.storylet_routes.canonical_scene_chain != tuple(scene.metadata.scene_id for scene in package.scenes):
        raise StoryPackageError("storylet-routes canonical scene chain must match plot order")
    if package.storylet_routes.sole_ending_scene_id != package.scenes[-1].metadata.scene_id:
        raise StoryPackageError("storylet-routes sole ending must be the final plot scene")
    for route in package.storylet_routes.storylets:
        if route.scene_id not in scenes or route.id not in route_ids:
            raise StoryPackageError("storylet route references unknown scene")
        window = windows[route.scene_id]
        if not 0 <= route.earliest_turn <= route.target_turn <= route.latest_turn <= window.handoff_after_turns:
            raise StoryPackageError(f"storylet '{route.id}' escapes its scene pacing window")
        if {item.fact_id for item in route.activation_conditions} - set(package.world.facts):
            raise StoryPackageError(f"storylet route '{route.id}' has an unknown activation fact")
        for realization in route.realizations:
            if {operation.fact_id for operation in realization.operations} - set(package.world.facts):
                raise StoryPackageError(f"storylet route '{route.id}' has an unknown operation fact")
            if set(realization.protected_knowledge_boundaries) - set(package.world.protected_knowledge):
                raise StoryPackageError(f"storylet route '{route.id}' has an unknown protected boundary")
    for event in (*package.storylet_routes.bridge_events, *package.storylet_routes.resolution_events):
        if event.scene_id not in scenes:
            raise StoryPackageError(f"canonical route event '{event.id}' references an unknown scene")
        activation_facts = set(event.activation.all_facts_true) | set(event.activation.any_of)
        if activation_facts - set(package.world.facts):
            raise StoryPackageError(f"canonical route event '{event.id}' has an unknown activation fact")
        if event.activation.any_of and not 1 <= event.activation.at_least <= len(event.activation.any_of):
            raise StoryPackageError(
                f"canonical route event '{event.id}' has an activation threshold outside "
                f"1..{len(event.activation.any_of)}"
            )
        if not event.activation.any_of and event.activation.at_least > 0:
            raise StoryPackageError(
                f"canonical route event '{event.id}' has an activation threshold without a fact pool"
            )
        if not event.activation.all_facts_true and not event.activation.any_of:
            raise StoryPackageError(f"canonical route event '{event.id}' has a vacuous activation rule")
        if {operation.fact_id for operation in event.operations} - set(package.world.facts):
            raise StoryPackageError(f"canonical route event '{event.id}' has an unknown operation fact")
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(scene_id: str) -> None:
        if scene_id in visiting:
            raise StoryPackageError("scene transition graph contains a dependency cycle")
        if scene_id not in visited:
            visiting.add(scene_id)
            for target in outgoing[scene_id]:
                visit(target)
            visiting.remove(scene_id)
            visited.add(scene_id)

    for scene_id in scenes:
        visit(scene_id)
    for source_id in scenes:
        tied = [t for t in package.pacing.transitions if t.source_scene_id == source_id]
        if len({(t.priority, tuple(t.triggers)) for t in tied}) != len(tied):
            raise StoryPackageError(f"transitions from {source_id} have ambiguous priority")


def _validate_deliveries(package: StoryPackage) -> None:
    """Fail closed when a canonical bridge cannot safely carry a fact.

    Together, the delivery-direction and missing-delivery checks make the
    bridge invariant explicit: every required fact is either deliverable or
    has no player-visible knowledge definition and is therefore world-only.
    """

    from storygame.runtime.validation import unconveyed_terms

    scenes = {scene.metadata.scene_id: scene for scene in package.scenes}
    facts = package.fact_ids
    canonical_events = package.storylet_routes.bridge_events
    exit_prerequisite_facts = {
        fact_id
        for event in canonical_events
        for fact_id in (*event.activation.all_facts_true, *event.activation.any_of)
    }
    player_safe_facts = {
        effect.fact_id
        for known in package.knowledge.knowledge
        if known.audience.player_visible
        for effect in known.establishes
    }
    deliveries_by_fact: dict[str, FactDelivery] = {}
    for delivery in package.deliveries:
        if delivery.fact_id not in facts:
            raise StoryPackageError(f"delivery for fact '{delivery.fact_id}' references an unknown fact")
        if delivery.fact_id in deliveries_by_fact:
            raise StoryPackageError(f"fact '{delivery.fact_id}' has more than one delivery")
        deliveries_by_fact[delivery.fact_id] = delivery
        scene = scenes.get(delivery.scene_id)
        if scene is None:
            raise StoryPackageError(f"delivery for fact '{delivery.fact_id}' references an unknown scene")
        if delivery.source_entity_id and delivery.source_entity_id not in scene.metadata.participant_ids:
            raise StoryPackageError(
                f"delivery for fact '{delivery.fact_id}' names source entity '{delivery.source_entity_id}' "
                f"absent from scene {delivery.scene_id} participants"
            )
        unknown_costs = {cost.fact_id for cost in delivery.costs} - facts
        if unknown_costs:
            raise StoryPackageError(
                f"delivery for fact '{delivery.fact_id}' has unknown cost fact(s): {sorted(unknown_costs)}"
            )
        missing = unconveyed_terms(delivery.must_convey, delivery.fallback_text)
        if missing:
            raise StoryPackageError(
                f"delivery for fact '{delivery.fact_id}' fallback_text does not convey: {', '.join(missing)}"
            )
        player_safe = any(
            known.audience.player_visible
            for known in package.knowledge.knowledge
            if any(effect.fact_id == delivery.fact_id for effect in known.establishes)
        )
        if not player_safe:
            raise StoryPackageError(
                f"delivery for fact '{delivery.fact_id}' has no player-visible knowledge definition"
            )
    # World-only prerequisites, such as Rebecca's observation, are deliberately
    # absent from this audit: they arrive from declared world actions rather
    # than from a player-visible handoff.
    missing_deliveries = sorted((exit_prerequisite_facts & player_safe_facts) - set(deliveries_by_fact))
    if missing_deliveries:
        fact_id = missing_deliveries[0]
        raise StoryPackageError(f"bridge-required fact '{fact_id}' has no FactDelivery")


def load_story_package(root: Path) -> StoryPackage:
    """Load one package directory without accepting prose as runtime truth."""
    try:
        plot_text = (root / "plot.md").read_text(encoding="utf-8")
        scenes = _parse_scenes(plot_text)
        plot_beat_anchors = {anchor for scene in scenes for anchor in scene.beats}
        plot_scene_ids = {scene.metadata.scene_id for scene in scenes}
        storylets = _parse_storylets(
            (root / "storylets.md").read_text(encoding="utf-8"), plot_beat_anchors, plot_scene_ids
        )
        world = WorldSource.model_validate(_yaml(root / "world.yaml"))
        pacing = PacingSource.model_validate(_yaml(root / "pacing.yaml"))
        routes_raw = _yaml(root / "storylet-routes.yaml")
        knowledge = KnowledgeCatalog.model_validate(_yaml(root / "knowledge.yaml"))
        handoffs_raw = _yaml(root / "handoffs.yaml")
        raw_deliveries = handoffs_raw.get("deliveries")
        if not isinstance(raw_deliveries, list):
            raise StoryPackageError("YAML handoffs.yaml must contain a deliveries list")
        deliveries = tuple(FactDelivery.model_validate(item) for item in raw_deliveries)

        def event_source(item: dict[str, Any]) -> dict[str, Any]:
            activation = item.get("activation", {})
            return {
                "id": item["id"],
                "scene_id": item["scene_id"],
                "activation": {
                    "all_facts_true": activation.get("all_facts_true", ()),
                    "any_of": activation.get("any_of", ()),
                    "at_least": activation.get("at_least", 0),
                },
                "operations": item["produces"],
            }

        routes = StoryletRoutesSource.model_validate(
            {
                "story_id": routes_raw["story_id"],
                "canonical_scene_chain": routes_raw["contract"]["canonical_scene_chain"],
                "sole_ending_scene_id": routes_raw["contract"]["sole_ending_scene_id"],
                "storylets": tuple(
                    {
                        "id": item["id"],
                        "scene_id": item["scene_id"],
                        "title": item["title"],
                        "activation_conditions": item["activation"].get("conditions", ()),
                        "earliest_turn": item["activation"]["pacing"]["earliest_turn"],
                        "target_turn": item["activation"]["pacing"]["target_turn"],
                        "latest_turn": item["activation"]["pacing"]["latest_turn"],
                        "pressure_role": item["pressure_role"],
                        "realizations": item["realization_options"],
                    }
                    for item in routes_raw["storylets"]
                ),
                "bridge_events": tuple(event_source(item) for item in routes_raw.get("canonical_bridge_events", ())),
                "resolution_events": tuple(
                    event_source(item) for item in routes_raw.get("canonical_resolution_events", ())
                ),
            }
        )
    except (OSError, ValidationError) as exc:
        raise StoryPackageError(str(exc)) from exc
    package = StoryPackage(
        story_id=world.story_id,
        protagonist_id=world.protagonist_id,
        scenes=scenes,
        world=world,
        pacing=pacing,
        storylets=storylets,
        storylet_routes=routes,
        knowledge=knowledge,
        knowledge_indexes=_compile_knowledge_indexes(knowledge),
        deliveries=deliveries,
    )
    _validate(package)
    _validate_knowledge(package)
    _validate_deliveries(package)
    return package

"""Orchestrate validation, deterministic source compilation, and loader checks."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from storygame.story_package import loader
from storygame.story_package.models import (
    Character,
    FactPredicate,
    KnowledgeCatalog,
    PacingSource,
    StoryletRoutesSource,
    StoryPackage,
)

from . import check_source_tree
from .c_knowledge import build_events, build_incidents, build_knowledge, build_routes, contexts
from .c_scene import (
    build_ending,
    build_frame,
    build_pacing_scene,
    build_scene,
    build_transition,
)
from .c_scene import (
    build_events as build_scene_events,
)
from .c_world import build_connections, build_fact_models, build_facts, build_world
from .diagnostics import Diagnostic, SourceError
from .reader import SourceTree

COMPILER_VERSION = "1"


def compile_source_tree(root: Path) -> StoryPackage:
    """Compile a validated source tree into a checked StoryPackage."""

    diagnostics = check_source_tree(root)
    if diagnostics:
        raise SourceError(diagnostics)
    tree, reader_diagnostics = _read_validated(root)
    if reader_diagnostics:
        raise SourceError(reader_diagnostics)
    try:
        package = _build_package(tree)
        _run_loader_checks(package)
    except Exception as error:
        raise SourceError([_loader_diagnostic(error)]) from error
    return package


def _read_validated(root: Path) -> tuple[SourceTree, list[Diagnostic]]:
    """Read source files after the public validation pass."""

    from .reader import read_source_tree

    return read_source_tree(root)


def _build_package(tree: SourceTree) -> StoryPackage:
    """Assemble all immutable package fields from ordered source records."""

    story = _mapping(tree.files["story.yaml"])
    catalog = _mapping(tree.files["catalog.yaml"])
    scene_records = _scene_records(tree, story["scenes"])
    facts = build_facts(scene_records, catalog)
    world = build_world(story, catalog, facts)
    entity_kinds = _entity_kinds(world)
    scenes = tuple(build_scene(scene, entity_kinds) for _, scene in scene_records)
    scene_contexts = contexts(scene_records, tree.files)
    storylets, routes = build_routes(scene_contexts)
    claims, deliveries = build_knowledge(scene_contexts, routes)
    knowledge = KnowledgeCatalog(
        schema_version="2.0",
        facts=build_fact_models(facts),
        scene_frames=tuple(build_frame(scene) for _, scene in scene_records),
        knowledge=claims,
    )
    bridges, _ = build_events(scene_contexts)
    incidents = build_incidents(scene_contexts, routes)
    pacing = PacingSource(
        budget_seconds=story["budget_seconds"],
        scenes=tuple(build_pacing_scene(scene) for _, scene in scene_records),
        transitions=tuple(
            transition for _, scene in scene_records if (transition := build_transition(scene)) is not None
        ),
        events=tuple(event for _, scene in scene_records for event in build_scene_events(scene)),
        ending=build_ending(scene_records[-1][1]),
    )
    pacing = _supply_transition_sources(pacing)
    routes_source = StoryletRoutesSource(
        story_id=story["story"],
        canonical_scene_chain=tuple(story["scenes"]),
        sole_ending_scene_id=story["scenes"][-1],
        storylets=routes,
        bridge_events=bridges,
    )
    return StoryPackage(
        story_id=story["story"],
        protagonist_id=story["protagonist"],
        genre=story.get("genre", ""),
        characters=_characters(story, catalog),
        scenes=scenes,
        world=world,
        pacing=pacing,
        storylets=storylets,
        storylet_routes=routes_source,
        knowledge=knowledge,
        knowledge_indexes=loader._compile_knowledge_indexes(knowledge, world),
        deliveries=deliveries,
        incidents=incidents,
        connections=build_connections(catalog),
    )


def _mapping(value: object) -> Mapping:
    """Require a validated source document to be a mapping."""

    if not isinstance(value, Mapping):
        raise ValueError("validated source document is not a mapping")
    return value


def _scene_records(tree: SourceTree, scene_ids: list[str]) -> list[tuple[str, Mapping]]:
    """Return scene documents in the explicit root scene order."""

    records = []
    for scene_id in scene_ids:
        records.append((scene_id, _mapping(tree.files[f"scenes/{scene_id}.yaml"])))
    return records


def _entity_kinds(world) -> dict[str, str]:
    """Classify catalog IDs for placement routing."""

    return {
        **{entity.id: "place" for entity in world.locations},
        **{entity.id: "character" for entity in world.npcs},
        **{entity.id: "group" for entity in world.groups},
        **{entity.id: "item" for entity in world.items},
    }


def _characters(story: Mapping, catalog: Mapping) -> tuple[Character, ...]:
    """Build principal character records in the root's explicit order."""

    raw = catalog.get("characters", {})
    result: list[Character] = []
    for identifier in story.get("principal_characters", ()):
        record = raw[identifier]
        result.append(Character(id=identifier, name=record["name"], bio=record.get("narrator_bio") or record["bio"]))
    return tuple(result)


def _supply_transition_sources(pacing: PacingSource) -> PacingSource:
    """Ensure every positive transition trigger has a local pacing producer."""

    events = list(pacing.events)
    for transition in pacing.transitions:
        existing = {
            effect.fact_id
            for event in events
            if event.scene_id == transition.source_scene_id
            for effect in event.effects
            if effect.equals is True
        }
        missing = [
            trigger.fact_id
            for trigger in transition.triggers
            if trigger.equals is True and trigger.fact_id not in existing
        ]
        if not missing:
            continue
        index = next(index for index, event in enumerate(events) if event.scene_id == transition.source_scene_id)
        event = events[index]
        effects = (*event.effects, *(FactPredicate(fact_id=fact_id, equals=True) for fact_id in missing))
        events[index] = event.model_copy(update={"effects": effects})
    return pacing.model_copy(update={"events": tuple(events)})


def _run_loader_checks(package: StoryPackage) -> None:
    """Run every inherited loader check in its established order."""

    loader._validate_disclosure_guards(package)
    loader._validate_knowledge(package)
    loader._validate_entry_variants(package)
    loader._validate(package)
    loader._validate_authored_handoffs(package)
    loader._validate_deliveries(package)
    loader._validate_incidents(package)
    loader._validate_connections(package)
    loader._validate_transition_trigger_sources(package)
    loader._validate_resolution_entry_guarantees(package)
    loader._validate_required_reveal_prerequisites(package)
    loader._validate_ending(package)


def _loader_diagnostic(error: Exception) -> Diagnostic:
    """Wrap an inherited loader failure using the contract's stable names."""

    message = str(error)
    lowered = message.casefold()
    name = "L2.cycles" if "cycle" in lowered or "establishes its own prerequisite" in lowered else "LOADER"
    return Diagnostic(name=name, file="", address="loader", field="package", message=message)

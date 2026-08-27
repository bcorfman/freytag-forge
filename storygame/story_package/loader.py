"""Strict loaders and cross-reference validation for Markdown story packages."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from storygame.story_package.models import (
    PacingSource,
    Scene,
    SceneMetadata,
    Storylet,
    StoryletRoutesSource,
    StoryPackage,
    WorldSource,
)


class StoryPackageError(ValueError):
    """A source package is malformed or internally inconsistent."""


_SCENE = re.compile(r"^## Scene ([1-9][A-Z]) .*$", re.MULTILINE)
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
        prose = body[frontmatter.end() :].strip()
        scenes.append(Scene(metadata=metadata, prose=prose))
    return tuple(scenes)


def _clock(value: str) -> int:
    match = re.fullmatch(r"(\d{2}):(\d{2}):(\d{2})", value.strip())
    if not match:
        raise StoryPackageError(f"invalid timestamp '{value}' (use HH:MM:SS)")
    hour, minute, second = map(int, match.groups())
    if minute > 59 or second > 59:
        raise StoryPackageError(f"invalid timestamp '{value}'")
    return hour * 3600 + minute * 60 + second


def _parse_storylets(text: str, plot_anchors: set[str]) -> tuple[Storylet, ...]:
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
        links = tuple(re.findall(r"\]\(plot\.md#([^)]+)\)", sections["Source beats:"]))
        if not links:
            raise StoryPackageError(f"storylet {match.group(1)} lacks plot.md source links")
        if any(not any(link.startswith(anchor) for anchor in plot_anchors) for link in links):
            raise StoryPackageError(f"storylet {match.group(1)} links to an unknown plot heading")
        window = dict(re.findall(r"(earliest|target|latest):\s*`?([0-9:]+)`?", sections["Pacing window"]))
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
                earliest_seconds=_clock(window["earliest"]),
                target_seconds=_clock(window["target"]),
                latest_seconds=_clock(window["latest"]),
                pacing_impact=impact,
            )
        )
    return tuple(storylets)


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
        if not window.earliest_seconds <= event.at_seconds <= window.latest_seconds:
            raise StoryPackageError(f"pacing event '{event.id}' escapes its scene pacing window")
    for storylet in package.storylets:
        if storylet.scene_id not in scenes:
            raise StoryPackageError(f"storylet '{storylet.id}' references unknown scene")
        window = windows[storylet.scene_id]
        within_scene_window = (
            window.earliest_seconds <= storylet.earliest_seconds <= storylet.target_seconds
            and storylet.latest_seconds <= window.latest_seconds
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
        if {item.fact_id for item in event.activation_conditions} - set(package.world.facts):
            raise StoryPackageError(f"canonical route event '{event.id}' has an unknown activation fact")
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


def load_story_package(root: Path) -> StoryPackage:
    """Load one package directory without accepting prose as runtime truth."""
    try:
        plot_text = (root / "plot.md").read_text(encoding="utf-8")
        scenes = _parse_scenes(plot_text)
        scene_ids = re.findall(r"^### Scene ([1-9][A-Z])\.\d+", plot_text, re.MULTILINE)
        plot_anchors = {f"scene-{scene.lower()}" for scene in scene_ids}
        storylets = _parse_storylets((root / "storylets.md").read_text(encoding="utf-8"), plot_anchors)
        world = WorldSource.model_validate(_yaml(root / "world.yaml"))
        pacing = PacingSource.model_validate(_yaml(root / "pacing.yaml"))
        routes_raw = _yaml(root / "storylet-routes.yaml")

        def event_source(item: dict[str, Any]) -> dict[str, Any]:
            activation = item.get("activation", {})
            return {
                "id": item["id"],
                "scene_id": item["scene_id"],
                "activation_conditions": tuple(
                    {"fact_id": fact_id, "equals": True} for fact_id in activation.get("all_facts_true", ())
                ),
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
                        "earliest_seconds": item["activation"]["pacing"]["earliest_seconds"],
                        "target_seconds": item["activation"]["pacing"]["target_seconds"],
                        "latest_seconds": item["activation"]["pacing"]["latest_seconds"],
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
    )
    _validate(package)
    return package

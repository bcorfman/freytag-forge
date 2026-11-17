"""Resolve declarative story addresses against compiled packages and source trees.

Compiled ``StoryPackage`` values are the runtime truth.  The compiler does not
retain the source tree, so source-only handles (reveal, variant, part, and
authored templates) are read from an explicitly exposed ``source_root`` when
available, or from the current local source-tree candidates used by tests and
CLI callers.  The default package is loaded through the legacy loader once.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Any

from storygame.story_package.loader import load_story_package
from storygame.story_package.models import StoryPackage

from .reader import SourceTree, read_source_tree

_STORIES_ROOT = Path(__file__).resolve().parents[2] / "data" / "stories"
_ADDRESS = re.compile(r"^(?P<kind>[a-z]+):(?P<id>[^.\[\]]+)(?:\.(?P<fields>.+))?$")
_SEGMENT = re.compile(r"^(?P<name>[^\[\]]+?)(?:\[(?P<selector>-?\d+)\])?$")
_SOURCE_ATTRIBUTES = ("source_root", "_source_root", "source_path", "_source_path")


@dataclass(frozen=True)
class _Address:
    """Parsed address components, keeping the original for errors."""

    address: str
    kind: str
    identifier: str
    fields: tuple[tuple[str, int | None], ...]


def story_text(address: str, *, package: StoryPackage | None = None, source: bool = False) -> str:
    """Return a string-valued address, optionally using its authored template."""

    parsed = _parse(address)
    if source:
        raw = _source_value(parsed, package)
        if raw is not _MISSING:
            return _as_text(raw, parsed)
    resolved_package = _get_package(package)
    try:
        value = _resolve(parsed, resolved_package)
    except KeyError:
        raw = _source_value(parsed, package)
        if raw is _MISSING:
            raise
        value = raw
    return _as_text(value, parsed)


def story_value(address: str, *, package: StoryPackage | None = None) -> object:
    """Return the package value at an address without coercing its type."""

    parsed = _parse(address)
    return _resolve(parsed, _get_package(package))


class _Missing:
    """Sentinel for a source lookup that has no usable source tree."""


_MISSING = _Missing()


def _parse(address: str) -> _Address:
    """Parse the contract grammar, including dotted outline IDs."""

    match = _ADDRESS.fullmatch(address)
    if match is None:
        raise KeyError(address)
    kind = match["kind"]
    identifier = match["id"]
    fields_text = match["fields"] or ""
    if kind == "outline" and fields_text:
        first, separator, remainder = fields_text.partition(".")
        if separator:
            identifier = f"{identifier}.{first}"
            fields_text = remainder
    fields = tuple(_field_parts(fields_text, address))
    return _Address(address, kind, identifier, fields)


def _field_parts(fields: str, address: str) -> list[tuple[str, int | None]]:
    """Parse dotted fields and optional integer selectors."""

    if not fields:
        return []
    result: list[tuple[str, int | None]] = []
    for field in fields.split("."):
        match = _SEGMENT.fullmatch(field)
        if match is None or not match["name"]:
            raise KeyError(address)
        selector = match["selector"]
        result.append((match["name"], int(selector) if selector is not None else None))
    return result


def _get_package(package: StoryPackage | None) -> StoryPackage:
    """Use the supplied package or the cached legacy default."""

    return package if package is not None else _default_package()


@cache
def _default_package() -> StoryPackage:
    """Load the default story package once through the normal loader."""

    roots = tuple(path for path in sorted(_STORIES_ROOT.iterdir()) if path.is_dir())
    if len(roots) != 1:
        raise RuntimeError("default story package is ambiguous")
    return load_story_package(roots[0])


def _resolve(address: _Address, package: StoryPackage) -> object:
    """Resolve one address from the immutable package model."""

    resolvers = {
        "scene": _scene,
        "fact": _fact,
        "delivery": _delivery,
        "claim": _claim,
        "beat": _beat,
        "exit": _exit,
        "bridge": _bridge,
        "outline": _outline,
        "ending": _ending,
        "entity": _entity,
        "reveal": _reveal,
        "variant": _variant,
        "part": _part,
        "outcome": _outcome,
    }
    resolver = resolvers.get(address.kind)
    if resolver is None:
        raise KeyError(address.address)
    value = resolver(address.identifier, address.fields, package, address.address)
    return _require(value, address.address)


def _scene(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a scene field from its metadata and frame."""

    scene = _find(package.scenes, identifier, "metadata.scene_id", address)
    frame = _find(package.knowledge.scene_frames, identifier, "scene_id", address)
    field = fields[0][0] if fields else ""
    aliases = {"header": "title", "entry": "entry_text", "entry_additions": "entry_variants"}
    if field in {"situation", "pressure"}:
        return _walk(frame, fields, address)
    if field == "title":
        return _walk(scene.opening_beat, (("title", None),), address)
    return _walk(scene.metadata, ((aliases.get(field, field), fields[0][1]), *fields[1:]), address)


def _fact(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a fact definition."""

    fact = _find(package.knowledge.facts, identifier, "id", address)
    return _walk(fact, fields, address)


def _delivery(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a fact delivery."""

    delivery = _find(package.deliveries, identifier, "fact_id", address)
    return _walk(delivery, fields, address)


def _claim(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a player-knowledge claim and its delivery aliases."""

    claim = _find(package.knowledge.knowledge, identifier, "id", address)
    if not fields:
        raise KeyError(address)
    first, selector = fields[0]
    aliases = {"says": "statement", "text": "delivery_text", "text_when": "delivery_variants"}
    return _walk(claim, ((aliases.get(first, first), selector), *fields[1:]), address)


def _beat(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a pacing event, mapping authored ``say`` to realizations."""

    beat = _find(package.pacing.events, identifier, "id", address)
    if not fields:
        raise KeyError(address)
    first, selector = fields[0]
    if first != "say":
        return _walk(beat, fields, address)
    if selector == -1:
        realizations = [item for item in beat.realizations if not item.when]
        if len(realizations) != 1:
            raise KeyError(address)
        value: object = realizations[0]
        return _walk(value, fields[1:], address)
    return _walk(beat, (("realizations", selector), *fields[1:]), address)


def _exit(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a transition, including its legacy metadata bridge text."""

    transition = _find(package.pacing.transitions, identifier, "id", address)
    if fields and fields[0][0] == "bridge":
        scene = _find(package.scenes, transition.source_scene_id, "metadata.scene_id", address)
        value = scene.metadata.bridge_text.get(identifier, _MISSING)
        return _walk(value, fields[1:], address)
    return _walk(transition, fields, address)


def _bridge(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a canonical route bridge event."""

    try:
        event = _find(package.storylet_routes.bridge_events, identifier, "id", address)
    except KeyError:
        value = _source_value(_Address(address, "bridge", identifier, fields), package)
        return _require(value, address)
    return _walk(event, fields, address)


def _outline(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a scene outline beat by its authored beat ID."""

    for scene in package.scenes:
        for beat in scene.beats.values():
            if beat.id == identifier:
                return _walk(beat, fields, address)
    raise KeyError(address)


def _ending(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve the package ending under its contract ID."""

    if identifier != "story" or package.pacing.ending is None:
        raise KeyError(address)
    ending = package.pacing.ending
    if fields and fields[0][0] == "additions":
        return _walk(ending, (("variants", fields[0][1]), *fields[1:]), address)
    return _walk(ending, fields, address)


def _entity(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a catalog entity across the package's world collections."""

    collections = (package.world.locations, package.world.npcs, package.world.groups, package.world.items)
    for collection in collections:
        for entity in collection:
            if entity.id == identifier:
                return _walk(entity, fields, address)
    raise KeyError(address)


def _reveal(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve source-owned reveal fields through the authored handle."""

    value = _source_value(_Address(address, "reveal", identifier, fields), package)
    return _require(value, address)


def _variant(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a variant's intent from routes and its text from the claim."""

    reveal_id, separator, variant_id = identifier.partition("/")
    if not separator:
        raise KeyError(address)
    tree = _source_tree(package)
    if tree is None:
        raise KeyError(address)
    reveal = _source_reveal(tree, reveal_id)
    variants = _read(reveal, ["variants"])
    raw = _read(variants, [variant_id])
    if raw is _MISSING:
        raise KeyError(address)
    if fields and fields[0][0] == "text":
        claim_id = _read(raw, ["claim_id"])
        if isinstance(claim_id, str):
            claim = _find(package.knowledge.knowledge, claim_id, "id", address)
            return _require(_walk(claim, (("delivery_text", fields[0][1]), *fields[1:]), address), address)
    route = _find(package.storylet_routes.storylets, _read(reveal, ["storylet_id"]), "id", address)
    realization_id = _read(raw, ["realization_id"])
    realization = _find(route.realizations, realization_id, "id", address)
    if fields and fields[0][0] == "intent":
        return _walk(realization, (("dramatic_intent", fields[0][1]), *fields[1:]), address)
    return _walk(raw, fields, address)


def _part(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve a named authored part."""

    value = _source_value(_Address(address, "part", identifier, fields), package)
    return _require(value, address)


def _outcome(identifier: str, fields, package: StoryPackage, address: str) -> object:
    """Resolve an incident outcome from ``incident/outcome``."""

    incident_id, separator, outcome_id = identifier.partition("/")
    if not separator:
        raise KeyError(address)
    incident = _find(package.incidents, incident_id, "id", address)
    outcome = _find(incident.outcomes, outcome_id, "id", address)
    return _walk(outcome, fields, address)


def _find(values: Sequence[object], identifier: str, field: str, address: str) -> object:
    """Find a model by an identifying attribute or raise the contract error."""

    for value in values:
        if _read(value, field.split(".")) == identifier:
            return value
    raise KeyError(address)


def _walk(value: object, fields, address: str) -> object:
    """Walk model attributes, mappings, and indexed sequences."""

    for name, selector in fields:
        value = _read(value, [name])
        if selector is not None:
            if not isinstance(value, (list, tuple)):
                raise KeyError(address)
            try:
                value = value[selector]
            except IndexError:
                raise KeyError(address) from None
    return value


def _read(value: object, path: list[str]) -> object:
    """Read one model or mapping key without treating false values as missing."""

    current = value
    for name in path:
        if isinstance(current, Mapping):
            if name not in current:
                return _MISSING
            current = current[name]
        else:
            current = getattr(current, name, _MISSING)
        if current is _MISSING:
            return _MISSING
    return current


def _require(value: object, address: str) -> object:
    """Convert missing and unset values into the required address-named error."""

    if value is _MISSING or value is None:
        raise KeyError(address)
    return value


def _as_text(value: object, address: _Address) -> str:
    """Require the string result promised by ``story_text``."""

    value = _require(value, address.address)
    if not isinstance(value, str):
        raise KeyError(address.address)
    return value


def _source_value(address: _Address, package: StoryPackage | None) -> object:
    """Resolve an authored value when a matching source tree is available."""

    if package is None:
        return _MISSING
    for tree in _source_trees(package):
        raw = _source_record(address, tree)
        if raw is _MISSING:
            continue
        value = _walk(raw, address.fields, address.address)
        if value is not _MISSING and value is not None:
            return value
    return _MISSING


def _source_record(address: _Address, tree: SourceTree) -> object:
    """Select the raw source record corresponding to an address kind."""

    if address.kind == "scene":
        return _source_scene(tree, address.identifier)
    if address.kind == "fact":
        return _source_fact(tree, address.identifier)
    if address.kind == "delivery":
        fact = _source_fact(tree, address.identifier)
        return _read(fact, ["delivery"])
    if address.kind == "claim":
        return _source_claim(tree, address.identifier)
    if address.kind == "beat":
        return _source_beat(tree, address.identifier)
    if address.kind == "exit":
        scene = _source_scene(tree, _source_exit_scene(tree, address.identifier))
        return _read(scene, ["exit"])
    if address.kind == "bridge":
        return _source_bridge(tree, address.identifier)
    if address.kind == "outline":
        return _source_outline(tree, address.identifier)
    if address.kind == "ending":
        return _source_ending(tree, address.identifier)
    if address.kind == "entity":
        return _source_entity(tree, address.identifier)
    if address.kind == "reveal":
        return _source_reveal(tree, address.identifier)
    if address.kind == "variant":
        reveal_id, _, variant_id = address.identifier.partition("/")
        reveal = _source_reveal(tree, reveal_id)
        return _read(_read(reveal, ["variants"]), [variant_id])
    if address.kind == "part":
        reveal_id, _, part_id = address.identifier.partition("/")
        reveal = _source_reveal(tree, reveal_id)
        return _read(_read(reveal, ["parts"]), [part_id])
    if address.kind == "outcome":
        return _source_outcome(tree, address.identifier)
    return _MISSING


def _source_scene(tree: SourceTree, identifier: str) -> object:
    """Read a source scene by ID."""

    return tree.files.get(f"scenes/{identifier}.yaml", _MISSING)


def _source_fact(tree: SourceTree, identifier: str) -> object:
    """Find a fact declaration in scene or catalog source."""

    for document in tree.files.values():
        if not isinstance(document, Mapping):
            continue
        facts = document.get("facts")
        if isinstance(facts, Mapping) and identifier in facts:
            return facts[identifier]
        unplaced = document.get("unplaced_facts")
        if isinstance(unplaced, Mapping) and identifier in unplaced:
            return unplaced[identifier]
    return _MISSING


def _source_claim(tree: SourceTree, identifier: str) -> object:
    """Find a claim in entry, reveal, extra, or bridge source records."""

    for document in tree.files.values():
        if not isinstance(document, Mapping):
            continue
        for claim in document.get("entry_claims", ()) or ():
            if isinstance(claim, Mapping) and claim.get("claim_id") == identifier:
                return claim
        for reveal in document.get("reveals", ()) or ():
            for variant in _variants(reveal):
                if variant.get("claim_id") == identifier:
                    return variant
                for claim in variant.get("extra_claims", ()) or ():
                    if isinstance(claim, Mapping) and claim.get("claim_id") == identifier:
                        return claim
        for bridge in document.get("bridge", ()) or ():
            claim = bridge.get("claim") if isinstance(bridge, Mapping) else None
            if isinstance(claim, Mapping) and claim.get("claim_id") == identifier:
                return claim
    return _MISSING


def _variants(reveal: object) -> tuple[Mapping[str, Any], ...]:
    """Return mapping-valued reveal variants in source order."""

    values = _read(reveal, ["variants"])
    return (
        tuple(value for value in values.values() if isinstance(value, Mapping)) if isinstance(values, Mapping) else ()
    )


def _source_beat(tree: SourceTree, identifier: str) -> object:
    """Find a pacing event by ID."""

    for document in tree.files.values():
        beats = document.get("beats") if isinstance(document, Mapping) else None
        for beat in beats or ():
            if isinstance(beat, Mapping) and beat.get("id") == identifier:
                return beat
    return _MISSING


def _source_exit_scene(tree: SourceTree, identifier: str) -> str:
    """Find the source scene containing a transition ID."""

    for scene_id in _source_scene_ids(tree):
        scene = _source_scene(tree, scene_id)
        exit_record = _read(scene, ["exit"])
        if isinstance(exit_record, Mapping) and exit_record.get("id") == identifier:
            return scene_id
    return ""


def _source_bridge(tree: SourceTree, identifier: str) -> object:
    """Find a bridge event by ID."""

    for document in tree.files.values():
        for bridge in document.get("bridge", ()) if isinstance(document, Mapping) else ():
            if isinstance(bridge, Mapping) and bridge.get("id") == identifier:
                return bridge
    return _MISSING


def _source_outline(tree: SourceTree, identifier: str) -> object:
    """Find an outline record by beat ID."""

    for scene_id in _source_scene_ids(tree):
        scene = _source_scene(tree, scene_id)
        for outline in _read(scene, ["outline"]) or ():
            if isinstance(outline, Mapping) and outline.get("id") == identifier:
                return outline
    return _MISSING


def _source_ending(tree: SourceTree, identifier: str) -> object:
    """Find the ending stored on the final source scene."""

    if identifier != "story":
        return _MISSING
    for scene_id in reversed(_source_scene_ids(tree)):
        ending = _read(_source_scene(tree, scene_id), ["ending"])
        if ending is not _MISSING:
            return ending
    return _MISSING


def _source_entity(tree: SourceTree, identifier: str) -> object:
    """Find a catalog entity across its declared sections."""

    catalog = tree.files.get("catalog.yaml")
    if not isinstance(catalog, Mapping):
        return _MISSING
    for section in ("places", "characters", "groups", "items", "props", "kinds"):
        records = catalog.get(section)
        if isinstance(records, Mapping) and identifier in records:
            return records[identifier]
    return _MISSING


def _source_outcome(tree: SourceTree, identifier: str) -> object:
    """Find an outcome mapping nested in a source incident."""

    incident_id, separator, outcome_id = identifier.partition("/")
    if not separator:
        return _MISSING
    for document in tree.files.values():
        for incident in document.get("incidents", ()) if isinstance(document, Mapping) else ():
            if not isinstance(incident, Mapping) or incident.get("id") != incident_id:
                continue
            reveal_id = incident.get("reveal")
            reveal = _source_reveal(tree, reveal_id) if isinstance(reveal_id, str) else _MISSING
            for variant in _variants(reveal):
                outcome = variant.get("outcome")
                if isinstance(outcome, Mapping) and outcome.get("id") == outcome_id:
                    return outcome
    return _MISSING


def _source_reveal(tree: SourceTree, identifier: str) -> object:
    """Find a reveal by its authored handle."""

    for document in tree.files.values():
        for reveal in document.get("reveals", ()) if isinstance(document, Mapping) else ():
            if isinstance(reveal, Mapping) and reveal.get("id") == identifier:
                return reveal
    return _MISSING


def _source_scene_ids(tree: SourceTree) -> tuple[str, ...]:
    """Return source scene IDs in their declared story order."""

    story = tree.files.get("story.yaml")
    if isinstance(story, Mapping) and isinstance(story.get("scenes"), list):
        return tuple(str(scene_id) for scene_id in story["scenes"])
    return tuple(
        path.removeprefix("scenes/").removesuffix(".yaml")
        for path in sorted(tree.files)
        if path.startswith("scenes/") and path.endswith(".yaml") and ".match." not in path
    )


@cache
def _read_cached(root: Path) -> SourceTree | None:
    """Read one source root once and discard roots with reader errors."""

    tree, diagnostics = read_source_tree(root)
    return tree if not diagnostics else None


def _source_tree(package: StoryPackage) -> SourceTree | None:
    """Find a source tree exposed by a caller or present in the local workspace."""

    trees = _source_trees(package)
    return trees[0] if trees else None


def _source_trees(package: StoryPackage) -> tuple[SourceTree, ...]:
    """Return all matching local source trees in deterministic candidate order."""

    trees: list[SourceTree] = []
    seen: set[Path] = set()
    for attribute in _SOURCE_ATTRIBUTES:
        root = getattr(package, attribute, None)
        if isinstance(root, (str, Path)):
            tree = _matching_tree(Path(root), package.story_id)
            if tree is not None and tree.root not in seen:
                seen.add(tree.root)
                trees.append(tree)
    candidates = [Path.cwd(), Path.cwd() / "data" / "stories" / package.story_id]
    recent = sorted(
        Path("/tmp").rglob("story.yaml"),
        key=lambda path: path.stat().st_mtime_ns,
        reverse=True,
    )
    candidates.extend(path.parent for path in recent[:24])
    for candidate in candidates:
        tree = _matching_tree(candidate, package.story_id)
        if tree is not None and tree.root not in seen:
            seen.add(tree.root)
            trees.append(tree)
    return tuple(trees)


def _matching_tree(root: Path, story_id: str) -> SourceTree | None:
    """Read a candidate root only when its declarative story ID matches."""

    if not (root / "story.yaml").is_file():
        return None
    tree = _read_cached(root.resolve())
    story = tree.files.get("story.yaml") if tree is not None else None
    return tree if isinstance(story, Mapping) and story.get("story") == story_id else None

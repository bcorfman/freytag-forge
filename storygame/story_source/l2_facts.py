"""Layer-two checks for story-wide IDs, references, and fact ownership."""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from .checks import layer2_check
from .diagnostics import Diagnostic
from .reader import SourceTree

_SCENE_FILE = re.compile(r"^scenes/[^/.]+\.yaml$")
_MATCH_FILE = re.compile(r"^scenes/[^/.]+\.match\.yaml$")
_PART = re.compile(r"(?<!\{)\{([a-z][a-z0-9_]*)\}(?!\})")
_SCENE_REF_FIELDS = ("companions", "participants", "items", "prop_pool")


@dataclass(frozen=True)
class _Definition:
    """One author-defined ID and its source location."""

    identifier: str
    file: str
    address: str
    field: str


@dataclass(frozen=True)
class _FactUse:
    """One fact read, written, or referenced by source data."""

    identifier: str
    file: str
    address: str
    field: str
    scene: str | None
    kind: str


@dataclass(frozen=True)
class _Reference:
    """One cross-record reference to validate."""

    identifier: str
    file: str
    address: str
    field: str
    kind: str


def _mapping(value: object) -> dict[Any, Any] | None:
    """Return mappings only, keeping layer-two checks quiet on bad shapes."""

    return value if isinstance(value, dict) else None


def _scene_files(tree: SourceTree) -> list[tuple[str, dict[Any, Any]]]:
    """Return parsed scene documents in deterministic file order."""

    return [
        (file, value)
        for file, value in sorted(tree.files.items())
        if _SCENE_FILE.fullmatch(file) and isinstance(value, dict)
    ]


def _scene_id(data: dict[Any, Any]) -> str | None:
    """Read a usable scene ID from a validated scene document."""

    value = data.get("scene")
    return value if isinstance(value, str) else None


def _put(
    definitions: dict[str, list[_Definition]], kind: str, identifier: object, file: str, address: str, field: str
) -> None:
    """Add a definition when its ID is a string."""

    if isinstance(identifier, str):
        definitions[f"{kind}:{identifier}"].append(_Definition(identifier, file, address, field))


def _collect_definitions(tree: SourceTree) -> dict[str, list[_Definition]]:
    """Collect every ID kind covered by the duplicate-ID contract row."""

    definitions: dict[str, list[_Definition]] = defaultdict(list)
    for file, data in _scene_files(tree):
        _collect_scene_definitions(definitions, file, data)
    catalog = _mapping(tree.files.get("catalog.yaml"))
    if catalog is not None:
        for section in ("places", "characters", "groups", "items"):
            records = _mapping(catalog.get(section))
            if records is not None:
                for identifier in records:
                    _put(definitions, "entity", identifier, "catalog.yaml", f"entity:{identifier}", "id")
    return definitions


def _collect_scene_definitions(definitions: dict[str, list[_Definition]], file: str, data: dict[Any, Any]) -> None:
    """Collect definitions from one scene document."""

    facts = _mapping(data.get("facts"))
    if facts is not None:
        for identifier in facts:
            _put(definitions, "fact", identifier, file, f"fact:{identifier}", str(identifier))
    for index, outline in _enumerate(data.get("outline")):
        if isinstance(outline, dict):
            outline_id = outline.get("id")
            _put(definitions, "outline", outline_id, file, f"outline:{outline_id or index}", "id")
            _put(definitions, "outline_anchor", outline.get("anchor"), file, f"outline:{outline_id or index}", "anchor")
    _collect_list_ids(definitions, file, data.get("beats"), "beat", "id")
    _collect_list_ids(definitions, file, data.get("bridge"), "bridge", "id")
    _collect_list_ids(definitions, file, data.get("incidents"), "incident", "id")
    for _, bridge in _enumerate(data.get("bridge")):
        if isinstance(bridge, dict):
            _collect_claim_record(definitions, file, bridge.get("claim"))
    exit_record = _mapping(data.get("exit"))
    if exit_record is not None:
        _put(definitions, "exit", exit_record.get("id"), file, f"exit:{exit_record.get('id')}", "id")
    _collect_reveal_definitions(definitions, file, data.get("reveals"))
    _collect_claim_list_definitions(definitions, file, data.get("entry_claims"))


def _collect_list_ids(
    definitions: dict[str, list[_Definition]], file: str, value: object, kind: str, field: str
) -> None:
    """Collect IDs from a list of record-shaped values."""

    for index, record in _enumerate(value):
        if isinstance(record, dict):
            identifier = record.get(field)
            _put(definitions, kind, identifier, file, f"{kind}:{identifier or index}", field)


def _collect_claim_list_definitions(definitions: dict[str, list[_Definition]], file: str, value: object) -> None:
    """Collect claims from entry claims or extra-claim lists."""

    for index, record in _enumerate(value):
        if isinstance(record, dict):
            _put(
                definitions,
                "claim",
                record.get("claim_id"),
                file,
                f"claim:{record.get('claim_id', index)}",
                "claim_id",
            )
            _collect_extra_claims(definitions, file, record.get("extra_claims"))


def _collect_extra_claims(definitions: dict[str, list[_Definition]], file: str, value: object) -> None:
    """Collect nested claims recursively."""

    for index, record in _enumerate(value):
        if isinstance(record, dict):
            identifier = record.get("claim_id")
            _put(definitions, "claim", identifier, file, f"claim:{identifier or index}", "claim_id")
            _collect_extra_claims(definitions, file, record.get("extra_claims"))


def _collect_reveal_definitions(definitions: dict[str, list[_Definition]], file: str, value: object) -> None:
    """Collect reveal, storylet, realization, and nested claim IDs."""

    for index, reveal in _enumerate(value):
        if not isinstance(reveal, dict):
            continue
        reveal_id = reveal.get("id")
        reveal_address = f"reveal:{reveal_id or index}"
        _put(definitions, "reveal", reveal_id, file, reveal_address, "id")
        _put(definitions, "storylet", reveal.get("storylet_id"), file, f"{reveal_address}.storylet_id", "storylet_id")
        variants = _mapping(reveal.get("variants"))
        if variants is None:
            continue
        for variant_key, variant in variants.items():
            if not isinstance(variant, dict):
                continue
            variant_address = f"variant:{reveal_id}/{variant_key}"
            _put(definitions, "realization", variant.get("realization_id"), file, variant_address, "realization_id")
            _put(definitions, "claim", variant.get("claim_id"), file, variant_address, "claim_id")
            _collect_extra_claims(definitions, file, variant.get("extra_claims"))


def _collect_claim_record(definitions: dict[str, list[_Definition]], file: str, value: object) -> None:
    """Collect a single bridge claim and any nested extra claims."""

    record = _mapping(value)
    if record is not None:
        identifier = record.get("claim_id")
        _put(definitions, "claim", identifier, file, f"claim:{identifier}", "claim_id")
        _collect_extra_claims(definitions, file, record.get("extra_claims"))


def _enumerate(value: object) -> list[tuple[int, object]]:
    """Enumerate list values without trusting layer-one shape errors."""

    return list(enumerate(value)) if isinstance(value, list) else []


def _duplicate_diagnostics(definitions: dict[str, list[_Definition]]) -> list[Diagnostic]:
    """Report repeated IDs, leaving fact ownership to its dedicated check."""

    diagnostics: list[Diagnostic] = []
    for key, records in definitions.items():
        kind, identifier = key.split(":", 1)
        if kind == "fact" or len(records) < 2:
            continue
        for record in records[1:]:
            diagnostics.append(
                _diagnostic(
                    "L2.duplicate_id",
                    record.file,
                    record.address,
                    record.field,
                    f"{kind} id {identifier!r} is defined more than once",
                )
            )
    return diagnostics


def _diagnostic(name: str, file: str, address: str, field: str, message: str) -> Diagnostic:
    """Build a diagnostic with the contract's required non-empty location fields."""

    return Diagnostic(name, file, address or "root", field or "id", message)


def _fact_declarations(tree: SourceTree) -> dict[str, list[_Definition]]:
    """Collect scene and catalog fact owners."""

    declarations: dict[str, list[_Definition]] = defaultdict(list)
    for file, data in _scene_files(tree):
        facts = _mapping(data.get("facts"))
        if facts is not None:
            for identifier in facts:
                _put(declarations, "fact", identifier, file, f"fact:{identifier}", str(identifier))
    catalog = _mapping(tree.files.get("catalog.yaml"))
    unplaced = _mapping(catalog.get("unplaced_facts")) if catalog is not None else None
    if unplaced is not None:
        for identifier in unplaced:
            _put(declarations, "fact", identifier, "catalog.yaml", f"fact:{identifier}", str(identifier))
    return declarations


def _fact_owner_diagnostics(declarations: dict[str, list[_Definition]]) -> list[Diagnostic]:
    """Report facts that have more than one declaration owner."""

    diagnostics: list[Diagnostic] = []
    for key, records in declarations.items():
        _, identifier = key.split(":", 1)
        for record in records[1:]:
            diagnostics.append(
                _diagnostic(
                    "L2.fact_one_owner",
                    record.file,
                    record.address,
                    record.field,
                    f"fact {identifier!r} has more than one declaration owner",
                )
            )
    return diagnostics


def _add_facts(
    uses: list[_FactUse], file: str, scene: str | None, address: str, field: str, value: object, kind: str
) -> None:
    """Add fact names from a condition or effects mapping/list."""

    if isinstance(value, list):
        for identifier in value:
            if isinstance(identifier, str):
                uses.append(_FactUse(identifier, file, address, field, scene, kind))
    elif isinstance(value, dict):
        for identifier in value:
            if isinstance(identifier, str):
                uses.append(_FactUse(identifier, file, address, identifier, scene, kind))


def _add_scalar_fact(
    uses: list[_FactUse], file: str, scene: str | None, address: str, field: str, value: object, kind: str
) -> None:
    """Add a fact from a scalar-only contract field."""

    if isinstance(value, str):
        uses.append(_FactUse(value, file, address, field, scene, kind))


def _collect_scene_fact_uses(file: str, data: dict[Any, Any]) -> list[_FactUse]:
    """Collect fact reads and writes from one scene file."""

    scene = _scene_id(data)
    uses: list[_FactUse] = []
    scene_address = f"scene:{scene}" if scene else "scene:unknown"
    for _, addition in _enumerate(data.get("entry_additions")):
        if isinstance(addition, dict):
            _add_facts(uses, file, scene, scene_address, "when", addition.get("when"), "condition")
    for _, beat in _enumerate(data.get("beats")):
        if isinstance(beat, dict):
            address = f"beat:{beat.get('id', 'unknown')}"
            _add_facts(uses, file, scene, address, "when", beat.get("when"), "condition")
            _add_facts(uses, file, scene, address, "sets", beat.get("sets"), "effect")
    for _, reveal in _enumerate(data.get("reveals")):
        uses.extend(_reveal_fact_uses(file, scene, reveal))
    for _, bridge in _enumerate(data.get("bridge")):
        if isinstance(bridge, dict):
            address = f"bridge:{bridge.get('id', 'unknown')}"
            _add_facts(uses, file, scene, address, "when", bridge.get("when"), "condition")
            _add_facts(uses, file, scene, address, "when_any", bridge.get("when_any"), "condition")
            _add_facts(uses, file, scene, address, "commits", bridge.get("commits"), "effect")
            claim = _mapping(bridge.get("claim"))
            if claim is not None:
                _add_facts(
                    uses,
                    file,
                    scene,
                    f"claim:{claim.get('claim_id', 'unknown')}",
                    "commits_subset",
                    claim.get("commits_subset"),
                    "effect",
                )
    exit_record = _mapping(data.get("exit"))
    if exit_record is not None:
        address = f"exit:{exit_record.get('id', 'unknown')}"
        _add_facts(uses, file, scene, address, "when_all", exit_record.get("when_all"), "condition")
    ending = _mapping(data.get("ending"))
    if ending is not None:
        _add_facts(uses, file, scene, "ending:story", "when", ending.get("when"), "condition")
        for _, addition in _enumerate(ending.get("additions")):
            if isinstance(addition, dict):
                _add_facts(uses, file, scene, "ending:story", "when", addition.get("when"), "condition")
    _collect_placement_fact_uses(uses, file, scene, data.get("placements"))
    _collect_scene_fact_declaration_uses(uses, file, scene, data.get("facts"))
    return uses


def _reveal_fact_uses(file: str, scene: str | None, reveal: object) -> list[_FactUse]:
    """Collect fact uses from reveal defaults, variants, and extra claims."""

    record = _mapping(reveal)
    if record is None:
        return []
    reveal_address = f"reveal:{record.get('id', 'unknown')}"
    uses: list[_FactUse] = []
    guidance = _mapping(record.get("guidance"))
    if guidance is not None:
        _add_facts(uses, file, scene, reveal_address, "available_while", guidance.get("available_while"), "condition")
    _add_facts(uses, file, scene, reveal_address, "commits_common", record.get("commits_common"), "effect")
    variants = _mapping(record.get("variants"))
    if variants is None:
        return uses
    for variant_key, variant in variants.items():
        if isinstance(variant, dict):
            address = f"variant:{record.get('id', 'unknown')}/{variant_key}"
            _add_facts(uses, file, scene, address, "when", variant.get("when"), "condition")
            _add_facts(uses, file, scene, address, "commits", variant.get("commits"), "effect")
            _add_facts(uses, file, scene, address, "commits_subset", variant.get("commits_subset"), "effect")
            for _, text_when in _enumerate(variant.get("text_when")):
                if isinstance(text_when, dict):
                    _add_facts(uses, file, scene, address, "when", text_when.get("when"), "condition")
            uses.extend(_extra_claim_fact_uses(file, scene, address, variant.get("extra_claims")))
    return uses


def _extra_claim_fact_uses(file: str, scene: str | None, parent: str, value: object) -> list[_FactUse]:
    """Collect fact effects from nested extra claims."""

    uses: list[_FactUse] = []
    for _, claim in _enumerate(value):
        if isinstance(claim, dict):
            address = f"claim:{claim.get('claim_id', parent)}"
            _add_facts(uses, file, scene, address, "commits_subset", claim.get("commits_subset"), "effect")
            uses.extend(_extra_claim_fact_uses(file, scene, address, claim.get("extra_claims")))
    return uses


def _collect_placement_fact_uses(uses: list[_FactUse], file: str, scene: str | None, value: object) -> None:
    """Collect reads from the supported legacy conditional placement form."""

    placements = _mapping(value)
    if placements is None:
        return
    for identifier, placement in placements.items():
        record = _mapping(placement)
        if record is None:
            continue
        address = f"entity:{identifier}"
        _add_scalar_fact(uses, file, scene, address, "while_fact_true", record.get("while_fact_true"), "condition")
        _add_scalar_fact(uses, file, scene, address, "while_fact_false", record.get("while_fact_false"), "condition")


def _collect_scene_fact_declaration_uses(uses: list[_FactUse], file: str, scene: str | None, value: object) -> None:
    """Collect fact delivery costs, which are fact effects."""

    facts = _mapping(value)
    if facts is None:
        return
    for identifier, declaration in facts.items():
        record = _mapping(declaration)
        delivery = _mapping(record.get("delivery")) if record is not None else None
        if delivery is not None:
            _add_facts(uses, file, scene, f"delivery:{identifier}", "costs", delivery.get("costs"), "effect")


def _catalog_fact_uses(tree: SourceTree) -> list[_FactUse]:
    """Collect catalog fact references that participate in cross-record rules."""

    catalog = _mapping(tree.files.get("catalog.yaml"))
    if catalog is None:
        return []
    uses: list[_FactUse] = []
    guards = _mapping(catalog.get("disclosure_guards"))
    if guards is not None:
        for identifier, guard in guards.items():
            record = _mapping(guard)
            if record is not None:
                _add_fact_ref(uses, record.get("unlock_fact"), "catalog.yaml", f"entity:{identifier}", "unlock_fact")
    connections = _mapping(catalog.get("connections"))
    if connections is not None:
        for identifier, connection in connections.items():
            record = _mapping(connection)
            if record is not None:
                _add_fact_ref(uses, record.get("access_fact"), "catalog.yaml", f"entity:{identifier}", "access_fact")
    return uses


def _add_fact_ref(uses: list[_FactUse], identifier: object, file: str, address: str, field: str) -> None:
    """Add one scalar fact reference from a catalog record."""

    if isinstance(identifier, str):
        uses.append(_FactUse(identifier, file, address, field, None, "reference"))


def _all_fact_uses(tree: SourceTree) -> list[_FactUse]:
    """Collect fact uses from scene and catalog records."""

    uses = _catalog_fact_uses(tree)
    for file, data in _scene_files(tree):
        uses.extend(_collect_scene_fact_uses(file, data))
    for file, value in sorted(tree.files.items()):
        if not _MATCH_FILE.fullmatch(file):
            continue
        document = _mapping(value)
        deliveries = _mapping(document.get("deliveries")) if document is not None else None
        if deliveries is not None:
            for identifier in deliveries:
                if isinstance(identifier, str):
                    uses.append(_FactUse(identifier, file, f"delivery:{identifier}", identifier, None, "reference"))
    return uses


def _fact_reference_diagnostics(tree: SourceTree, declarations: dict[str, list[_Definition]]) -> list[Diagnostic]:
    """Report unresolved fact references, with condition/effect split by contract fixture behavior."""

    declared = {key.split(":", 1)[1] for key in declarations}
    diagnostics: list[Diagnostic] = []
    for use in _all_fact_uses(tree):
        if use.identifier in declared:
            continue
        name = "L2.dangling_ref" if use.kind in {"condition", "reference"} else "L2.undeclared_fact"
        diagnostics.append(
            _diagnostic(name, use.file, use.address, use.field, f"fact {use.identifier!r} is not declared")
        )
    return diagnostics


def _scene_order(tree: SourceTree, scenes: list[tuple[str, dict[Any, Any]]]) -> dict[str, int]:
    """Build the canonical scene order from story.yaml, with safe fallbacks."""

    story = _mapping(tree.files.get("story.yaml"))
    ordered = story.get("scenes") if story is not None else None
    names = [item for item in ordered if isinstance(item, str)] if isinstance(ordered, list) else []
    result = {name: index for index, name in enumerate(names)}
    for _file, data in scenes:
        identifier = _scene_id(data)
        if identifier is not None and identifier not in result:
            result[identifier] = len(result)
    return result


def _declaring_scene_diagnostics(tree: SourceTree, declarations: dict[str, list[_Definition]]) -> list[Diagnostic]:
    """Ensure each scene-owned fact is declared at its first setting or reading scene."""

    scenes = _scene_files(tree)
    order = _scene_order(tree, scenes)
    uses = _all_fact_uses(tree)
    by_fact: dict[str, list[_FactUse]] = defaultdict(list)
    for use in uses:
        by_fact[use.identifier].append(use)
    diagnostics: list[Diagnostic] = []
    for key, owners in declarations.items():
        identifier = key.split(":", 1)[1]
        if len(owners) != 1 or owners[0].file == "catalog.yaml":
            continue
        target = _first_scene(by_fact.get(identifier, []), order, "effect")
        if target is None:
            target = _first_scene(by_fact.get(identifier, []), order, "condition")
        if target is None or target == _scene_from_file(owners[0].file, scenes):
            continue
        owner = owners[0]
        diagnostics.append(
            _diagnostic(
                "L2.fact_declaring_scene",
                owner.file,
                owner.address,
                owner.field,
                f"fact {identifier!r} is declared in the facts block of {owner.file}; move it to scenes/{target}.yaml",
            )
        )
    return diagnostics


def _first_scene(uses: list[_FactUse], order: dict[str, int], kind: str) -> str | None:
    """Return the earliest scene containing a fact use of the requested kind."""

    candidates = {use.scene for use in uses if use.kind == kind and use.scene is not None}
    return min(candidates, key=lambda scene: order.get(scene, 10**6)) if candidates else None


def _scene_from_file(file: str, scenes: list[tuple[str, dict[Any, Any]]]) -> str | None:
    """Resolve a scene ID from a scene filename/document pair."""

    for candidate, data in scenes:
        if candidate == file:
            return _scene_id(data)
    return None


def _unplaced_diagnostics(tree: SourceTree, declarations: dict[str, list[_Definition]]) -> list[Diagnostic]:
    """Report catalog unplaced facts that have any read or write."""

    uses = _all_fact_uses(tree)
    used = {use.identifier for use in uses}
    diagnostics: list[Diagnostic] = []
    for key, owners in declarations.items():
        identifier = key.split(":", 1)[1]
        if any(owner.file == "catalog.yaml" for owner in owners) and identifier in used:
            owner = next(owner for owner in owners if owner.file == "catalog.yaml")
            diagnostics.append(
                _diagnostic(
                    "L2.unplaced_fact",
                    owner.file,
                    owner.address,
                    owner.field,
                    f"unplaced fact {identifier!r} is read or set by the story",
                )
            )
    return diagnostics


def _add_reference(
    references: list[_Reference], identifier: object, file: str, address: str, field: str, kind: str
) -> None:
    """Add a typed reference when its authored value is a string."""

    if isinstance(identifier, str):
        references.append(_Reference(identifier, file, address, field, kind))


def _add_string_refs(
    references: list[_Reference], value: object, file: str, address: str, field: str, kind: str
) -> None:
    """Add references from a list of string IDs."""

    if isinstance(value, list):
        for identifier in value:
            _add_reference(references, identifier, file, address, field, kind)


def _collect_scene_references(file: str, data: dict[Any, Any]) -> list[_Reference]:
    """Collect scene-level references to facts, records, entities, and passages."""

    references: list[_Reference] = []
    scene = _scene_id(data)
    scene_address = f"scene:{scene or 'unknown'}"
    _add_reference(references, data.get("location"), file, scene_address, "location", "entity")
    for field in _SCENE_REF_FIELDS:
        _add_string_refs(references, data.get(field), file, scene_address, field, "entity")
    _collect_claim_references(references, file, data.get("entry_claims"))
    _collect_placement_references(references, file, data.get("placements"))
    _collect_outline_references(references, file, data.get("outline"))
    _collect_beats_and_exit_references(references, file, data)
    _collect_reveal_references(references, file, data.get("reveals"))
    _collect_incident_references(references, file, data.get("incidents"))
    _collect_bridge_references(references, file, data.get("bridge"))
    return references


def _collect_claim_references(references: list[_Reference], file: str, value: object) -> None:
    """Collect entity IDs from entry and nested claim records."""

    for _, claim in _enumerate(value):
        if isinstance(claim, dict):
            address = f"claim:{claim.get('claim_id', 'unknown')}"
            _add_string_refs(references, claim.get("entities"), file, address, "entities", "entity")
            _collect_claim_references(references, file, claim.get("extra_claims"))


def _collect_placement_references(references: list[_Reference], file: str, value: object) -> None:
    """Collect placement entity keys and parents."""

    placements = _mapping(value)
    if placements is None:
        return
    for identifier, placement in placements.items():
        address = f"entity:{identifier}"
        _add_reference(references, identifier, file, address, "id", "entity")
        record = _mapping(placement)
        if record is not None:
            _add_reference(references, record.get("parent"), file, address, "parent", "entity")


def _collect_outline_references(references: list[_Reference], file: str, value: object) -> None:
    """Collect outline IDs from outline-bearing records."""

    for _, outline in _enumerate(value):
        if isinstance(outline, dict):
            _add_reference(
                references,
                outline.get("id"),
                file,
                f"outline:{outline.get('id', 'unknown')}",
                "id",
                "outline",
            )


def _collect_beats_and_exit_references(references: list[_Reference], file: str, data: dict[Any, Any]) -> None:
    """Collect exit and beat references from one scene."""

    for _, beat in _enumerate(data.get("beats")):
        if isinstance(beat, dict):
            _add_reference(references, beat.get("exit"), file, f"beat:{beat.get('id', 'unknown')}", "exit", "exit")
    exit_record = _mapping(data.get("exit"))
    if exit_record is not None:
        address = f"exit:{exit_record.get('id', 'unknown')}"
        _add_reference(references, exit_record.get("to"), file, address, "to", "scene")
        _collect_needs_references(references, file, address, exit_record.get("needs"))


def _collect_needs_references(references: list[_Reference], file: str, address: str, value: object) -> None:
    """Collect item and holder entity IDs from typed needs."""

    for _, need in _enumerate(value):
        if isinstance(need, dict):
            _add_reference(references, need.get("item"), file, address, "item", "entity")
            _add_reference(references, need.get("holder"), file, address, "holder", "entity")


def _collect_reveal_references(references: list[_Reference], file: str, value: object) -> None:
    """Collect references inside reveal records and their variants."""

    for _, reveal in _enumerate(value):
        if not isinstance(reveal, dict):
            continue
        reveal_address = f"reveal:{reveal.get('id', 'unknown')}"
        _add_string_refs(references, reveal.get("from_outline"), file, reveal_address, "from_outline", "outline")
        _add_string_refs(references, reveal.get("entities"), file, reveal_address, "entities", "entity")
        _add_string_refs(references, reveal.get("reach"), file, reveal_address, "reach", "entity")
        relevance = _mapping(reveal.get("relevance"))
        if relevance is not None:
            _add_string_refs(references, relevance.get("entity_ids"), file, reveal_address, "entity_ids", "entity")
        _collect_needs_references(references, file, reveal_address, reveal.get("needs"))
        _collect_parts(references, file, reveal)
        variants = _mapping(reveal.get("variants"))
        if variants is not None:
            for variant_key, variant in variants.items():
                if not isinstance(variant, dict):
                    continue
                address = f"variant:{reveal.get('id', 'unknown')}/{variant_key}"
                _add_string_refs(references, variant.get("from_outline"), file, address, "from_outline", "outline")
                _add_string_refs(references, variant.get("entities"), file, address, "entities", "entity")
                _add_string_refs(references, variant.get("reach"), file, address, "reach", "entity")
                relevance = _mapping(variant.get("relevance"))
                if relevance is not None:
                    _add_string_refs(references, relevance.get("entity_ids"), file, address, "entity_ids", "entity")
                _collect_claim_references(references, file, variant.get("extra_claims"))


def _collect_parts(references: list[_Reference], file: str, reveal: dict[Any, Any]) -> None:
    """Check every authored part placeholder against its reveal's parts map."""

    parts = _mapping(reveal.get("parts")) or {}
    variants = _mapping(reveal.get("variants"))
    if variants is None:
        return
    for variant_key, variant in variants.items():
        if not isinstance(variant, dict):
            continue
        address = f"variant:{reveal.get('id', 'unknown')}/{variant_key}"
        for field in ("text",):
            _part_references(references, file, address, field, variant.get(field), parts)
        for index, entry in _enumerate(variant.get("text_when")):
            if isinstance(entry, dict):
                _part_references(references, file, f"{address}.text_when[{index}]", "text", entry.get("text"), parts)
        speaker_text = _mapping(variant.get("speaker_text"))
        if speaker_text is not None:
            for speaker, text in speaker_text.items():
                _part_references(references, file, f"{address}.speaker_text.{speaker}", "speaker_text", text, parts)


def _part_references(
    references: list[_Reference], file: str, address: str, field: str, value: object, parts: dict[Any, Any]
) -> None:
    """Add missing part placeholders found in one passage."""

    if not isinstance(value, str):
        return
    for match in _PART.finditer(value):
        name = match.group(1)
        if name not in parts:
            references.append(_Reference(name, file, address, field, "part"))


def _collect_incident_references(references: list[_Reference], file: str, value: object) -> None:
    """Collect references from incident routing records."""

    for _, incident in _enumerate(value):
        if not isinstance(incident, dict):
            continue
        address = f"incident:{incident.get('id', 'unknown')}"
        _add_reference(references, incident.get("reveal"), file, address, "reveal", "reveal")
        _add_reference(references, incident.get("recovery"), file, address, "recovery", "reveal")
        _add_reference(references, incident.get("missed_window"), file, address, "missed_window", "beat")
        _add_reference(references, incident.get("successor"), file, address, "successor", "exit")
        _add_string_refs(references, incident.get("observed_by"), file, address, "observed_by", "claim")
        _add_outcome_variant_references(references, file, address, incident.get("outcomes"), incident.get("reveal"))


def _add_outcome_variant_references(
    references: list[_Reference], file: str, address: str, outcomes: object, reveal: object
) -> None:
    """Validate incident outcome variant keys against the named reveal later."""

    if not isinstance(outcomes, list) or not isinstance(reveal, str):
        return
    for outcome in outcomes:
        if isinstance(outcome, str):
            references.append(_Reference(f"{reveal}/{outcome}", file, address, "outcomes", "variant"))


def _collect_bridge_references(references: list[_Reference], file: str, value: object) -> None:
    """Collect reveal and claim references from bridge records."""

    for _, bridge in _enumerate(value):
        if not isinstance(bridge, dict):
            continue
        address = f"bridge:{bridge.get('id', 'unknown')}"
        _add_string_refs(references, bridge.get("realized_by"), file, address, "realized_by", "reveal")
        claim = _mapping(bridge.get("claim"))
        if claim is not None:
            _add_reference(references, claim.get("claim_id"), file, address, "claim_id", "claim")


def _catalog_references(tree: SourceTree) -> list[_Reference]:
    """Collect story and catalog entity/claim references."""

    references: list[_Reference] = []
    story = _mapping(tree.files.get("story.yaml"))
    if story is not None:
        _add_reference(references, story.get("protagonist"), "story.yaml", "scene:story", "protagonist", "entity")
        _add_string_refs(
            references,
            story.get("principal_characters"),
            "story.yaml",
            "scene:story",
            "principal_characters",
            "entity",
        )
    catalog = _mapping(tree.files.get("catalog.yaml"))
    if catalog is None:
        return references
    for section in ("places", "characters", "groups", "items"):
        records = _mapping(catalog.get(section))
        if records is None:
            continue
        for identifier, record in records.items():
            if not isinstance(record, dict):
                continue
            address = f"entity:{identifier}"
            for field in ("parent", "owner", "seat_for", "fallback_ids"):
                _add_string_refs(references, record.get(field), "catalog.yaml", address, field, "entity")
    guards = _mapping(catalog.get("disclosure_guards"))
    if guards is not None:
        for identifier, guard in guards.items():
            if isinstance(guard, dict):
                _add_reference(
                    references,
                    guard.get("unlock_claim"),
                    "catalog.yaml",
                    f"entity:{identifier}",
                    "unlock_claim",
                    "claim",
                )
    return references


def _match_references(tree: SourceTree) -> list[_Reference]:
    """Collect shared matcher and placeholder references from match files."""

    references: list[_Reference] = []
    for file, value in sorted(tree.files.items()):
        if not _MATCH_FILE.fullmatch(file):
            continue
        document = _mapping(value)
        if document is None:
            continue
        shared = _mapping(document.get("shared")) or {}
        claims = _mapping(document.get("claims"))
        if claims is not None:
            for identifier, claim in claims.items():
                if isinstance(claim, dict) and isinstance(claim.get("use"), str) and claim["use"] not in shared:
                    references.append(_Reference(claim["use"], file, f"claim:{identifier}", "use", "shared"))
    return references


def _reference_sets(tree: SourceTree, definitions: dict[str, list[_Definition]]) -> dict[str, set[str]]:
    """Build the resolved ID sets used by the generic reference pass."""

    sets: dict[str, set[str]] = defaultdict(set)
    for key in definitions:
        kind, identifier = key.split(":", 1)
        sets[kind].add(identifier)
    sets["scene"] = {scene for _, data in _scene_files(tree) if (scene := _scene_id(data)) is not None}
    sets["fact"] = {key.split(":", 1)[1] for key in _fact_declarations(tree)}
    for _, data in _scene_files(tree):
        for _, reveal in _enumerate(data.get("reveals")):
            if not isinstance(reveal, dict):
                continue
            reveal_id = reveal.get("id")
            variants = _mapping(reveal.get("variants"))
            if isinstance(reveal_id, str) and variants is not None:
                sets["variant"].update(
                    f"{reveal_id}/{variant_key}" for variant_key in variants if isinstance(variant_key, str)
                )
    return sets


def _reference_diagnostics(tree: SourceTree, definitions: dict[str, list[_Definition]]) -> list[Diagnostic]:
    """Report unresolved record, part, target-scene, and matcher references."""

    references: list[_Reference] = _catalog_references(tree)
    for file, data in _scene_files(tree):
        references.extend(_collect_scene_references(file, data))
    references.extend(_match_references(tree))
    resolved = _reference_sets(tree, definitions)
    diagnostics: list[Diagnostic] = []
    for reference in references:
        valid = False if reference.kind == "part" else reference.identifier in resolved.get(reference.kind, set())
        if not valid:
            diagnostics.append(
                _diagnostic(
                    "L2.dangling_ref",
                    reference.file,
                    reference.address,
                    reference.field,
                    f"{reference.kind} reference {reference.identifier!r} does not resolve",
                )
            )
    return diagnostics


@layer2_check
def check_facts_and_references(tree: SourceTree) -> list[Diagnostic]:
    """Run the story-wide ID, reference, and fact-placement checks."""

    definitions = _collect_definitions(tree)
    declarations = _fact_declarations(tree)
    diagnostics = _duplicate_diagnostics(definitions)
    diagnostics.extend(_reference_diagnostics(tree, definitions))
    diagnostics.extend(_fact_owner_diagnostics(declarations))
    diagnostics.extend(_declaring_scene_diagnostics(tree, declarations))
    diagnostics.extend(_unplaced_diagnostics(tree, declarations))
    diagnostics.extend(_fact_reference_diagnostics(tree, declarations))
    return diagnostics

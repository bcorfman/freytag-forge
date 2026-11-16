"""Layer-two checks for claims, matcher coverage, and scene ownership rules."""

from __future__ import annotations

import re
from collections.abc import Iterator
from typing import Any

from .checks import layer2_check
from .diagnostics import Diagnostic
from .reader import SourceTree

_SCENE_FILE = re.compile(r"scenes/([^/.]+)\.yaml$")
_MATCH_FILE = re.compile(r"scenes/([^/.]+)\.match\.yaml$")
_SOURCE_FILES = {"story.yaml", "catalog.yaml", "lexicon.yaml", "ownership.yaml"}


def _mapping(value: object) -> dict[Any, Any] | None:
    """Return mappings only, allowing malformed layer-one values to be skipped."""

    return value if isinstance(value, dict) else None


def _scene_files(tree: SourceTree) -> Iterator[tuple[str, str, dict[Any, Any]]]:
    """Yield parsed declarative scene files with their scene ids."""

    for file, value in sorted(tree.files.items()):
        match = _SCENE_FILE.fullmatch(file)
        record = _mapping(value)
        if match and record is not None and not _MATCH_FILE.fullmatch(file):
            scene_id = record.get("scene")
            if isinstance(scene_id, str):
                yield file, scene_id, record


def _diagnostic(name: str, file: str, address: str, field: str, message: str) -> Diagnostic:
    """Construct a diagnostic with a section-8-compatible non-empty address."""

    return Diagnostic(name, file, address or "root", field or "root", message)


def _claim_record(record: object) -> tuple[str, dict[Any, Any]] | None:
    """Return a claim id and mapping when a claim record is usable."""

    claim = _mapping(record)
    claim_id = claim.get("claim_id") if claim is not None else None
    return (claim_id, claim) if isinstance(claim_id, str) else None


def _extra_claims(record: object) -> Iterator[dict[Any, Any]]:
    """Yield a claim and any nested extra claims without trusting their shape."""

    claim = _mapping(record)
    if claim is None:
        return
    yield claim
    extras = claim.get("extra_claims")
    if isinstance(extras, list):
        for extra in extras:
            yield from _extra_claims(extra)


def _scene_claims(record: dict[Any, Any]) -> Iterator[tuple[str, dict[Any, Any]]]:
    """Yield every claim defined by one scene, including entry and bridge claims."""

    entry_claims = record.get("entry_claims")
    if isinstance(entry_claims, list):
        for entry in entry_claims:
            claim = _claim_record(entry)
            if claim is not None:
                yield claim

    reveals = record.get("reveals")
    if isinstance(reveals, list):
        for reveal in reveals:
            reveal_record = _mapping(reveal)
            variants = reveal_record.get("variants") if reveal_record is not None else None
            if not isinstance(variants, dict):
                continue
            for variant in variants.values():
                for claim in _extra_claims(variant):
                    found = _claim_record(claim)
                    if found is not None:
                        yield found

    bridges = record.get("bridge")
    if isinstance(bridges, list):
        for bridge in bridges:
            bridge_record = _mapping(bridge)
            if bridge_record is not None:
                claim = _claim_record(bridge_record.get("claim"))
                if claim is not None:
                    yield claim


def _reveal_variants(
    record: dict[Any, Any],
) -> Iterator[tuple[str, str, dict[Any, Any], dict[Any, Any]]]:
    """Yield reveal id, reveal record, and each variant record."""

    reveals = record.get("reveals")
    if not isinstance(reveals, list):
        return
    for reveal in reveals:
        reveal_record = _mapping(reveal)
        reveal_id = reveal_record.get("id") if reveal_record is not None else None
        variants = reveal_record.get("variants") if reveal_record is not None else None
        if not isinstance(reveal_id, str) or not isinstance(variants, dict):
            continue
        for variant_key, variant in variants.items():
            variant_record = _mapping(variant)
            if isinstance(variant_key, str) and variant_record is not None:
                yield reveal_id, variant_key, reveal_record, variant_record


def _compiled_commits(reveal: dict[Any, Any], variant: dict[Any, Any]) -> dict[Any, Any] | None:
    """Merge reveal-wide and variant commits in the contract's precedence order."""

    common = reveal.get("commits_common", {})
    commits = variant.get("commits")
    if not isinstance(common, dict) or not isinstance(commits, dict):
        return None
    result = dict(common)
    result.update(commits)
    return result


def _claim_authorized(tree: SourceTree) -> list[Diagnostic]:
    """Check that every written claim subset is authorized by its source."""

    diagnostics: list[Diagnostic] = []
    for file, _, scene in _scene_files(tree):
        for _reveal_id, _variant_key, reveal, variant in _reveal_variants(scene):
            commits = _compiled_commits(reveal, variant)
            if commits is None:
                continue
            claim_id = variant.get("claim_id")
            if isinstance(claim_id, str):
                diagnostics.extend(_authorized_diagnostic(file, claim_id, variant.get("commits_subset"), commits))
            extras = variant.get("extra_claims")
            if isinstance(extras, list):
                for extra in extras:
                    for claim in _extra_claims(extra):
                        extra_id = claim.get("claim_id")
                        if isinstance(extra_id, str):
                            diagnostics.extend(
                                _authorized_diagnostic(file, extra_id, claim.get("commits_subset"), commits)
                            )
        bridges = scene.get("bridge")
        if isinstance(bridges, list):
            for bridge in bridges:
                bridge_record = _mapping(bridge)
                if bridge_record is None or not isinstance(bridge_record.get("commits"), dict):
                    continue
                claim = _mapping(bridge_record.get("claim"))
                claim_id = claim.get("claim_id") if claim is not None else None
                if isinstance(claim_id, str) and claim is not None:
                    diagnostics.extend(
                        _authorized_diagnostic(file, claim_id, claim.get("commits_subset"), bridge_record["commits"])
                    )
    return diagnostics


def _authorized_diagnostic(file: str, claim_id: str, subset: object, commits: dict[Any, Any]) -> list[Diagnostic]:
    """Return one authorization diagnostic when a subset is not contained."""

    if not isinstance(subset, dict):
        return []
    if all(key in commits and commits[key] == value for key, value in subset.items()):
        return []
    return [
        _diagnostic(
            "L2.claim_authorized",
            file,
            f"claim:{claim_id}",
            "commits_subset",
            f"claim {claim_id!r} establishes a fact outside its source commits",
        )
    ]


def _override_add_only(tree: SourceTree) -> list[Diagnostic]:
    """Reject non-additive matcher overrides and variant-level boundaries."""

    diagnostics: list[Diagnostic] = []
    for file, _, match in _match_files(tree):
        shared = _mapping(match.get("shared")) or {}
        claims = _mapping(match.get("claims")) or {}
        for claim_id, claim in claims.items():
            if not isinstance(claim_id, str) or not isinstance(claim, dict):
                continue
            override = claim.get("leak_terms")
            shared_name = claim.get("use")
            shared_record = _mapping(shared.get(shared_name)) if isinstance(shared_name, str) else None
            has_shared_leaks = "leak_terms" in shared or (shared_record is not None and "leak_terms" in shared_record)
            if has_shared_leaks and "leak_terms" in claim and not _add_mapping(override):
                diagnostics.append(
                    _diagnostic(
                        "L2.override_add_only",
                        file,
                        f"claim:{claim_id}.leak_terms",
                        "leak_terms",
                        f"claim {claim_id!r} must override shared leak_terms with {{add: [...]}}",
                    )
                )

    for file, _, scene in _scene_files(tree):
        for reveal_id, variant_key, _, variant in _reveal_variants(scene):
            if "boundaries" in variant:
                diagnostics.append(
                    _diagnostic(
                        "L2.override_add_only",
                        file,
                        f"variant:{reveal_id}/{variant_key}",
                        "boundaries",
                        f"variant {reveal_id!r} cannot define reveal-level boundaries",
                    )
                )
    return diagnostics


def _add_mapping(value: object) -> bool:
    """Recognize the only legal additive override shape."""

    return isinstance(value, dict) and set(value) == {"add"} and isinstance(value["add"], list)


def _match_files(tree: SourceTree) -> Iterator[tuple[str, str, dict[Any, Any]]]:
    """Yield parsed match files with their declared scene ids."""

    for file, value in sorted(tree.files.items()):
        match = _MATCH_FILE.fullmatch(file)
        record = _mapping(value)
        scene_id = record.get("scene") if record is not None else None
        if match and record is not None and isinstance(scene_id, str):
            yield file, scene_id, record


def _match_coverage(tree: SourceTree) -> list[Diagnostic]:
    """Require exact claim and delivery coverage in each scene match file."""

    diagnostics: list[Diagnostic] = []
    matches = {scene_id: (file, record) for file, scene_id, record in _match_files(tree)}
    for scene_file, scene_id, scene in _scene_files(tree):
        match_file, match = matches.get(scene_id, (f"scenes/{scene_id}.match.yaml", {}))
        match_claims = _mapping(match.get("claims")) or {}
        source_claims = {claim_id for claim_id, _ in _scene_claims(scene)}
        for claim_id in sorted(source_claims - set(match_claims)):
            diagnostics.append(
                _diagnostic(
                    "L2.match_coverage",
                    scene_file,
                    f"claim:{claim_id}",
                    "claims",
                    f"claim {claim_id!r} has no match entry in {match_file}",
                )
            )
        for claim_id in sorted(set(match_claims) - source_claims):
            if not isinstance(claim_id, str):
                continue
            diagnostics.append(
                _diagnostic(
                    "L2.match_coverage",
                    match_file,
                    f"claim:{claim_id}",
                    "claims",
                    f"match entry {claim_id!r} has no scene claim",
                )
            )
        diagnostics.extend(_delivery_coverage(tree, scene_file, scene_id, scene, matches))
    return diagnostics


def _delivery_coverage(
    tree: SourceTree,
    scene_file: str,
    scene_id: str,
    scene: dict[Any, Any],
    matches: dict[str, tuple[str, dict[Any, Any]]],
) -> list[Diagnostic]:
    """Check delivery records against the match file selected by their scene."""

    diagnostics: list[Diagnostic] = []
    facts = scene.get("facts")
    if not isinstance(facts, dict):
        return diagnostics
    for fact_id, declaration in facts.items():
        fact = _mapping(declaration)
        delivery = fact.get("delivery") if fact is not None else None
        delivery_record = _mapping(delivery)
        if not isinstance(fact_id, str) or delivery_record is None:
            continue
        target_scene = delivery_record.get("scene", scene_id)
        target = matches.get(target_scene) if isinstance(target_scene, str) else None
        target_file, target_match = target if target is not None else (f"scenes/{target_scene}.match.yaml", {})
        deliveries = _mapping(target_match.get("deliveries")) or {}
        if fact_id not in deliveries:
            diagnostics.append(
                _diagnostic(
                    "L2.match_coverage",
                    scene_file,
                    f"delivery:{fact_id}",
                    "deliveries",
                    f"delivery {fact_id!r} has no match entry in {target_file}",
                )
            )
    return diagnostics


def _incident_observations(tree: SourceTree) -> list[Diagnostic]:
    """Require each incident outcome claim in its observed-by list."""

    diagnostics: list[Diagnostic] = []
    for file, _, scene in _scene_files(tree):
        reveals = {
            reveal_id: reveal
            for reveal_id, _variant_key, reveal, _variant in _reveal_variants(scene)
            if isinstance(reveal_id, str)
        }
        incidents = scene.get("incidents")
        if not isinstance(incidents, list):
            continue
        for incident in incidents:
            record = _mapping(incident)
            if record is None:
                continue
            reveal_id = record.get("reveal")
            reveal = reveals.get(reveal_id) if isinstance(reveal_id, str) else None
            outcomes = record.get("outcomes")
            observed = record.get("observed_by")
            if reveal is None or not isinstance(outcomes, list) or not isinstance(observed, list):
                continue
            variants = _mapping(reveal.get("variants"))
            if variants is None:
                continue
            incident_id = record.get("id", "unknown")
            for outcome in outcomes:
                if not isinstance(outcome, str):
                    continue
                variant = _mapping(variants.get(outcome))
                claim_id = variant.get("claim_id") if variant is not None else None
                if isinstance(claim_id, str) and claim_id not in observed:
                    diagnostics.append(
                        _diagnostic(
                            "L2.incident_observes_outcomes",
                            file,
                            f"incident:{incident_id}",
                            "observed_by",
                            f"incident {incident_id!r} does not observe outcome claim {claim_id!r}",
                        )
                    )
    return diagnostics


def _scene_scope(tree: SourceTree) -> list[Diagnostic]:
    """Keep reveal dependencies and exit helpers within their scene scope."""

    diagnostics: list[Diagnostic] = []
    exits = _exit_owners(tree)
    for file, scene_id, scene in _scene_files(tree):
        available = _scene_items(scene)
        seen_reveals: set[str] = set()
        for reveal_id, variant_key, reveal, variant in _reveal_variants(scene):
            if reveal_id not in seen_reveals:
                diagnostics.extend(
                    _scope_exit_refs(file, scene_id, reveal_id, reveal.get("helps_exit"), exits, "helps_exit")
                )
                diagnostics.extend(_scope_items(file, reveal_id, reveal.get("reach"), available, "reach"))
                diagnostics.extend(_scope_needs(file, f"reveal:{reveal_id}.needs", reveal.get("needs"), available))
                seen_reveals.add(reveal_id)
            diagnostics.extend(
                _scope_exit_refs(file, scene_id, reveal_id, variant.get("helps_exit"), exits, "helps_exit", variant_key)
            )
            if not isinstance(variant.get("claim_id"), str):
                diagnostics.extend(_scope_items(file, reveal_id, variant.get("reach"), available, "reach", variant_key))
        for claim_id, claim in _scene_claims(scene):
            diagnostics.extend(_scope_items(file, claim_id, claim.get("reach"), available, "reach"))
        exit_record = _mapping(scene.get("exit"))
        if exit_record is not None:
            diagnostics.extend(
                _scope_needs(
                    file, f"exit:{exit_record.get('id', 'unknown')}.needs", exit_record.get("needs"), available
                )
            )
        for incident in scene.get("incidents", []) if isinstance(scene.get("incidents"), list) else []:
            incident_record = _mapping(incident)
            if incident_record is None:
                continue
            successor = incident_record.get("successor")
            if isinstance(successor, str) and successor in exits and exits[successor] != scene_id:
                diagnostics.append(
                    _diagnostic(
                        "L2.scene_scope",
                        file,
                        f"incident:{incident_record.get('id', 'unknown')}",
                        "successor",
                        f"successor {successor!r} belongs to scene {exits[successor]!r}, not {scene_id!r}",
                    )
                )
    return diagnostics


def _exit_owners(tree: SourceTree) -> dict[str, str]:
    """Map known exit ids to the scene that defines them."""

    owners: dict[str, str] = {}
    for _, scene_id, scene in _scene_files(tree):
        exit_record = _mapping(scene.get("exit"))
        exit_id = exit_record.get("id") if exit_record is not None else None
        if isinstance(exit_id, str):
            owners[exit_id] = scene_id
    return owners


def _scene_items(scene: dict[Any, Any]) -> set[str]:
    """Return only explicitly declared scene items and participants."""

    available: set[str] = set()
    for field in ("items", "participants"):
        values = scene.get(field)
        if isinstance(values, list):
            available.update(item for item in values if isinstance(item, str))
    return available


def _scope_exit_refs(
    file: str,
    scene_id: str,
    reveal_id: str,
    value: object,
    exits: dict[str, str],
    field: str,
    variant_key: str | None = None,
) -> list[Diagnostic]:
    """Report known exit references owned by another scene."""

    if not isinstance(value, list):
        return []
    address = f"variant:{reveal_id}/{variant_key}" if variant_key else f"reveal:{reveal_id}"
    return [
        _diagnostic(
            "L2.scene_scope",
            file,
            address,
            field,
            f"{field} reference {exit_id!r} names scene {exits[exit_id]!r}, not {scene_id!r}",
        )
        for exit_id in value
        if isinstance(exit_id, str) and exit_id in exits and exits[exit_id] != scene_id
    ]


def _scope_items(
    file: str,
    reveal_id: str,
    value: object,
    available: set[str],
    field: str,
    variant_key: str | None = None,
) -> list[Diagnostic]:
    """Report reach entities that are not in the scene's explicit scope."""

    if not isinstance(value, list):
        return []
    address = f"variant:{reveal_id}/{variant_key}" if variant_key else f"reveal:{reveal_id}"
    return [
        _diagnostic(
            "L2.scene_scope",
            file,
            address,
            field,
            f"{field} item {item!r} is absent from this scene's items and participants",
        )
        for item in value
        if isinstance(item, str) and item not in available
    ]


def _scope_needs(file: str, address: str, value: object, available: set[str]) -> list[Diagnostic]:
    """Report typed needs whose item is outside the explicit scene scope."""

    if not isinstance(value, list):
        return []
    diagnostics: list[Diagnostic] = []
    for relation in value:
        relation_record = _mapping(relation)
        item = relation_record.get("item") if relation_record is not None else None
        if isinstance(item, str) and item not in available:
            diagnostics.append(
                _diagnostic(
                    "L2.scene_scope",
                    file,
                    address,
                    "needs",
                    f"needs item {item!r} is absent from this scene's items and participants",
                )
            )
    return diagnostics


def _ending_scene(tree: SourceTree) -> list[Diagnostic]:
    """Require an ending only in the last story scene."""

    story = _mapping(tree.files.get("story.yaml"))
    scenes = story.get("scenes") if story is not None else None
    if not isinstance(scenes, list) or not scenes or not all(isinstance(scene, str) for scene in scenes):
        return []
    last_scene = scenes[-1]
    diagnostics: list[Diagnostic] = []
    for file, scene_id, scene in _scene_files(tree):
        if "ending" in scene and scene_id != last_scene:
            diagnostics.append(
                _diagnostic(
                    "L2.ending_scene",
                    file,
                    "ending:story",
                    "ending",
                    f"ending belongs to scene {scene_id!r}, but the last story scene is {last_scene!r}",
                )
            )
    return diagnostics


def _ownership(tree: SourceTree) -> list[Diagnostic]:
    """Reject manifest ownership conflicts with source files or legacy records."""

    manifest = _mapping(tree.files.get("ownership.yaml"))
    if manifest is None:
        return []
    diagnostics: list[Diagnostic] = []
    scene_owners = _mapping(manifest.get("scenes")) or {}
    for scene_id, owner in scene_owners.items():
        if not isinstance(scene_id, str) or owner != "compiled":
            continue
        source_file = f"scenes/{scene_id}.yaml"
        if source_file in tree.files:
            diagnostics.append(
                _ownership_diagnostic(
                    f"scene:{scene_id}", "scenes", f"ownership.yaml marks scene {scene_id!r} compiled", source_file
                )
            )
    if manifest.get("catalog") == "compiled" and "catalog.yaml" in tree.files:
        diagnostics.append(
            _ownership_diagnostic("catalog", "catalog", "ownership.yaml marks catalog compiled", "catalog.yaml")
        )
    diagnostics.extend(_legacy_id_conflicts(tree))
    return diagnostics


def _ownership_diagnostic(address: str, field: str, owner_text: str, source_file: str) -> Diagnostic:
    """Build the ownership diagnostic while naming both source owners."""

    identifier = address.split(":", 1)[-1]
    return _diagnostic(
        "L2.ownership",
        "ownership.yaml",
        address,
        field,
        f"record {identifier!r} is defined by ownership.yaml and {source_file}: {owner_text}",
    )


def _legacy_id_conflicts(tree: SourceTree) -> list[Diagnostic]:
    """Find explicit IDs repeated between declarative and legacy YAML files."""

    known: dict[str, set[str]] = {}
    for file, value in tree.files.items():
        if file in _SOURCE_FILES or _SCENE_FILE.fullmatch(file) or _MATCH_FILE.fullmatch(file):
            for identifier in _declared_ids(value):
                known.setdefault(identifier, set()).add(file)
    diagnostics: list[Diagnostic] = []
    for file, value in tree.files.items():
        if file in _SOURCE_FILES or _SCENE_FILE.fullmatch(file) or _MATCH_FILE.fullmatch(file):
            continue
        for identifier in _declared_ids(value):
            for source in sorted(known.get(identifier, ())):
                diagnostics.append(
                    _diagnostic(
                        "L2.ownership",
                        "ownership.yaml",
                        f"record:{identifier}",
                        "ownership",
                        f"record {identifier!r} is defined in {source} and legacy file {file}",
                    )
                )
    return diagnostics


def _declared_ids(value: object) -> set[str]:
    """Collect conservative record IDs from legacy or declarative YAML."""

    id_keys = {"id", "scene_id", "fact_id", "claim_id", "storylet_id", "realization_id", "event_id"}
    identifiers: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            if key in id_keys and isinstance(child, str):
                identifiers.add(child)
            if isinstance(child, dict):
                identifiers.update(
                    str(item)
                    for item in child
                    if isinstance(item, str)
                    and key in {"facts", "claims", "reveals", "events", "incidents", "characters", "items", "places"}
                )
            identifiers.update(_declared_ids(child))
    elif isinstance(value, list):
        for child in value:
            identifiers.update(_declared_ids(child))
    return identifiers


@layer2_check
def check_claims_and_scope(tree: SourceTree) -> list[Diagnostic]:
    """Run all layer-two checks owned by the claims and scope worker."""

    diagnostics: list[Diagnostic] = []
    diagnostics.extend(_claim_authorized(tree))
    diagnostics.extend(_override_add_only(tree))
    diagnostics.extend(_match_coverage(tree))
    diagnostics.extend(_incident_observations(tree))
    diagnostics.extend(_scene_scope(tree))
    diagnostics.extend(_ending_scene(tree))
    diagnostics.extend(_ownership(tree))
    return diagnostics

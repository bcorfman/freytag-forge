"""Layer-two checks for story logic that must survive source compilation."""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping
from typing import Any

from .checks import layer2_check
from .diagnostics import Diagnostic
from .reader import SourceTree

_SCENE_FILE = re.compile(r"scenes/([^/.]+)\.yaml$")
_MATCH_FILE = re.compile(r"scenes/([^/.]+)\.match\.yaml$")


def _mapping(value: object) -> dict[Any, Any] | None:
    """Return a mapping while keeping layer-two checks quiet on bad shapes."""

    return value if isinstance(value, dict) else None


def _scene_files(tree: SourceTree) -> Iterator[tuple[str, str, dict[Any, Any]]]:
    """Yield source scene files in deterministic order."""

    for file, value in sorted(tree.files.items()):
        if _MATCH_FILE.fullmatch(file):
            continue
        record = _mapping(value)
        match = _SCENE_FILE.fullmatch(file)
        if match and record is not None and isinstance(record.get("scene"), str):
            yield file, record["scene"], record


def _diagnostic(name: str, file: str, address: str, field: str, message: str) -> Diagnostic:
    """Build a diagnostic with a non-empty source location."""

    return Diagnostic(name, file, address or "root", field or "root", message)


def _true_mapping_keys(value: object) -> set[str]:
    """Return fact IDs asserted true by a source mapping."""

    record = _mapping(value)
    if record is None:
        return set()
    return {key for key, state in record.items() if isinstance(key, str) and state is True}


def _mapping_keys(value: object) -> set[str]:
    """Return fact IDs named by a source mapping, regardless of operation value."""

    record = _mapping(value)
    if record is None:
        return set()
    return {key for key in record if isinstance(key, str)}


def _scene_fact_declarations(tree: SourceTree) -> Iterator[tuple[str, str, str, dict[Any, Any]]]:
    """Yield scene fact declarations and their owning source file."""

    for file, scene_id, scene in _scene_files(tree):
        facts = _mapping(scene.get("facts"))
        if facts is None:
            continue
        for fact_id, declaration in facts.items():
            fact = _mapping(declaration)
            if isinstance(fact_id, str) and fact is not None:
                yield file, scene_id, fact_id, fact


def _catalog_fact_declarations(tree: SourceTree) -> Iterator[tuple[str, None, str, dict[Any, Any]]]:
    """Yield catalog.unplaced_facts declarations, if present."""

    catalog = _mapping(tree.files.get("catalog.yaml"))
    facts = _mapping(catalog.get("unplaced_facts")) if catalog is not None else None
    if facts is None:
        return
    for fact_id, declaration in facts.items():
        fact = _mapping(declaration)
        if isinstance(fact_id, str) and fact is not None:
            yield "catalog.yaml", None, fact_id, fact


def _all_fact_declarations(tree: SourceTree) -> Iterator[tuple[str, str | None, str, dict[Any, Any]]]:
    """Yield every source declaration that can carry a delivery."""

    yield from _scene_fact_declarations(tree)
    yield from _catalog_fact_declarations(tree)


def _add_reveal_producers(producers: set[str], reveal: Mapping[Any, Any]) -> None:
    """Add true commits from every realization of a reveal."""

    common = _mapping(reveal.get("commits_common")) or {}
    variants = _mapping(reveal.get("variants"))
    if variants is None:
        return
    for variant in variants.values():
        record = _mapping(variant)
        if record is None:
            continue
        commits = dict(common)
        commits.update(_mapping(record.get("commits")) or {})
        producers.update(_true_mapping_keys(commits))


def _add_incident_producers(producers: set[str], scene: Mapping[Any, Any]) -> None:
    """Add facts made true by the source scene's incident outcomes."""

    reveals = {
        reveal.get("id"): reveal
        for reveal in scene.get("reveals", ())
        if isinstance(reveal, Mapping) and isinstance(reveal.get("id"), str)
    }
    incidents = scene.get("incidents")
    if not isinstance(incidents, list):
        return
    for incident in incidents:
        record = _mapping(incident)
        reveal = reveals.get(record.get("reveal")) if record is not None else None
        variants = _mapping(reveal.get("variants")) if reveal is not None else None
        outcomes = record.get("outcomes") if record is not None else None
        if variants is None or not isinstance(outcomes, list):
            continue
        for outcome_key in outcomes:
            variant = _mapping(variants.get(outcome_key))
            if variant is None:
                continue
            commits = dict(_mapping(reveal.get("commits_common")) or {})
            commits.update(_mapping(variant.get("commits")) or {})
            producers.update(_true_mapping_keys(commits))
            outcome = _mapping(variant.get("outcome"))
            if outcome is not None:
                for field in ("advantages", "costs"):
                    values = outcome.get(field)
                    if isinstance(values, list):
                        producers.update(item for item in values if isinstance(item, str))


def _add_scene_producers(scene: Mapping[Any, Any]) -> set[str]:
    """Collect all source records that can assert a fact in one scene."""

    producers: set[str] = set()
    beats = scene.get("beats")
    if isinstance(beats, list):
        for beat in beats:
            record = _mapping(beat)
            if record is not None:
                producers.update(_true_mapping_keys(record.get("sets")))

    reveals = scene.get("reveals")
    if isinstance(reveals, list):
        for reveal in reveals:
            if isinstance(reveal, Mapping):
                _add_reveal_producers(producers, reveal)

    bridges = scene.get("bridge")
    if isinstance(bridges, list):
        for bridge in bridges:
            record = _mapping(bridge)
            if record is not None:
                producers.update(_true_mapping_keys(record.get("commits")))

    entry_claims = scene.get("entry_claims")
    if isinstance(entry_claims, list) and entry_claims:
        scene_id = scene.get("scene")
        if isinstance(scene_id, str):
            producers.add(f"scene_{scene_id.lower()}_entry_known")

    _add_incident_producers(producers, scene)
    return producers


def _add_delivery_producers(producers_by_scene: dict[str, set[str]], tree: SourceTree) -> None:
    """Include delivery assertions and true delivery costs, as the loader does."""

    for _, declaring_scene, fact_id, fact in _all_fact_declarations(tree):
        delivery = _mapping(fact.get("delivery"))
        if delivery is None:
            continue
        scene_id = delivery.get("scene") if isinstance(delivery.get("scene"), str) else declaring_scene
        if scene_id is None:
            continue
        producers_by_scene.setdefault(scene_id, set()).add(fact_id)
        producers_by_scene[scene_id].update(_true_mapping_keys(delivery.get("costs")))


def _transition_graph_has_cycle(tree: SourceTree) -> bool:
    """Leave cyclic transition reporting to the inherited L2.cycles check."""

    outgoing = {
        scene_id: exit_record.get("to")
        for _, scene_id, scene in _scene_files(tree)
        if (exit_record := _mapping(scene.get("exit"))) is not None and isinstance(exit_record.get("to"), str)
    }
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(scene_id: str) -> bool:
        if scene_id in visiting:
            return True
        if scene_id in visited:
            return False
        visiting.add(scene_id)
        target = outgoing.get(scene_id)
        if target is not None and visit(target):
            return True
        visiting.remove(scene_id)
        visited.add(scene_id)
        return False

    return any(visit(scene_id) for scene_id in outgoing)


def _transition_source_diagnostics(tree: SourceTree) -> list[Diagnostic]:
    """Reject positive exit triggers that have no producer in their source scene."""

    if _transition_graph_has_cycle(tree):
        return []
    producers_by_scene = {scene_id: _add_scene_producers(scene) for _, scene_id, scene in _scene_files(tree)}
    _add_delivery_producers(producers_by_scene, tree)
    diagnostics: list[Diagnostic] = []
    for file, scene_id, scene in _scene_files(tree):
        exit_record = _mapping(scene.get("exit"))
        if exit_record is None:
            continue
        exit_id = exit_record.get("id")
        if not isinstance(exit_id, str):
            continue
        when_all = exit_record.get("when_all")
        fact_ids = list(when_all) if isinstance(when_all, Mapping) else when_all
        if not isinstance(fact_ids, (list, tuple)):
            continue
        for fact_id in fact_ids:
            if not isinstance(fact_id, str) or fact_id in producers_by_scene.get(scene_id, set()):
                continue
            diagnostics.append(
                _diagnostic(
                    "L2.transition_source",
                    file,
                    f"exit:{exit_id}",
                    f"when_all[{fact_id}]",
                    f"transition '{exit_id}' trigger fact '{fact_id}' can never fail because it has no producer "
                    f"in source scene '{scene_id}'",
                )
            )
    return diagnostics


def _player_visible(value: object) -> bool:
    """Apply the source audience shorthand used by the compiler."""

    if value == "public":
        return True
    record = _mapping(value)
    return record is not None and record.get("player_visible") is True


def _claim_fact_ids(claim: Mapping[Any, Any]) -> set[str]:
    """Return the fact IDs established by a claim's effective subset."""

    return _mapping_keys(claim.get("commits_subset"))


def _visible_reveal_facts(visible: set[str], reveal: Mapping[Any, Any]) -> None:
    """Collect facts established by player-visible reveal claims."""

    common = _mapping(reveal.get("commits_common")) or {}
    variants = _mapping(reveal.get("variants"))
    if variants is None:
        return
    for variant_value in variants.values():
        variant = _mapping(variant_value)
        if variant is None:
            continue
        merged = dict(common)
        merged.update(_mapping(variant.get("commits")) or {})
        extras = variant.get("extra_claims")
        extra_records = [item for item in extras if isinstance(item, Mapping)] if isinstance(extras, list) else []
        extra_owned = {fact_id for extra in extra_records for fact_id in _claim_fact_ids(extra)}
        if "claim_id" in variant and _player_visible(variant.get("audience", reveal.get("audience"))):
            subset = _mapping(variant.get("commits_subset"))
            if subset is None:
                subset = {fact_id: value for fact_id, value in merged.items() if fact_id not in extra_owned}
            visible.update(_mapping_keys(subset))
        for extra in extra_records:
            if not isinstance(extra.get("claim_id"), str) or not _player_visible(
                extra.get("audience", variant.get("audience", reveal.get("audience")))
            ):
                continue
            extra_commits = dict(merged)
            if "commits" in extra:
                extra_commits = dict(common)
                extra_commits.update(_mapping(extra.get("commits")) or {})
            visible.update(_mapping_keys(extra.get("commits_subset", extra_commits)))


def _visible_claim_facts(tree: SourceTree) -> set[str]:
    """Collect every fact that a player-visible source claim can establish."""

    visible: set[str] = set()
    for _, scene_id, scene in _scene_files(tree):
        entry_claims = scene.get("entry_claims")
        if isinstance(entry_claims, list):
            for claim in entry_claims:
                record = _mapping(claim)
                if record is not None and _player_visible(record.get("audience")):
                    visible.add(f"scene_{scene_id.lower()}_entry_known")

        reveals = scene.get("reveals")
        if isinstance(reveals, list):
            for reveal in reveals:
                if isinstance(reveal, Mapping):
                    _visible_reveal_facts(visible, reveal)

        bridges = scene.get("bridge")
        if isinstance(bridges, list):
            for bridge in bridges:
                record = _mapping(bridge)
                claim = _mapping(record.get("claim")) if record is not None else None
                if claim is not None and _player_visible(claim.get("audience")):
                    commits = record.get("commits", {})
                    visible.update(_mapping_keys(claim.get("commits_subset", commits)))
    return visible


def _delivery_visibility_diagnostics(tree: SourceTree) -> list[Diagnostic]:
    """Reject deliveries for facts that no player-visible claim establishes."""

    visible_facts = _visible_claim_facts(tree)
    diagnostics: list[Diagnostic] = []
    for file, _, fact_id, fact in _all_fact_declarations(tree):
        if not fact.get("on_assert") or _mapping(fact.get("delivery")) is None or fact_id in visible_facts:
            continue
        diagnostics.append(
            _diagnostic(
                "L2.delivery_unseen",
                file,
                f"fact:{fact_id}",
                "delivery",
                f"delivery for fact '{fact_id}' has no player-visible knowledge definition",
            )
        )
    return diagnostics


@layer2_check
def check_story_logic(tree: SourceTree) -> list[Diagnostic]:
    """Run source checks for transition producers and delivery visibility."""

    return [*_transition_source_diagnostics(tree), *_delivery_visibility_diagnostics(tree)]

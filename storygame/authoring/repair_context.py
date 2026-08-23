"""Stable, read-only context for bounded causal-blueprint repairs."""

from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from storygame.authoring.symbol_resolution import Namespace, SymbolRegistry


class ChangeKind(StrEnum):
    """Structural changes that can affect a repair's unrelated story content."""

    ADDITION = "declaration_addition"
    REMOVAL = "declaration_removal"
    RENAME = "declaration_rename"
    OWNERSHIP = "ownership_change"
    REFERENCE = "reference_change"


class StructuralChange(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: ChangeKind
    namespace: Namespace
    path: str
    identifier: str
    previous_identifier: str | None = None
    target_namespace: Namespace | None = None
    values: tuple[str, ...] | None = None
    previous_values: tuple[str, ...] | None = None


class StructuralDiff(BaseModel):
    model_config = ConfigDict(frozen=True)

    changes: tuple[StructuralChange, ...] = ()

    def render(self) -> tuple[str, ...]:
        return tuple(
            f"{change.kind.value} at {change.path}: {change.namespace.value} '{change.identifier}'"
            + (f" renamed from '{change.previous_identifier}'" if change.previous_identifier is not None else "")
            for change in self.changes
        )


def repair_ledger(candidate: object) -> dict[str, object] | None:
    """Return deterministic namespace IDs from the shared symbol registry."""

    payload = _payload(candidate)
    if payload is None:
        return None
    try:
        registry = SymbolRegistry.from_payload(payload)
    except (TypeError, KeyError):
        return None
    names = {
        Namespace.TRUTH: "truth_ids",
        Namespace.PARTICIPANT: "participant_ids",
        Namespace.LOCATION: "location_ids",
        Namespace.CONNECTED_ROUTE: "connected_route_ids",
        Namespace.CAUSAL_EVENT: "causal_event_ids",
        Namespace.EVIDENCE_OPPORTUNITY: "evidence_opportunity_ids",
        Namespace.REALIZATION_ROUTE: "realization_route_ids",
        Namespace.REVELATION: "revelation_ids",
        Namespace.REQUIRED_OUTCOME: "required_outcome_ids",
        Namespace.REQUIRED_BEAT: "required_beat_ids",
        Namespace.OPTIONAL_BEAT: "optional_beat_ids",
        Namespace.END_STATE: "end_state_ids",
    }
    ledger = {key: list(registry.ids(namespace)) for namespace, key in names.items()}
    ledger["evidence_opportunity_truth_ids"] = {
        identifier: registry.symbol(Namespace.EVIDENCE_OPPORTUNITY, identifier).related_identifier
        for identifier in registry.ids(Namespace.EVIDENCE_OPPORTUNITY)
        if registry.symbol(Namespace.EVIDENCE_OPPORTUNITY, identifier) is not None
        and registry.symbol(Namespace.EVIDENCE_OPPORTUNITY, identifier).related_identifier is not None
    }
    return ledger


def structural_diff(previous: object, current: object) -> StructuralDiff:
    """Compare declarations and reference-bearing fields in stable source order."""

    old = _payload(previous) or {}
    new = _payload(current) or {}
    changes: list[StructuralChange] = []
    for collection, namespace in SymbolRegistry._COLLECTIONS:
        old_items = _by_id(old.get(collection))
        new_items = _by_id(new.get(collection))
        removed = sorted(set(old_items) - set(new_items))
        added = sorted(set(new_items) - set(old_items))
        paired: set[str] = set()
        for old_id in removed:
            matches = [
                candidate for candidate in added if _without_id(old_items[old_id]) == _without_id(new_items[candidate])
            ]
            if len(matches) == 1:
                new_id = matches[0]
                paired.add(new_id)
                changes.append(
                    StructuralChange(
                        kind=ChangeKind.RENAME,
                        namespace=namespace,
                        path=f"{collection}.{new_id}.id",
                        identifier=new_id,
                        previous_identifier=old_id,
                    )
                )
            else:
                changes.append(
                    StructuralChange(
                        kind=ChangeKind.REMOVAL,
                        namespace=namespace,
                        path=f"{collection}.{old_id}",
                        identifier=old_id,
                    )
                )
        for identifier in added:
            if identifier not in paired:
                changes.append(
                    StructuralChange(
                        kind=ChangeKind.ADDITION,
                        namespace=namespace,
                        path=f"{collection}.{identifier}",
                        identifier=identifier,
                    )
                )
        for identifier in sorted(set(old_items) & set(new_items)):
            _reference_changes(
                old_items[identifier],
                new_items[identifier],
                f"{collection}[{identifier}]",
                namespace,
                changes,
            )
    return StructuralDiff(changes=tuple(changes))


def is_additive_reference_change(
    change: StructuralChange,
    previous: object,
    current: object,
    diagnostic_details: tuple[str, ...] = (),
) -> bool:
    """Allow only ordered additions of symbols newly declared by the repair."""

    if (
        change.kind is not ChangeKind.REFERENCE
        or change.target_namespace is None
        or not diagnostic_details
        or not change.path.endswith((".output_truths", ".result_truth_ids", ".opportunity_ids"))
    ):
        return False
    before = change.previous_values
    after = change.values
    if before is None or after is None or not _is_subsequence(before, after):
        return False
    previous_ledger = repair_ledger(previous)
    current_ledger = repair_ledger(current)
    if previous_ledger is None or current_ledger is None:
        return False
    ledger_key = {
        Namespace.TRUTH: "truth_ids",
        Namespace.PARTICIPANT: "participant_ids",
        Namespace.LOCATION: "location_ids",
        Namespace.CONNECTED_ROUTE: "connected_route_ids",
        Namespace.CAUSAL_EVENT: "causal_event_ids",
        Namespace.EVIDENCE_OPPORTUNITY: "evidence_opportunity_ids",
        Namespace.REALIZATION_ROUTE: "realization_route_ids",
        Namespace.REVELATION: "revelation_ids",
        Namespace.REQUIRED_OUTCOME: "required_outcome_ids",
        Namespace.REQUIRED_BEAT: "required_beat_ids",
        Namespace.OPTIONAL_BEAT: "optional_beat_ids",
        Namespace.END_STATE: "end_state_ids",
    }[change.target_namespace]
    previous_ids = set(previous_ledger[ledger_key])
    introduced_ids = set(current_ledger[ledger_key]) - previous_ids
    added_references = set(after) - set(before)
    if not added_references or not added_references <= introduced_ids:
        return False
    details = " ".join(diagnostic_details).casefold()
    if change.target_namespace is Namespace.EVIDENCE_OPPORTUNITY:
        payload = _payload(current) or {}
        opportunities = _by_id(payload.get("evidence_opportunities"))
        related_truths = {
            str(opportunities[identifier].get("truth_id"))
            for identifier in added_references
            if identifier in opportunities
        }
        return any(value.casefold() in details for value in added_references | related_truths)
    return any(identifier.casefold() in details for identifier in added_references)


def _payload(candidate: object) -> Mapping[str, object] | None:
    if isinstance(candidate, Mapping):
        return candidate
    model_dump = getattr(candidate, "model_dump", None)
    if callable(model_dump):
        dumped = model_dump(mode="json")
        return dumped if isinstance(dumped, Mapping) else None
    if isinstance(candidate, str):
        try:
            dumped = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return dumped if isinstance(dumped, Mapping) else None
    return None


def _is_subsequence(before: tuple[str, ...], after: tuple[str, ...]) -> bool:
    position = 0
    for value in after:
        if position < len(before) and value == before[position]:
            position += 1
    return position == len(before)


def _by_id(value: object) -> dict[str, Mapping[str, object]]:
    if not isinstance(value, (list, tuple)):
        return {}
    return {item["id"]: item for item in value if isinstance(item, Mapping) and isinstance(item.get("id"), str)}


def _without_id(item: Mapping[str, object]) -> dict[str, object]:
    return {key: value for key, value in item.items() if key != "id"}


def _reference_changes(
    old: Mapping[str, object],
    new: Mapping[str, object],
    path: str,
    source_namespace: Namespace,
    changes: list[StructuralChange],
) -> None:
    for key in sorted(set(old) & set(new)):
        before, after = old[key], new[key]
        child_path = f"{path}.{key}"
        if isinstance(before, Mapping) and isinstance(after, Mapping):
            _reference_changes(before, after, child_path, source_namespace, changes)
            continue
        if before == after or not (key.endswith("_id") or key.endswith("_ids")):
            continue
        target_namespace = _target_namespace(key)
        kind = ChangeKind.OWNERSHIP if key in {"route_id", "holder_id", "owner_id"} else ChangeKind.REFERENCE
        previous_values = _reference_sequence(before)
        values = _reference_sequence(after)
        changes.append(
            StructuralChange(
                kind=kind,
                namespace=source_namespace,
                path=child_path,
                identifier=str(after),
                previous_identifier=str(before),
                target_namespace=target_namespace,
                values=values,
                previous_values=previous_values,
            )
        )


def _reference_sequence(value: object) -> tuple[str, ...] | None:
    if not isinstance(value, (list, tuple)) or not all(isinstance(item, str) for item in value):
        return None
    return tuple(value)


def _target_namespace(key: str) -> Namespace | None:
    stem = key.removesuffix("_ids").removesuffix("_id")
    aliases = {
        "truth": Namespace.TRUTH,
        "output": Namespace.TRUTH,
        "result": Namespace.TRUTH,
        "participant": Namespace.PARTICIPANT,
        "location": Namespace.LOCATION,
        "route": Namespace.REALIZATION_ROUTE,
        "revelation": Namespace.REVELATION,
        "outcome": Namespace.REQUIRED_OUTCOME,
        "beat": Namespace.REQUIRED_BEAT,
        "event": Namespace.CAUSAL_EVENT,
        "opportunity": Namespace.EVIDENCE_OPPORTUNITY,
    }
    return aliases.get(stem)

"""Check that contract world needs have model and story support."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from worldkeeper import WorldSchema

from factory.contracts.lint import load_rules
from storygame.runtime.world_model import world_schema_data
from storygame.story_package.dependencies import consumers, producers
from storygame.story_package.loader import load_story_package

from .gap_delta import DEFAULT_ROOT

_OBJECT_RELATIONS = {"hold", "know", "reach", "hidden", "seated", "companion"}
_NO_OBJECT_RELATIONS = {"axis", "exist"}


@dataclass(frozen=True)
class NeedResult:
    """The three-question assessment for one contract need."""

    scene_id: str
    need_id: str
    relation: str
    outcome: str
    q1: str
    q2: str
    q3: str
    reasons: tuple[str, ...]


def _ordered_scene_records(
    contract: Mapping[str, Any], rules: Mapping[str, Any]
) -> list[tuple[str, int, dict[str, Any]]]:
    scenes = contract.get("scenes", ())
    if not isinstance(scenes, list):
        return []
    scene_ids = [scene_id for scene_id in rules.get("scene_ids", ()) if isinstance(scene_id, str)]
    positions = {scene_id: position for position, scene_id in enumerate(scene_ids)}
    records = []
    for index, scene in enumerate(scenes):
        if isinstance(scene, dict):
            scene_id = scene.get("scene_id") if isinstance(scene.get("scene_id"), str) else ""
            records.append((scene_id, positions.get(scene_id, len(positions) + index), scene))
    return [record for _, record in sorted(enumerate(records), key=lambda item: (item[1][1], item[0]))]


def _need_records(records: list[tuple[str, int, dict[str, Any]]]) -> list[tuple[str, int, dict[str, Any]]]:
    result = []
    for scene_id, position, scene in records:
        needs = scene.get("world_needs", ())
        if isinstance(needs, list):
            result.extend((scene_id, position, need) for need in needs if isinstance(need, dict))
    return result


def _kind(schema: WorldSchema, entity_id: str, supplied: object) -> str | None:
    if supplied is not None:
        return supplied if isinstance(supplied, str) else None
    entity = schema.entities.get(entity_id)
    return getattr(entity, "kind", None) if entity is not None else None


def _earlier_contract_creates(
    need_records: list[tuple[str, int, dict[str, Any]]], scene_position: int, fact_id: str
) -> bool:
    return any(
        position < scene_position
        and need.get("relation") == "know"
        and need.get("object") == fact_id
        and need.get("role", "relies_on") == "creates"
        for _scene_id, position, need in need_records
    )


def _later_contract_relies_on(
    need_records: list[tuple[str, int, dict[str, Any]]], scene_position: int, fact_id: str
) -> bool:
    return any(
        position > scene_position
        and need.get("relation") == "know"
        and need.get("object") == fact_id
        and need.get("role", "relies_on") == "relies_on"
        for _scene_id, position, need in need_records
    )


def _package_scene_support(records: object, scene_position: int, positions: Mapping[str, int], *, before: bool) -> bool:
    for record in records:
        record_scene_id = getattr(record, "scene_id", None)
        if record_scene_id is None:
            return True
        record_position = positions.get(record_scene_id)
        if record_position is not None:
            supported = record_position <= scene_position if before else record_position >= scene_position
            if supported:
                return True
    return False


def _malformed_result(scene_id: str, need: Mapping[str, Any]) -> NeedResult:
    need_id = need.get("id") if isinstance(need.get("id"), str) else ""
    relation = need.get("relation") if isinstance(need.get("relation"), str) else ""
    return NeedResult(scene_id, need_id, relation, "story_hole", "n/a", "n/a", "n/a", ("malformed need",))


def _check_one(
    scene_id: str,
    scene_position: int,
    need: Mapping[str, Any],
    schema: WorldSchema,
    package: object,
    need_records: list[tuple[str, int, dict[str, Any]]],
    positions: Mapping[str, int],
    allowed_roles: tuple[str, ...],
) -> NeedResult:
    need_id = need.get("id") if isinstance(need.get("id"), str) else ""
    relation = need.get("relation") if isinstance(need.get("relation"), str) else ""
    subject = need.get("subject")
    role = need.get("role", "relies_on")
    malformed = (
        not need_id.strip()
        or not relation.strip()
        or not isinstance(subject, str)
        or not subject.strip()
        or ("role" in need and role not in allowed_roles)
        or any(
            field in need and (not isinstance(need[field], str) or not need[field].strip())
            for field in ("subject_kind", "object_kind")
        )
    )
    if relation in _OBJECT_RELATIONS and (not isinstance(need.get("object"), str) or not need["object"].strip()):
        malformed = True
    if relation == "axis" and (
        not isinstance(need.get("axis"), str)
        or not need["axis"].strip()
        or not isinstance(need.get("pole"), str)
        or not need["pole"].strip()
    ):
        malformed = True
    if malformed:
        return _malformed_result(scene_id, need)

    fact_ids = set(getattr(package, "fact_ids", ()))
    object_id = need.get("object") if isinstance(need.get("object"), str) else ""
    subject_kind = _kind(schema, subject, need.get("subject_kind"))
    object_kind = None
    if relation not in _NO_OBJECT_RELATIONS and relation != "know":
        object_kind = _kind(schema, object_id, need.get("object_kind"))

    reasons: list[str] = []
    q1 = "yes"
    q2 = "n/a"
    q3 = "n/a"
    q1_outcome = "ok"
    needs_object_kind = relation in (_OBJECT_RELATIONS - {"know"})
    if subject_kind is None or (needs_object_kind and object_kind is None):
        q1 = "no"
        q1_outcome = "story_hole"
        missing = subject if subject_kind is None else object_id
        reasons.append(f"declare the thing or give its kind: {missing}")
    else:
        representation = schema.can_represent(relation, subject_kind, object_kind)
        if not representation.ok:
            q1 = "no"
            reason = representation.reason
            reasons.append(reason)
            q1_outcome = "story_hole" if reason.startswith("unknown kind") else "worldkeeper_ticket"

    if (
        relation == "know"
        and object_id not in fact_ids
        and not _earlier_contract_creates(need_records, scene_position, object_id)
    ):
        q1 = "no"
        reasons.append("fact is not declared")
        if q1_outcome != "worldkeeper_ticket":
            q1_outcome = "story_hole"

    if relation == "know" and role == "relies_on":
        q2_support = _package_scene_support(
            producers(package, object_id), scene_position, positions, before=True
        ) or _earlier_contract_creates(need_records, scene_position, object_id)
        if q2_support:
            q2 = "yes"
        else:
            q2 = "no"
            reasons.append("nothing earlier produces it")
    if relation == "know" and role == "creates":
        q3_support = _package_scene_support(
            consumers(package, object_id), scene_position, positions, before=False
        ) or _later_contract_relies_on(need_records, scene_position, object_id)
        if q3_support:
            q3 = "yes"
        else:
            q3 = "no"
            reasons.append("nothing later reads it")

    has_ticket = q1_outcome == "worldkeeper_ticket"
    outcome = "worldkeeper_ticket" if has_ticket else "story_hole" if "no" in (q1, q2, q3) else "ok"
    return NeedResult(scene_id, need_id, relation, outcome, q1, q2, q3, tuple(reasons))


def check_needs(contract: dict, package, *, rules: dict | None = None) -> list[NeedResult]:
    """Assess every world need in scene order and contract order."""

    active_rules = load_rules() if rules is None else rules
    if not isinstance(contract, dict):
        return []
    schema = WorldSchema.from_data(world_schema_data(package))
    records = _ordered_scene_records(contract, active_rules)
    need_records = _need_records(records)
    positions = {scene_id: position for scene_id, position, _scene in records}
    allowed_roles = tuple(
        role for role in active_rules.get("need_roles", ("relies_on", "creates")) if isinstance(role, str)
    )
    results = []
    for scene_id, scene_position, scene in records:
        needs = scene.get("world_needs", ())
        if not isinstance(needs, list):
            continue
        for need in needs:
            if not isinstance(need, dict):
                results.append(_malformed_result(scene_id, {}))
            else:
                results.append(
                    _check_one(
                        scene_id,
                        scene_position,
                        need,
                        schema,
                        package,
                        need_records,
                        positions,
                        allowed_roles,
                    )
                )
    return results


def tickets_for(results: list[NeedResult]) -> list[dict]:
    """Return ticket records for every need that is not OK."""

    tickets = []
    for result in results:
        if result.outcome == "ok":
            continue
        reasons = "; ".join(result.reasons)
        tickets.append(
            {
                "kind": result.outcome,
                "scene_id": result.scene_id,
                "need_id": result.need_id,
                "summary": (
                    f"Scene {result.scene_id} need {result.need_id} has {result.outcome.replace('_', ' ')}: {reasons}."
                ),
            }
        )
    return tickets


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("contract", type=Path)
    parser.add_argument("--story", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", dest="json_path", type=Path, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the world-need check for one contract."""

    options = _parser().parse_args(argv)
    try:
        contract = json.loads(options.contract.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"error: {error}")
        return 2
    package = load_story_package(options.story)
    results = check_needs(contract, package)
    tickets = tickets_for(results)
    for ticket in tickets:
        print(f"{ticket['kind']} {ticket['scene_id']} {ticket['need_id']}: {ticket['summary']}")
    if not tickets:
        print("ok")
    if options.json_path is not None:
        options.json_path.write_text(
            json.dumps({"results": [asdict(result) for result in results], "tickets": tickets}, indent=2) + "\n",
            encoding="utf-8",
        )
    return 0 if not tickets else 1


if __name__ == "__main__":
    raise SystemExit(main())

"""Deterministic export, import, and comparison of world-only facts."""

from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import World


WORLD_PREDICATES = (
    "wk_alias",
    "wk_axis",
    "wk_companion",
    "wk_condition",
    "wk_facet",
    "wk_fixed",
    "wk_hidden",
    "wk_incidental",
    "wk_kind",
    "wk_moved",
    "wk_name",
    "wk_owner",
    "wk_parent",
    "wk_place_text",
    "wk_relation",
    "wk_seeded",
    "wk_status",
    "wk_unplaced",
)

SCHEMA_VERSION = 1
_WORLD_MARKER = "__world__"


def _fact_dict(fact):
    return {
        "predicate": fact.predicate,
        "subject": fact.subject,
        "object": fact.object,
        "value": fact.value,
    }


def _fact_sort_key(fact):
    return tuple(
        (0, "") if value is None else (1, value)
        for value in (fact["predicate"], fact["subject"], fact["object"], fact["value"])
    )


def export_state(world: "World") -> dict:
    """Return every known world fact in a deterministic, JSON-safe shape."""
    facts = [_fact_dict(fact) for predicate in WORLD_PREDICATES for fact in world.backend.matching(predicate)]
    facts.sort(key=_fact_sort_key)
    return {"schema": SCHEMA_VERSION, "facts": facts}


def _refusal(reason):
    from .model import OpResult

    return OpResult(False, reason)


def import_state(world: "World", state: dict):
    """Replace known world facts with a validated snapshot."""
    if not isinstance(state, dict) or state.get("schema") != SCHEMA_VERSION:
        return _refusal("unknown state schema")
    facts = state.get("facts")
    if not isinstance(facts, list):
        return _refusal("state facts must be a list")

    parsed = []
    declared_ids = set(world.schema.entities)
    for item in facts:
        if not isinstance(item, dict):
            return _refusal("state fact must be an object")
        predicate = item.get("predicate")
        subject = item.get("subject")
        if predicate not in WORLD_PREDICATES:
            return _refusal(f"unknown world predicate: {predicate}")
        if not isinstance(subject, str) or (subject not in declared_ids and subject != _WORLD_MARKER):
            return _refusal(f"unknown world subject: {subject}")
        if any(item.get(field) is not None and not isinstance(item.get(field), str) for field in ("object", "value")):
            return _refusal("world fact fields must be strings or null")
        parsed.append(world._fact(predicate, subject, item.get("object"), item.get("value")))

    for predicate in WORLD_PREDICATES:
        for fact in world.backend.matching(predicate):
            world.backend.retract_fact(fact)
    for fact in parsed:
        world.backend.assert_fact(fact)
    from .model import OpResult

    return OpResult(True)


def entry_problems(world: "World", protagonist_id: str, location_id: str) -> tuple[str, ...]:
    """Return plain-language violations of the world entry invariants."""
    problems = []
    parent_subjects = {fact.subject for fact in world._facts("wk_parent")}
    entity_ids = set(world.entity_ids()) | parent_subjects

    for entity_id in sorted(entity_ids):
        parent_facts = world._facts("wk_parent", entity_id)
        effective_parent = world.parent(entity_id)
        if effective_parent is not None and len(parent_facts) != 1:
            problems.append(f"{entity_id} does not have exactly one parent fact")
        for fact in parent_facts:
            if not fact.value or not world.exists(fact.value):
                problems.append(f"{entity_id} has a parent that does not exist")
        if entity_id in world.chain(entity_id):
            problems.append(f"{entity_id} is in a parent cycle")

    if not world.exists(protagonist_id):
        problems.append(f"protagonist {protagonist_id} does not exist")
    elif location_id not in world.chain(protagonist_id):
        problems.append(f"protagonist {protagonist_id} is not at {location_id}")

    for entity_id in sorted(world.entity_ids()):
        if (
            world.is_item(entity_id)
            and world.holder(entity_id) == protagonist_id
            and world.holds(protagonist_id, entity_id)
            and world.is_hidden(entity_id)
        ):
            problems.append(f"held item {entity_id} is hidden")

    for fact in world._facts("wk_axis"):
        definitions = {definition["name"]: definition for definition in world.axis_definitions(fact.subject)}
        definition = definitions.get(fact.object)
        if definition is None or fact.value not in definition["poles"]:
            problems.append(f"{fact.subject} has an invalid axis value")

    for fact in world._facts("wk_companion"):
        if not world.exists(fact.subject) or not world.exists(fact.object):
            problems.append(f"companion {fact.subject} or {fact.object} does not exist")

    return tuple(dict.fromkeys(problems))


def _group_facts(state):
    grouped = defaultdict(list)
    for fact in state["facts"]:
        grouped[(fact["predicate"], fact["subject"])].append(fact)
    for facts in grouped.values():
        facts.sort(key=_fact_sort_key)
    return grouped


def diff_states(before: dict, after: dict) -> dict:
    """Return added, removed, and predicate/subject-grouped changed facts."""
    before_facts = {tuple(_fact_sort_key(fact)): fact for fact in before["facts"]}
    after_facts = {tuple(_fact_sort_key(fact)): fact for fact in after["facts"]}
    before_groups = _group_facts(before)
    after_groups = _group_facts(after)
    changed = []
    changed_keys = set()
    for key in sorted(set(before_groups) & set(after_groups)):
        if before_groups[key] != after_groups[key]:
            changed_keys.add(key)
            changed.append(
                {
                    "predicate": key[0],
                    "subject": key[1],
                    "before": before_groups[key],
                    "after": after_groups[key],
                }
            )
    return {
        "added": sorted(
            (
                fact
                for key, fact in after_facts.items()
                if key not in before_facts and (fact["predicate"], fact["subject"]) not in changed_keys
            ),
            key=_fact_sort_key,
        ),
        "removed": sorted(
            (
                fact
                for key, fact in before_facts.items()
                if key not in after_facts and (fact["predicate"], fact["subject"]) not in changed_keys
            ),
            key=_fact_sort_key,
        ),
        "changed": changed,
    }

"""Fact-backed schema and world operations."""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol

BASE_KINDS = {
    "entity": (),
    "area": ("entity",),
    "character": ("entity",),
    "thing": ("entity",),
    "container": ("thing",),
    "supporter": ("thing",),
    "furniture": ("thing",),
    "vehicle": ("container",),
}


@dataclass(frozen=True)
class Fact:
    """An immutable world fact."""

    predicate: str
    subject: str
    object: str | None = None
    value: str | None = None


class FactLike(Protocol):
    predicate: str
    subject: str
    object: str | None
    value: str | None


class FactBackend(Protocol):
    """Storage interface used by :class:`World`."""

    def matching(self, predicate: str, subject: str | None = None) -> tuple[FactLike, ...]: ...
    def assert_fact(self, fact) -> None: ...
    def retract_fact(self, fact) -> None: ...


class MemoryBackend:
    """Store facts in a process-local set."""

    def __init__(self):
        self._facts: set[Fact] = set()

    def matching(self, predicate, subject=None):
        """Return facts matching predicate and optional subject."""
        return tuple(
            fact for fact in self._facts if fact.predicate == predicate and (subject is None or fact.subject == subject)
        )

    def matching_all(self):
        """Return all stored facts."""
        return tuple(self._facts)

    def assert_fact(self, fact):
        """Store a fact."""
        self._facts.add(fact)

    def retract_fact(self, fact):
        """Remove a fact when present."""
        self._facts.discard(fact)


class SchemaError(ValueError):
    """An invalid schema declaration."""


@dataclass
class OpResult:
    """The success, refusal reason, and optional ID of an operation."""

    ok: bool
    reason: str = ""
    id: str | None = None


@dataclass
class _Entity:
    id: str
    name: str
    kind: str
    aliases: tuple[str, ...] = ()
    owner: str | None = None
    parent: str | None = None
    fixed: bool = False
    openable: bool = False
    open: bool = False
    captive: bool = False
    hidden: bool = False
    axes: tuple[dict[str, Any], ...] = ()


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _ancestors(kinds, kind):
    result = {kind}
    for parent_kind in kinds[kind]:
        result |= _ancestors(kinds, parent_kind)
    return result


class WorldSchema:
    """Hold static kinds and declared entities."""

    def __init__(self, kinds, entities):
        self.kinds, self.entities = kinds, entities

    @classmethod
    def from_data(cls, data: Mapping):
        """Validate mappings and return a schema, or raise :class:`SchemaError`."""
        kinds = dict(BASE_KINDS)
        kind_ids = set()
        for kind_data in data.get("kinds", []):
            kind_id = kind_data.get("id")
            if not kind_id or kind_id in kinds or kind_id in kind_ids:
                raise SchemaError("invalid or duplicate story kind")
            kind_ids.add(kind_id)
            kinds[kind_id] = tuple(kind_data.get("is", []))
        if any(parent not in kinds for parents in kinds.values() for parent in parents):
            raise SchemaError("unknown kind parent")

        def visit(kind, path=()):
            if kind in path:
                raise SchemaError("cycle among kinds")
            for parent_kind in kinds[kind]:
                visit(parent_kind, path + (kind,))

        for kind in kinds:
            visit(kind)
        entities = {}
        raw_entities = list(data.get("entities", []))
        for entity_data in raw_entities:
            entity_id, kind = entity_data.get("id"), entity_data.get("kind")
            if not entity_id or entity_id in entities or kind not in kinds:
                raise SchemaError("invalid entity declaration")
            axes = []
            for axis_data in entity_data.get("axes", []):
                poles = axis_data.get("poles", [])
                if len(poles) != 2 or poles[0] == poles[1]:
                    raise SchemaError("axis needs two distinct poles")
                axes.append(
                    {
                        "name": poles[0],
                        "poles": tuple(poles),
                        "aliases": dict(axis_data.get("aliases", {})),
                        "initial": axis_data.get("initial", poles[0]),
                    }
                )
            entities[entity_id] = _Entity(
                entity_id,
                entity_data.get("name", ""),
                kind,
                tuple(entity_data.get("aliases", [])),
                entity_data.get("owner"),
                entity_data.get("parent"),
                entity_data.get("fixed", kind == "furniture"),
                entity_data.get("openable", False),
                entity_data.get("open", False),
                entity_data.get("captive", False),
                entity_data.get("hidden", False),
                tuple(axes),
            )
        for entity in list(entities.values()):
            if entity.parent and (
                "area" not in _ancestors(kinds, entity.kind)
                or entity.parent not in entities
                or "area" not in _ancestors(kinds, entities[entity.parent].kind)
            ):
                raise SchemaError("area parent is not an area")
            if entity.owner and (
                entity.owner not in entities or "character" not in _ancestors(kinds, entities[entity.owner].kind)
            ):
                raise SchemaError("unknown owner")
            source = next(item for item in raw_entities if item.get("id") == entity.id)
            for content_name in source.get("contents", []):
                content_id = f"{entity.id}_{_slug(content_name)}"
                if content_id in entities:
                    raise SchemaError("duplicate expanded content")
                entities[content_id] = _Entity(content_id, content_name, "thing", parent=entity.id)
        return cls(kinds, entities)


class World:
    """Read and mutate a world whose only mutable state is in its backend."""

    def __init__(self, schema, backend, *, make_fact=Fact, resolver: Callable | None = None):
        self.schema, self.backend, self.make_fact, self.resolver = schema, backend, make_fact, resolver

    # Encoding: identity and free text are values; short keys are objects.
    def _fact(self, predicate, subject, object_value=None, value=None):
        return self.make_fact(predicate=predicate, subject=subject, object=object_value, value=value)

    def _facts(self, predicate, subject=None):
        return tuple(fact for fact in self.backend.matching(predicate, subject) if fact.predicate.startswith("wk_"))

    def _value(self, predicate, subject):
        facts = self._facts(predicate, subject)
        return facts[0].value if facts else None

    def _replace(self, predicate, subject, object_value=None, value=None):
        for fact in self._facts(predicate, subject):
            self.backend.retract_fact(fact)
        self.backend.assert_fact(self._fact(predicate, subject, object_value, value))

    def _replace_if_absent(self, predicate, subject, object_value=None, value=None):
        if not self._facts(predicate, subject):
            self.backend.assert_fact(self._fact(predicate, subject, object_value, value))

    def _replace_axis(self, entity_id, axis_name, pole):
        for fact in self._facts("wk_axis", entity_id):
            if fact.object == axis_name:
                self.backend.retract_fact(fact)
        self.backend.assert_fact(self._fact("wk_axis", entity_id, axis_name, pole))

    def _add(self, predicate, subject, object_value=None, value=None):
        if not any(fact.object == object_value and fact.value == value for fact in self._facts(predicate, subject)):
            self.backend.assert_fact(self._fact(predicate, subject, object_value, value))

    def _entity(self, entity_id):
        if entity_id in self.schema.entities:
            return self.schema.entities[entity_id]
        if entity_id in self._fact_ids():
            return _Entity(
                entity_id,
                self._value("wk_name", entity_id) or "",
                self._value("wk_kind", entity_id) or "thing",
                owner=self._value("wk_owner", entity_id),
            )
        return None

    def _is_a(self, entity_id, kind):
        entity = self._entity(entity_id)
        return bool(entity and kind in _ancestors(self.schema.kinds, entity.kind))

    def _fact_ids(self):
        return {fact.subject for fact in self._facts("wk_kind")}

    def _ids(self):
        return set(self.schema.entities) | self._fact_ids()

    def _axes(self, entity_id):
        entity = self._entity(entity_id)
        if not entity:
            return ()
        axes = []
        if entity.openable:
            axes.append({"name": "open", "poles": ("open", "closed"), "aliases": {}})
        if self._is_a(entity_id, "character"):
            axes.append({"name": "captive", "poles": ("captive", "free"), "aliases": {}})
        axes.extend(entity.axes)
        return tuple(axes)

    def seed(self):
        """Write missing initial facts without overwriting played state."""
        for entity in self.schema.entities.values():
            if entity.hidden:
                self._replace_if_absent("wk_hidden", entity.id, "true")
            if entity.parent:
                self._replace_if_absent("wk_parent", entity.id, value=entity.parent)
                self._replace_if_absent("wk_relation", entity.id, value="in")
            if entity.openable:
                self._seed_axis(entity.id, "open", "open" if entity.open else "closed")
            if self._is_a(entity.id, "character"):
                self._seed_axis(entity.id, "captive", "captive" if entity.captive else "free")
            for axis in entity.axes:
                self._seed_axis(entity.id, axis["name"], axis["initial"])
        return OpResult(True)

    def _seed_axis(self, entity_id, axis_name, initial):
        if not any(fact.object == axis_name for fact in self._facts("wk_axis", entity_id)):
            self._replace_axis(entity_id, axis_name, initial)

    def exists(self, entity_id):
        """Return whether an entity is declared or backed by a creation fact."""
        return self._entity(entity_id) is not None

    def kind(self, entity_id):
        """Return an entity kind, or empty text for an unknown ID."""
        entity = self._entity(entity_id)
        return entity.kind if entity else ""

    def is_a(self, entity_id, kind):
        """Return whether an entity is of a kind or its ancestor."""
        return self._is_a(entity_id, kind)

    def name(self, entity_id):
        """Return an entity name, or empty text for an unknown ID."""
        entity = self._entity(entity_id)
        return entity.name if entity else ""

    def owner(self, entity_id):
        """Return an entity owner, if recorded."""
        entity = self._entity(entity_id)
        return entity.owner if entity else None

    def parent(self, entity_id):
        """Return an entity parent, or no parent."""
        return self._entity(entity_id).parent if self._is_a(entity_id, "area") else self._value("wk_parent", entity_id)

    def relation(self, entity_id):
        """Return an entity's relation to its parent."""
        return (
            "in" if self._is_a(entity_id, "area") and self.parent(entity_id) else self._value("wk_relation", entity_id)
        )

    def chain(self, entity_id):
        """Return parent IDs from nearest to farthest."""
        chain, seen_ids, current_parent = [], set(), self.parent(entity_id)
        while current_parent and current_parent not in seen_ids:
            chain.append(current_parent)
            seen_ids.add(current_parent)
            current_parent = self.parent(current_parent)
        return tuple(chain)

    def area(self, entity_id):
        """Return the containing area, if placed."""
        return (
            entity_id
            if self._is_a(entity_id, "area")
            else next((ancestor for ancestor in self.chain(entity_id) if self._is_a(ancestor, "area")), None)
        )

    def holder(self, entity_id):
        """Return the containing character, if held."""
        return next((ancestor for ancestor in self.chain(entity_id) if self._is_a(ancestor, "character")), None)

    def together(self, first_id, second_id):
        """Return whether two entities share an area."""
        return self.area(first_id) is not None and self.area(first_id) == self.area(second_id)

    def contents(self, entity_id):
        """Return direct child IDs in sorted order."""
        return tuple(sorted(candidate for candidate in self._ids() if self.parent(candidate) == entity_id))

    def is_hidden(self, entity_id):
        """Return whether an entity is hidden."""
        return bool(self._facts("wk_hidden", entity_id))

    def status(self, entity_id):
        """Return an entity status, if set."""
        return self._value("wk_status", entity_id)

    def axis_values(self, entity_id):
        """Return axis names mapped to their poles."""
        return {fact.object: fact.value for fact in self._facts("wk_axis", entity_id)}

    def is_visible(self, entity_id):
        """Return whether an entity is currently visible."""
        if not self.exists(entity_id) or self.is_hidden(entity_id) or self.status(entity_id) == "missing":
            return False
        return not any(self._closed_in(entity) for entity in (entity_id,) + self.chain(entity_id))

    def _closed_in(self, entity_id):
        parent_id = self.parent(entity_id)
        return bool(
            self.relation(entity_id) == "in"
            and parent_id
            and self._entity(parent_id).openable
            and self.axis_values(parent_id).get("open") == "closed"
        )

    def given_with(self, entity_id):
        """Return visible direct contents of an open or non-openable container."""
        if not self._is_a(entity_id, "container"):
            return ()
        container = self._entity(entity_id)
        if container.openable and self.axis_values(entity_id).get("open") == "closed":
            return ()
        return tuple(
            child for child in self.contents(entity_id) if self.relation(child) == "in" and self.is_visible(child)
        )

    def conditions(self, entity_id):
        """Return conditions in the order supplied to :meth:`set_conditions`."""
        facts = sorted(self._facts("wk_condition", entity_id), key=lambda fact: int(fact.object or 0))
        return tuple(fact.value for fact in facts)

    def unplaced_name(self, entity_id):
        """Return an entity's unplaced free-text location."""
        return self._value("wk_unplaced", entity_id)

    def companions(self, entity_id):
        """Return companions following an entity."""
        return tuple(sorted(fact.subject for fact in self._facts("wk_companion") if fact.object == entity_id))

    def place_label(self, entity_id):
        """Return authored placement text, parent name, or unplaced name."""
        if not self.exists(entity_id):
            return None
        moved = any(self._facts("wk_moved", ancestor) for ancestor in (entity_id,) + self.chain(entity_id))
        if not moved and self._value("wk_place_text", entity_id):
            return self._value("wk_place_text", entity_id)
        return self.name(self.parent(entity_id)) if self.parent(entity_id) else self.unplaced_name(entity_id)

    def resolve(self, name):
        """Resolve names, aliases, part forms, or a resolver-selected ambiguity."""
        query = self._normalize(name)
        matches = []
        for entity_id in self._ids():
            entity = self._entity(entity_id)
            names = (entity.name,) + entity.aliases
            if any(self._normalize(candidate) == query for candidate in names):
                matches.append(entity_id)
            if self._is_a(entity_id, "area") and any(
                query in (self._normalize(candidate) + " floor", "floor of " + self._normalize(candidate))
                for candidate in names
            ):
                matches.append(entity_id)
            if self._is_a(entity_id, "character") and any(
                query in (self._normalize(candidate) + "'s hand", self._normalize(candidate) + "'s hands")
                for candidate in names
            ):
                matches.append(entity_id)
        unique_matches = list(dict.fromkeys(matches))
        if len(unique_matches) == 1:
            return unique_matches[0]
        if self.resolver:
            selected = self.resolver(name, tuple(unique_matches) if unique_matches else tuple(self._ids()))
            return selected if selected in self._ids() else None
        return None

    @staticmethod
    def _normalize(text):
        return re.sub(r"^(the|a|an)\s+", "", text.strip().lower())

    def _bad(self, reason):
        return OpResult(False, reason)

    def _check(self, entity_id, parent_id, under=False, authorized=False):
        if not self.exists(entity_id) or not self.exists(parent_id):
            return "unknown entity"
        if entity_id == parent_id or entity_id in self.chain(parent_id):
            return "that would create a cycle"
        if self._is_a(entity_id, "area"):
            return "areas cannot be moved"
        entity = self._entity(entity_id)
        if not authorized and entity.fixed:
            return "fixed things cannot move"
        if not authorized and self.is_hidden(entity_id):
            return "hidden things cannot move"
        if under and (
            not self._is_a(parent_id, "thing") or self._is_a(parent_id, "character") or self._is_a(parent_id, "area")
        ):
            return "under needs a thing parent"
        if self._is_a(entity_id, "character") and not (
            self._is_a(parent_id, "area") or self._is_a(parent_id, "container")
        ):
            return "characters can only be in areas or containers"
        if not self._is_a(entity_id, "character") and not any(
            self._is_a(parent_id, candidate) for candidate in ("area", "container", "supporter", "character")
        ):
            return "that parent cannot hold things"
        return None

    def _relation(self, parent_id, under=False):
        if under:
            return "under"
        if self._is_a(parent_id, "character"):
            return "carried_by"
        if self._is_a(parent_id, "supporter"):
            return "on"
        return "in"

    def _write_placement(self, entity_id, parent_id, relation):
        self._replace("wk_parent", entity_id, value=parent_id)
        self._replace("wk_relation", entity_id, value=relation)
        self._replace("wk_moved", entity_id, "true")

    def _transfer_open(self, old_parent, new_parent, old_relation, new_relation):
        for parent_id, relation in ((old_parent, old_relation), (new_parent, new_relation)):
            if (
                relation == "in"
                and parent_id
                and self._entity(parent_id).openable
                and self.axis_values(parent_id).get("open") == "closed"
            ):
                self._replace_axis(parent_id, "open", "open")

    def move(self, entity_id, parent_id, *, under=False):
        """Move a normal entity, refusing invalid, hidden, fixed, or cyclic moves."""
        reason = self._check(entity_id, parent_id, under)
        if reason:
            return self._bad(reason)
        old_parent, old_relation = self.parent(entity_id), self.relation(entity_id)
        new_relation = self._relation(parent_id, under)
        self._write_placement(entity_id, parent_id, new_relation)
        self._transfer_open(old_parent, parent_id, old_relation, new_relation)
        self._move_companions(entity_id, old_parent, parent_id)
        return OpResult(True, id=entity_id)

    def _move_companions(self, entity_id, old_parent, parent_id):
        for companion_id in self.companions(entity_id):
            if self.parent(companion_id) == old_parent:
                self._write_placement(companion_id, parent_id, self._relation(parent_id))

    def place(self, entity_id, parent_id, *, text=None, under=False, part_of=False):
        """Place setup content, permitting fixed and hidden entities."""
        if not self.exists(entity_id) or not self.exists(parent_id):
            return self._bad("unknown entity")
        if self._is_a(entity_id, "area"):
            return self._bad("areas cannot be placed")
        if part_of and not self._is_a(parent_id, "thing"):
            return self._bad("part_of needs a thing parent")
        reason = self._check(entity_id, parent_id, under, True)
        if reason:
            return self._bad(reason)
        self._write_placement(entity_id, parent_id, "part_of" if part_of else self._relation(parent_id, under))
        if text is not None:
            self._replace("wk_place_text", entity_id, value=text)
        for fact in self._facts("wk_moved", entity_id):
            self.backend.retract_fact(fact)
        return OpResult(True, id=entity_id)

    def set_unplaced(self, entity_id, place_name):
        """Remove an entity's parent and record a free-text location."""
        if not self.exists(entity_id):
            return self._bad("unknown entity")
        for predicate in ("wk_parent", "wk_relation"):
            for fact in self._facts(predicate, entity_id):
                self.backend.retract_fact(fact)
        self._replace("wk_unplaced", entity_id, value=place_name)
        self._replace("wk_moved", entity_id, "true")
        return OpResult(True, id=entity_id)

    def create(self, name, parent=None, *, kind="thing", under=False, owner=None):
        """Create a thing, refusing invalid names, kinds, owners, and parents."""
        if not name or len(name) > 80:
            return self._bad("name must be 1 to 80 characters")
        if self.resolve(name):
            return self._bad("an entity already has that name")
        if kind not in self.schema.kinds or "thing" not in _ancestors(self.schema.kinds, kind):
            return self._bad("kind must be a kind of thing")
        if owner is not None and not self._is_a(owner, "character"):
            return self._bad("owner must be a character")
        if parent is not None:
            if not self.exists(parent):
                return self._bad("unknown entity")
            if not any(self._is_a(parent, candidate) for candidate in ("area", "container", "supporter", "character")):
                return self._bad("that parent cannot hold things")
            if under and not self._is_a(parent, "thing"):
                return self._bad("under needs a thing parent")
        base_id, suffix = f"n_{_slug(name)}_", 1
        while f"{base_id}{suffix}" in self._ids():
            suffix += 1
        entity_id = f"{base_id}{suffix}"
        self._replace("wk_name", entity_id, value=name)
        self._replace("wk_kind", entity_id, value=kind)
        if owner:
            self._replace("wk_owner", entity_id, value=owner)
        if parent:
            self._write_placement(entity_id, parent, self._relation(parent, under))
        return OpResult(True, id=entity_id)

    def set_axis(self, entity_id, value):
        """Set one axis pole while preserving all other axes."""
        if not self.exists(entity_id):
            return self._bad("unknown entity")
        query = value.strip().lower()
        for axis in self._axes(entity_id):
            pole = next((candidate for candidate in axis["poles"] if candidate.lower() == query), None) or next(
                (mapped for alias, mapped in axis["aliases"].items() if alias.lower() == query), None
            )
            if pole:
                self._replace_axis(entity_id, axis["name"], pole)
                return OpResult(True, id=entity_id)
        return self._bad("value does not match an axis")

    def set_conditions(self, entity_id, phrases):
        """Set at most two short ordered conditions, refusing invalid phrases."""
        if not self.exists(entity_id):
            return self._bad("unknown entity")
        cleaned = [str(phrase).strip() for phrase in phrases]
        if len(cleaned) > 2 or any(not phrase or len(phrase) > 40 for phrase in cleaned):
            return self._bad("at most two short conditions are allowed")
        for fact in self._facts("wk_condition", entity_id):
            self.backend.retract_fact(fact)
        for index, phrase in enumerate(cleaned):
            self._add("wk_condition", entity_id, str(index), phrase)
        return OpResult(True, id=entity_id)

    def set_status(self, entity_id, status):
        """Set a supported status, refusing unknown status values."""
        if not self.exists(entity_id):
            return self._bad("unknown entity")
        if status not in {"missing", "destroyed", "incapacitated"}:
            return self._bad("unknown status")
        self._replace("wk_status", entity_id, value=status)
        if status == "missing":
            self.set_unplaced(entity_id, self.unplaced_name(entity_id) or "")
        return OpResult(True, id=entity_id)

    def reveal(self, entity_id):
        """Reveal an entity, refusing unknown IDs."""
        if not self.exists(entity_id):
            return self._bad("unknown entity")
        for fact in self._facts("wk_hidden", entity_id):
            self.backend.retract_fact(fact)
        return OpResult(True, id=entity_id)

    def set_companion(self, companion_id, leader_id):
        """Set a companion's leader, refusing non-character pairs."""
        if (
            not self._is_a(companion_id, "character")
            or not self._is_a(leader_id, "character")
            or companion_id == leader_id
        ):
            return self._bad("companions must be different characters")
        self._replace("wk_companion", companion_id, leader_id)
        return OpResult(True, id=companion_id)

    def clear_companion(self, companion_id):
        """Clear a companion's leader, refusing non-characters."""
        if not self._is_a(companion_id, "character"):
            return self._bad("companion must be a character")
        for fact in self._facts("wk_companion", companion_id):
            self.backend.retract_fact(fact)
        return OpResult(True, id=companion_id)

    def apply_effects(self, effects):
        """Apply supported move, reveal, companion, and axis effects."""
        results = []
        for effect in effects:
            if "move" in effect and "parent" in effect:
                results.append(self._effect_move(effect))
            elif "reveal" in effect:
                results.append(self.reveal(effect["reveal"]))
            elif "accompany" in effect and "with" in effect:
                results.append(self.set_companion(effect["accompany"], effect["with"]))
            elif "set_axis" in effect and "value" in effect:
                results.append(self.set_axis(effect["set_axis"], effect["value"]))
            else:
                results.append(self._bad("unknown story effect"))
        return results

    def _effect_move(self, effect):
        entity_id, parent_id, under = effect["move"], effect["parent"], effect.get("under", False)
        reason = self._check(entity_id, parent_id, under, True)
        if reason:
            return self._bad(reason)
        old_parent, old_relation = self.parent(entity_id), self.relation(entity_id)
        new_relation = self._relation(parent_id, under)
        self._write_placement(entity_id, parent_id, new_relation)
        self._transfer_open(old_parent, parent_id, old_relation, new_relation)
        self._move_companions(entity_id, old_parent, parent_id)
        return OpResult(True, id=entity_id)

"""Schema and fact-backed operations for worldkeeper."""

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
    """Storage required by World."""

    def matching(self, predicate: str, subject: str | None = None) -> tuple[FactLike, ...]: ...
    def assert_fact(self, fact) -> None: ...
    def retract_fact(self, fact) -> None: ...


class MemoryBackend:
    """Simple set-backed storage."""

    def __init__(self):
        self._facts: set[Fact] = set()

    def matching(self, predicate, subject=None):
        return tuple(f for f in self._facts if f.predicate == predicate and (subject is None or f.subject == subject))

    def matching_all(self):
        return tuple(self._facts)

    def assert_fact(self, fact):
        self._facts.add(fact)

    def retract_fact(self, fact):
        self._facts.discard(fact)


class SchemaError(ValueError):
    """Invalid schema declaration."""


@dataclass
class OpResult:
    """Result of an operation."""

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


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _anc(kinds, kind):
    out = {kind}
    for p in kinds[kind]:
        out |= _anc(kinds, p)
    return out


class WorldSchema:
    """Static kinds and declared entities."""

    def __init__(self, kinds, entities):
        self.kinds, self.entities = kinds, entities

    @classmethod
    def from_data(cls, data: Mapping):
        kinds = dict(BASE_KINDS)
        rawk = list(data.get("kinds", []))
        ids = set()
        for x in rawk:
            i = x.get("id")
            if not i or i in kinds or i in ids:
                raise SchemaError("invalid or duplicate story kind")
            ids.add(i)
            kinds[i] = tuple(x.get("is", []))
        for ps in kinds.values():
            if any(p not in kinds for p in ps):
                raise SchemaError("unknown kind parent")

        def visit(k, path=()):
            if k in path:
                raise SchemaError("cycle among kinds")
            for p in kinds[k]:
                visit(p, path + (k,))

        for k in kinds:
            visit(k)
        ents = {}
        raw = list(data.get("entities", []))
        for x in raw:
            i, k = x.get("id"), x.get("kind")
            if not i or i in ents or k not in kinds:
                raise SchemaError("invalid entity declaration")
            axes = []
            for a in x.get("axes", []):
                poles = a.get("poles", [])
                if len(poles) != 2 or poles[0] == poles[1]:
                    raise SchemaError("axis needs two distinct poles")
                axes.append(
                    {
                        "name": poles[0],
                        "poles": tuple(poles),
                        "aliases": dict(a.get("aliases", {})),
                        "initial": a.get("initial", poles[0]),
                    }
                )
            ents[i] = _Entity(
                i,
                x.get("name", ""),
                k,
                tuple(x.get("aliases", [])),
                x.get("owner"),
                x.get("parent"),
                x.get("fixed", k == "furniture"),
                x.get("openable", False),
                x.get("open", False),
                x.get("captive", False),
                x.get("hidden", False),
                tuple(axes),
            )
        for e in list(ents.values()):
            if e.parent and (
                "area" not in _anc(kinds, e.kind)
                or e.parent not in ents
                or "area" not in _anc(kinds, ents[e.parent].kind)
            ):
                raise SchemaError("area parent is not an area")
            if e.owner and (e.owner not in ents or "character" not in _anc(kinds, ents[e.owner].kind)):
                raise SchemaError("unknown owner")
            item = next(x for x in raw if x.get("id") == e.id)
            for n in item.get("contents", []):
                i = f"{e.id}_{_slug(n)}"
                if i in ents:
                    raise SchemaError("duplicate expanded content")
                ents[i] = _Entity(i, n, "thing", parent=e.id)
        return cls(kinds, ents)


class World:
    """Schema view whose mutable state lives in the supplied backend."""

    def __init__(self, schema, backend, *, make_fact=Fact, resolver: Callable | None = None):
        self.schema, self.backend, self.make_fact, self.resolver = schema, backend, make_fact, resolver
        self._dynamic = set()

    def _f(self, p, s, o, v=None):
        return self.make_fact(predicate=p, subject=s, object=o, value=v)

    def _fs(self, p, s=None):
        return tuple(f for f in self.backend.matching(p, s) if f.predicate.startswith("wk_"))

    def _one(self, p, s):
        f = self._fs(p, s)
        return f[0].object if f else None

    def _set(self, p, s, o, v=None):
        for f in self._fs(p, s):
            self.backend.retract_fact(f)
        self.backend.assert_fact(self._f(p, s, o, v))

    def _add(self, p, s, o, v=None):
        if not any(f.object == o and f.value == v for f in self._fs(p, s)):
            self.backend.assert_fact(self._f(p, s, o, v))

    def _e(self, i):
        if i in self.schema.entities:
            return self.schema.entities[i]
        if i in self._ids():
            return _Entity(
                i, self._one("wk_name", i) or "", self._one("wk_kind", i) or "thing", owner=self._one("wk_owner", i)
            )
        return None

    def _isa(self, i, k):
        return bool(self._e(i) and k in _anc(self.schema.kinds, self._e(i).kind))

    def _ids(self):
        dynamic = {f.subject for f in self._fs("wk_kind")}
        return set(self.schema.entities) | self._dynamic | dynamic

    def seed(self):
        for e in self.schema.entities.values():
            if e.hidden:
                self._add("wk_hidden", e.id, "true")
            if e.parent:
                self._set("wk_parent", e.id, e.parent)
                self._set("wk_relation", e.id, "in")
            if e.openable:
                self._set("wk_axis", e.id, "open" if e.open else "closed", "open")
            if self._isa(e.id, "character"):
                self._set("wk_axis", e.id, "captive" if e.captive else "free", "captive")
            for a in e.axes:
                self._set("wk_axis", e.id, a["initial"], a["name"])
        return OpResult(True)

    def exists(self, i):
        return self._e(i) is not None

    def kind(self, i):
        return self._e(i).kind if self._e(i) else ""

    def is_a(self, i, k):
        return self._isa(i, k)

    def name(self, i):
        return self._e(i).name if self._e(i) else ""

    def owner(self, i):
        return self._e(i).owner if self._e(i) else None

    def parent(self, i):
        return self._e(i).parent if self._isa(i, "area") else self._one("wk_parent", i)

    def relation(self, i):
        return "in" if self._isa(i, "area") and self.parent(i) else self._one("wk_relation", i)

    def chain(self, i):
        out = []
        seen = set()
        p = self.parent(i)
        while p and p not in seen:
            out.append(p)
            seen.add(p)
            p = self.parent(p)
        return tuple(out)

    def area(self, i):
        return i if self._isa(i, "area") else next((x for x in self.chain(i) if self._isa(x, "area")), None)

    def holder(self, i):
        return next((x for x in self.chain(i) if self._isa(x, "character")), None)

    def together(self, a, b):
        return self.area(a) is not None and self.area(a) == self.area(b)

    def contents(self, i):
        return tuple(sorted(x for x in self._ids() if self.parent(x) == i))

    def is_hidden(self, i):
        return bool(self._fs("wk_hidden", i))

    def status(self, i):
        return self._one("wk_status", i)

    def axis_values(self, i):
        return {f.value: f.object for f in self._fs("wk_axis", i)}

    def is_visible(self, i):
        if not self.exists(i) or self.is_hidden(i) or self.status(i) == "missing":
            return False
        return not any(
            self.relation(x) == "in"
            and self.parent(x)
            and self._e(self.parent(x)).openable
            and self.axis_values(self.parent(x)).get("open") == "closed"
            for x in (i,) + self.chain(i)
        )

    def given_with(self, i):
        return (
            tuple(x for x in self.contents(i) if self.relation(x) == "in" and self.is_visible(x))
            if self._isa(i, "container") and (not self._e(i).openable or self.axis_values(i).get("open") != "closed")
            else ()
        )

    def conditions(self, i):
        return tuple(sorted(f.object for f in self._fs("wk_condition", i)))

    def unplaced_name(self, i):
        return self._one("wk_unplaced", i)

    def companions(self, i):
        return tuple(sorted(f.subject for f in self._fs("wk_companion") if f.object == i))

    def place_label(self, i):
        if not self.exists(i):
            return None
        if not any(self._fs("wk_moved", x) for x in (i,) + self.chain(i)) and self._one("wk_place_text", i):
            return self._one("wk_place_text", i)
        return self.name(self.parent(i)) if self.parent(i) else self.unplaced_name(i)

    def resolve(self, name):
        norm = lambda s: re.sub(r"^(the|a|an) ", "", s.strip().lower())
        q = norm(name)
        c = []
        for i in self._ids():
            e = self._e(i)
            forms = (e.name,) + e.aliases
            if any(norm(x) == q for x in forms):
                c.append(i)
            if self._isa(i, "area") and any(q in (norm(x) + " floor", "floor of " + norm(x)) for x in forms):
                c.append(i)
            if self._isa(i, "character") and any(q in (norm(x) + "'s hand", norm(x) + "'s hands") for x in forms):
                c.append(i)
        c = list(dict.fromkeys(c))
        if len(c) == 1:
            return c[0]
        if self.resolver:
            r = self.resolver(name, tuple(c) if c else tuple(self._ids()))
            return r if r in self._ids() else None
        return None

    def _bad(self, s):
        return OpResult(False, s)

    def _check(self, e, p, under=False, auth=False):
        if not self.exists(e) or not self.exists(p):
            return "unknown entity"
        if e == p or e in self.chain(p):
            return "that would create a cycle"
        if self._isa(e, "area"):
            return "areas cannot be moved"
        if not auth and self._e(e).fixed:
            return "fixed things cannot move"
        if not auth and self.is_hidden(e):
            return "hidden things cannot move"
        if under and (not self._isa(p, "thing") or self._isa(p, "character") or self._isa(p, "area")):
            return "under needs a thing parent"
        if self._isa(e, "character") and not (self._isa(p, "area") or self._isa(p, "container")):
            return "characters can only be in areas or containers"
        if not self._isa(e, "character") and not any(
            self._isa(p, k) for k in ("area", "container", "supporter", "character")
        ):
            return "that parent cannot hold things"

    def _rel(self, p, under=False):
        return (
            "under"
            if under
            else ("carried_by" if self._isa(p, "character") else "on" if self._isa(p, "supporter") else "in")
        )

    def _write(self, e, p, r):
        self._set("wk_parent", e, p)
        self._set("wk_relation", e, r)
        self._set("wk_moved", e, "true")

    def _transfer_open(self, old, new):
        for p in (old, new):
            if p and self._e(p).openable and self.axis_values(p).get("open") == "closed":
                self._set("wk_axis", p, "open", "open")

    def move(self, e, p, *, under=False):
        reason = self._check(e, p, under)
        if reason:
            return self._bad(reason)
        old = self.parent(e)
        self._write(e, p, self._rel(p, under))
        self._transfer_open(old, p)
        for c in self.companions(e):
            if self.parent(c) == old:
                self._write(c, p, self._rel(p))
        return OpResult(True, id=e)

    def place(self, e, p, *, text=None, under=False, part_of=False):
        if not self.exists(e) or not self.exists(p):
            return self._bad("unknown entity")
        if self._isa(e, "area"):
            return self._bad("areas cannot be placed")
        if part_of and not self._isa(p, "thing"):
            return self._bad("part_of needs a thing parent")
        if e == p or e in self.chain(p):
            return self._bad("that would create a cycle")
        reason = self._check(e, p, under, True)
        if reason:
            return self._bad(reason)
        self._write(e, p, "part_of" if part_of else self._rel(p, under))
        if text is not None:
            self._set("wk_place_text", e, text)
        for f in self._fs("wk_moved", e):
            self.backend.retract_fact(f)
        return OpResult(True, id=e)

    def set_unplaced(self, e, place_name):
        if not self.exists(e):
            return self._bad("unknown entity")
        for p in ("wk_parent", "wk_relation"):
            for f in self._fs(p, e):
                self.backend.retract_fact(f)
        self._set("wk_unplaced", e, place_name)
        self._set("wk_moved", e, "true")
        return OpResult(True, id=e)

    def create(self, name, parent_id=None, *, kind="thing", under=False, owner=None):
        if not name or len(name) > 80:
            return self._bad("name must be 1 to 80 characters")
        if self.resolve(name):
            return self._bad("an entity already has that name")
        if kind not in self.schema.kinds or "thing" not in _anc(self.schema.kinds, kind):
            return self._bad("kind must be a kind of thing")
        if owner is not None and (not self._isa(owner, "character")):
            return self._bad("owner must be a character")
        if parent_id is not None:
            if not self.exists(parent_id):
                return self._bad("unknown entity")
            if not any(self._isa(parent_id, k) for k in ("area", "container", "supporter", "character")):
                return self._bad("that parent cannot hold things")
            if under and not self._isa(parent_id, "thing"):
                return self._bad("under needs a thing parent")
        base = f"n_{_slug(name)}_"
        k = 1
        while f"{base}{k}" in self._ids():
            k += 1
        i = f"{base}{k}"
        self._dynamic.add(i)
        self._set("wk_name", i, name)
        self._set("wk_kind", i, kind)
        if owner:
            self._set("wk_owner", i, owner)
        if parent_id:
            self._write(i, parent_id, self._rel(parent_id, under))
        return OpResult(True, id=i)

    def set_axis(self, e, value):
        if not self.exists(e):
            return self._bad("unknown entity")
        axes = []
        if self._e(e).openable:
            axes.append({"name": "open", "poles": ("open", "closed"), "aliases": {}})
        if self._isa(e, "character"):
            axes.append({"name": "captive", "poles": ("captive", "free"), "aliases": {}})
        axes += list(self._e(e).axes)
        q = value.strip().lower()
        for a in axes:
            v = next((p for p in a["poles"] if p.lower() == q), None) or next(
                (x for p, x in a["aliases"].items() if p.lower() == q), None
            )
            if v:
                self._set("wk_axis", e, v, a["name"])
                return OpResult(True, id=e)
        return self._bad("value does not match an axis")

    def set_conditions(self, e, phrases):
        if not self.exists(e):
            return self._bad("unknown entity")
        p = [str(x).strip() for x in phrases]
        if len(p) > 2 or any(not x or len(x) > 40 for x in p):
            return self._bad("at most two short conditions are allowed")
        for f in self._fs("wk_condition", e):
            self.backend.retract_fact(f)
        for x in p:
            self._add("wk_condition", e, x)
        return OpResult(True, id=e)

    def set_status(self, e, status):
        if not self.exists(e):
            return self._bad("unknown entity")
        if status not in {"missing", "destroyed", "incapacitated"}:
            return self._bad("unknown status")
        self._set("wk_status", e, status)
        if status == "missing":
            self.set_unplaced(e, self.unplaced_name(e) or "")
        return OpResult(True, id=e)

    def reveal(self, e):
        if not self.exists(e):
            return self._bad("unknown entity")
        for f in self._fs("wk_hidden", e):
            self.backend.retract_fact(f)
        return OpResult(True, id=e)

    def set_companion(self, c, l):
        if not self._isa(c, "character") or not self._isa(l, "character") or c == l:
            return self._bad("companions must be different characters")
        self._set("wk_companion", c, l)
        return OpResult(True, id=c)

    def clear_companion(self, c):
        if not self._isa(c, "character"):
            return self._bad("companion must be a character")
        for f in self._fs("wk_companion", c):
            self.backend.retract_fact(f)
        return OpResult(True, id=c)

    def apply_effects(self, effects):
        out = []
        for x in effects:
            if "move" in x and "parent" in x:
                out.append(self._effect_move(x))
            elif "reveal" in x:
                out.append(self.reveal(x["reveal"]))
            elif "accompany" in x and "with" in x:
                out.append(self.set_companion(x["accompany"], x["with"]))
            elif "set_axis" in x and "value" in x:
                out.append(self.set_axis(x["set_axis"], x["value"]))
            else:
                out.append(self._bad("unknown story effect"))
        return out

    def _effect_move(self, x):
        e, p = x["move"], x["parent"]
        reason = self._check(e, p, x.get("under", False), True)
        if reason:
            return self._bad(reason)
        self._write(e, p, self._rel(p, x.get("under", False)))
        return OpResult(True, id=e)

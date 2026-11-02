"""Bounded, fact-backed incidental props and cosmetic facets."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .model import World


def _frozen_map(value, label):
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")  # noqa: TRY004
    result = {}
    for key, values in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{label} names must be non-empty strings")
        if not isinstance(values, tuple) or not values or len(set(values)) != len(values):
            raise ValueError(f"{label} values must be non-empty tuples without duplicates")
        if any(not isinstance(item, str) or not item for item in values):
            raise ValueError(f"{label} values must be non-empty strings")
        result[key] = values
    return MappingProxyType(result)


@dataclass(frozen=True)
class PropTemplate:
    """Declare a narrator-created prop and its eligible parents."""

    name: str
    parents: tuple[str, ...]
    fixed: bool = False
    facets: Mapping[str, tuple[str, ...]] = field(default_factory=dict)

    def __post_init__(self):
        if not isinstance(self.name, str) or not 1 <= len(self.name) <= 80:
            raise ValueError("name must be 1 to 80 characters")
        if (
            not isinstance(self.parents, tuple)
            or not self.parents
            or any(not isinstance(parent, str) or not parent for parent in self.parents)
        ):
            raise ValueError("parents must be a non-empty tuple of entity IDs")
        if not isinstance(self.fixed, bool):
            raise ValueError("fixed must be boolean")  # noqa: TRY004
        object.__setattr__(self, "facets", _frozen_map(self.facets, "facet"))


@dataclass(frozen=True)
class IncidentalPolicy:
    """Set the eligible incidental pool, palettes, and allowance limits."""

    templates: Mapping[str, tuple[PropTemplate, ...]]
    palettes: Mapping[str, Mapping[str, tuple[str, ...]]] = field(default_factory=dict)
    authored: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    per_turn: int = 1
    per_scene: int = 3
    per_game: int = 12
    max_facets: int = 3

    def __post_init__(self):
        if not isinstance(self.templates, Mapping):
            raise ValueError("templates must be a mapping")  # noqa: TRY004
        pools = {}
        for scene, pool in self.templates.items():
            if not isinstance(scene, str) or not isinstance(pool, tuple):
                raise ValueError("template pools must be tuples")  # noqa: TRY004
            if any(not isinstance(template, PropTemplate) for template in pool):
                raise ValueError("template pools must contain PropTemplate values")
            names = [template.name for template in pool]
            if len(names) != len(set(names)):
                raise ValueError("template names must be unique within a pool")
            pools[scene] = pool
        object.__setattr__(self, "templates", MappingProxyType(pools))
        object.__setattr__(self, "palettes", self._nested_values(self.palettes, "palette"))
        if not isinstance(self.authored, Mapping):
            raise ValueError("authored must be a mapping")  # noqa: TRY004
        authored = {}
        for entity_id, values in self.authored.items():
            if not isinstance(entity_id, str) or not isinstance(values, Mapping):
                raise ValueError("authored values must be mappings")  # noqa: TRY004
            if any(
                not isinstance(facet, str) or not facet or not isinstance(value, str) or not value
                for facet, value in values.items()
            ):
                raise ValueError("authored facets must have non-empty string values")
            authored[entity_id] = MappingProxyType(dict(values))
        object.__setattr__(self, "authored", MappingProxyType(authored))
        if any(
            not isinstance(limit, int) or limit < 0
            for limit in (self.per_turn, self.per_scene, self.per_game, self.max_facets)
        ):
            raise ValueError("policy limits must be non-negative integers")

    @staticmethod
    def _nested_values(value, label):
        if not isinstance(value, Mapping):
            raise ValueError(f"{label}s must be a mapping")  # noqa: TRY004
        result = {}
        for entity_id, values in value.items():
            if not isinstance(entity_id, str) or not isinstance(values, Mapping):
                raise ValueError(f"{label}s must map entities to mappings")  # noqa: TRY004
            result[entity_id] = _frozen_map(values, label)
        return MappingProxyType(result)


@dataclass(frozen=True)
class PropProposal:
    """Request a template-named prop under a readable parent name."""

    template: str
    parent: str


@dataclass(frozen=True)
class TraitProposal:
    """Request one cosmetic facet on a readable target name."""

    target: str
    facet: str
    value: str


@dataclass(frozen=True)
class EmbellishResult:
    """Report an accepted or refused embellishment batch."""

    ok: bool
    reason: str = ""
    created: tuple[str, ...] = ()
    traits: tuple[tuple[str, str, str], ...] = ()


class IncidentalWorldMixin:
    """World operations for constrained incidental content."""

    def is_incidental(self: "World", entity_id: str) -> bool:
        """Return whether an entity has incidental provenance."""
        return bool(self._facts("wk_incidental", entity_id))

    def origin(self: "World", entity_id: str) -> tuple[str, str] | None:
        """Return an incidental entity's scene and template, if any."""
        fact = next(iter(self._facts("wk_incidental", entity_id)), None)
        return (fact.object, fact.value) if fact else None

    def facets(self: "World", entity_id: str) -> dict[str, str]:
        """Return only stored cosmetic facets for an entity."""
        return {fact.object: fact.value for fact in self._facts("wk_facet", entity_id) if fact.object and fact.value}

    def incidental_counts(self: "World", scene_id: str) -> tuple[int, int]:
        """Return lifetime incidental counts for a scene and the whole game."""
        facts = self._facts("wk_incidental")
        return sum(fact.object == scene_id for fact in facts), len(facts)

    def check_embellishments(self, policy, scene_id, props, traits) -> EmbellishResult:
        """Validate a complete batch without changing this world's backend."""
        scratch = self.__class__(self.schema, self.backend.clone(), make_fact=self.make_fact, resolver=None)
        return scratch._run_embellishments(policy, scene_id, tuple(props), tuple(traits))

    def apply_embellishments(self, policy, scene_id, props, traits) -> EmbellishResult:
        """Validate and atomically commit a complete embellishment batch."""
        props, traits = tuple(props), tuple(traits)
        checked = self.check_embellishments(policy, scene_id, props, traits)
        if not checked.ok:
            return checked
        applied = type(self)(self.schema, self.backend, make_fact=self.make_fact, resolver=None)
        return applied._run_embellishments(policy, scene_id, props, traits)

    def _run_embellishments(self, policy, scene_id, props, traits):
        if len(props) > policy.per_turn:
            return EmbellishResult(False, "turn allowance exceeded")
        scene_count, game_count = self.incidental_counts(scene_id)
        if scene_count + len(props) > policy.per_scene:
            return EmbellishResult(False, "scene allowance exceeded")
        if game_count + len(props) > policy.per_game:
            return EmbellishResult(False, "game allowance exceeded")
        pool = {template.name: template for template in policy.templates.get(scene_id, ())}
        if len(props) and not pool:
            return EmbellishResult(False, "unknown scene")
        templates = []
        for proposal in props:
            if not isinstance(proposal, PropProposal) or proposal.template not in pool:
                return EmbellishResult(False, "template is not eligible")
            template = pool[proposal.template]
            if any(fact.value == template.name for fact in self._facts("wk_incidental") if fact.object == scene_id):
                return EmbellishResult(False, "template already used")
            if self._name_collision(template.name):
                return EmbellishResult(False, "template name already exists")
            templates.append(template)
        if len({template.name for template in templates}) != len(templates):
            return EmbellishResult(False, "template already used in batch")
        created = []
        for proposal, template in zip(props, templates):
            parent_id = self.resolve(proposal.parent)
            if not parent_id or parent_id in created or parent_id not in template.parents:
                return EmbellishResult(False, "invalid parent")
            if not self._available_parent(parent_id):
                return EmbellishResult(False, "invalid parent")
            made = self.create(template.name, parent=parent_id)
            if not made.ok:
                return EmbellishResult(False, made.reason)
            created.append(made.id)
            self._add("wk_incidental", made.id, scene_id, template.name)
            if template.fixed:
                self._add("wk_fixed", made.id, "true")
        trait_result = self._apply_traits(policy, scene_id, traits, created, templates)
        if not trait_result[0]:
            return EmbellishResult(False, trait_result[1])
        return EmbellishResult(True, created=tuple(created), traits=tuple(trait_result[2]))

    def _name_collision(self, name):
        normalized = self._normalize(name)
        return any(
            self._normalize(candidate) == normalized for entity_id in self._ids() for candidate in self.names(entity_id)
        )

    def _available_parent(self, parent_id):
        return (
            self.exists(parent_id)
            and self.is_visible(parent_id)
            and self.open_state(parent_id) != "closed"
            and not self.contents_complete(parent_id)
            and any(self._is_a(parent_id, kind) for kind in ("area", "container", "supporter", "character"))
        )

    def _apply_traits(self, policy, scene_id, traits, created, templates):
        by_id = dict(zip(created, templates))
        added = []
        for proposal in traits:
            if not isinstance(proposal, TraitProposal):
                return False, "invalid trait", added
            target = self.resolve(proposal.target)
            if not target:
                return False, "unknown trait target", added
            authored = policy.authored.get(target, {}).get(proposal.facet)
            if authored is not None:
                if authored != proposal.value:
                    return False, "facet already has another value", added
                continue
            palette = self._trait_palette(policy, target, by_id, scene_id)
            allowed = palette.get(proposal.facet)
            if not allowed or proposal.value not in allowed:
                return False, "trait is not in the palette", added
            stored = self.facets(target).get(proposal.facet)
            current = authored if authored is not None else stored
            if current is not None:
                if current != proposal.value:
                    return False, "facet already has another value", added
                continue
            if len(set(policy.authored.get(target, {})) | set(self.facets(target))) >= policy.max_facets:
                return False, "facet limit exceeded", added
            self._add("wk_facet", target, proposal.facet, proposal.value)
            added.append((proposal.target, proposal.facet, proposal.value))
        return True, "", added

    def _trait_palette(self, policy, target, created, scene_id):
        template = created.get(target)
        if template:
            return template.facets
        if self.is_incidental(target):
            origin = self.origin(target)
            if origin:
                return next((item.facets for item in policy.templates.get(origin[0], ()) if item.name == origin[1]), {})
            return {}
        return policy.palettes.get(target, {})

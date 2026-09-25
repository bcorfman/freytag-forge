"""Immutable contracts for a Markdown story package."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ID = r"^[a-z][a-z0-9_]*$"
_SCENE_ID = r"^[1-9][A-Z]$"


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class FactPredicate(_Model):
    """A declarative predicate over a committed fact."""

    fact_id: str = Field(pattern=_ID)
    equals: str | bool | int | None = None


class ActivationRule(_Model):
    all_facts_true: tuple[str, ...] = ()
    any_of: tuple[str, ...] = ()
    at_least: int = 0

    def is_satisfied(self, true_facts):
        return all(fact_id in true_facts for fact_id in self.all_facts_true) and (
            not self.any_of or sum(fact_id in true_facts for fact_id in self.any_of) >= self.at_least
        )

    def minimal_undelivered_facts(self, true_facts):
        """Return the smallest stable set of facts which completes this rule."""

        known = set(true_facts)
        selected: list[str] = []
        for fact_id in self.all_facts_true:
            if fact_id not in known and fact_id not in selected:
                selected.append(fact_id)
        pool_count = sum(fact_id in known for fact_id in self.any_of)
        pool_count += sum(fact_id in self.any_of for fact_id in selected)
        needed = max(0, self.at_least - pool_count)
        for fact_id in self.any_of:
            if needed == 0:
                break
            if fact_id not in known and fact_id not in selected:
                selected.append(fact_id)
                needed -= 1
        return tuple(selected)


class FactDefinition(_Model):
    """A named world predicate and its authoring purpose."""

    id: str = Field(pattern=_ID)
    purpose: str = Field(min_length=1)


class Audience(_Model):
    """The only audiences a declarative revelation may address."""

    kind: Literal["public", "characters", "world_only"]
    character_ids: tuple[str, ...] = ()
    player_visible: bool = False

    @model_validator(mode="after")
    def explicit_character_scope(self) -> Audience:
        if self.kind == "characters" and not self.character_ids:
            raise ValueError("character audience requires character_ids")
        if self.kind != "characters" and self.character_ids:
            raise ValueError("only character audiences may name character_ids")
        if self.kind == "world_only" and self.player_visible:
            raise ValueError("world-only knowledge cannot be player-visible")
        return self


class RevealSource(_Model):
    """One package-owned route that may establish knowledge."""

    kind: Literal["storylet_realization", "canonical_route_event", "scene_entry"]
    storylet_id: str | None = None
    realization_id: str | None = None
    canonical_event_id: str | None = None

    @model_validator(mode="after")
    def complete_route_reference(self) -> RevealSource:
        route_fields = (self.storylet_id, self.realization_id)
        if self.kind == "storylet_realization" and not all(route_fields):
            raise ValueError("storylet realization source requires storylet_id and realization_id")
        if self.kind == "storylet_realization" and self.canonical_event_id:
            raise ValueError("storylet realization source cannot name a canonical route event")
        if self.kind == "canonical_route_event" and (not self.canonical_event_id or any(route_fields)):
            raise ValueError("canonical route event source requires only canonical_event_id")
        if self.kind == "scene_entry" and (any(route_fields) or self.canonical_event_id):
            raise ValueError("scene entry source cannot name another source")
        return self


class Relevance(_Model):
    entity_ids: tuple[str, ...] = ()
    priority: int = 0


class KnowledgeDefinition(_Model):
    """A player-safe claim whose truth is derived only from its fact effects."""

    id: str = Field(pattern=_ID)
    statement: str = Field(min_length=1)
    entity_ids: tuple[str, ...] = ()
    aliases: tuple[str, ...] = Field(min_length=1)
    audience: Audience
    available_in_scenes: tuple[str, ...] = Field(min_length=1)
    requires: tuple[FactPredicate, ...] = ()
    establishes: tuple[RouteOperation, ...] = Field(min_length=1)
    source: RevealSource
    relevance: Relevance = Field(default_factory=Relevance)
    earn_when: str | None = Field(default=None, min_length=1)
    action_evidence: tuple[tuple[str, ...], ...] = ()
    must_convey: tuple[tuple[str, ...], ...] = ()
    delivery_text: str | None = None


class SceneFrame(_Model):
    """A concise, explicitly player-safe immediate scene situation."""

    scene_id: str = Field(pattern=_SCENE_ID)
    situation: str = Field(min_length=1)
    pressure: str = Field(min_length=1)


class KnowledgeCatalog(_Model):
    """Versioned knowledge source interpreted consistently by saves and runtime."""

    schema_version: Literal["2.0"]
    facts: tuple[FactDefinition, ...] = Field(min_length=1)
    scene_frames: tuple[SceneFrame, ...] = Field(min_length=1)
    knowledge: tuple[KnowledgeDefinition, ...] = Field(min_length=1)


class KnowledgeIndexes(_Model):
    """Immutable lookup tables compiled once at package load time."""

    by_id: Mapping[str, KnowledgeDefinition]
    facts_to_knowledge: Mapping[str, tuple[str, ...]]
    source_to_knowledge: Mapping[str, tuple[str, ...]]
    scene_to_candidates: Mapping[str, tuple[str, ...]]
    alias_to_knowledge: Mapping[str, tuple[str, ...]]
    audience_to_known_terms: Mapping[str, tuple[str, ...]]
    prerequisite_dependents: Mapping[str, tuple[str, ...]]
    entity_alias_to_entities: Mapping[str, tuple[str, ...]] = {}
    term_to_knowledge: Mapping[str, tuple[str, ...]] = {}
    protected_terms: tuple[str, ...] = ()


class Entity(_Model):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    fallback_ids: tuple[str, ...] = ()
    # plot.md biographies are written for a reader who already knows the ending, so a
    # character's own concealed history can sit inside the paragraph that introduces
    # them. Setting this replaces that paragraph for prompt purposes only; plot.md
    # remains narrative ground truth and is never edited to accommodate the narrator.
    narrator_bio: str | None = None


class Location(Entity):
    parent: str | None = Field(default=None, pattern=_ID)


class Item(Entity):
    # A fixed thing is furniture or part of the scene, so the engine keeps its authored place.
    fixed: bool | None = None
    kind: str = Field(default="thing", pattern=_ID)
    openable: bool = False
    open: bool = False
    hidden: bool = False
    contents: list[str] = Field(default_factory=list)
    owner: str | None = Field(default=None, pattern=_ID)


class WorldEffect(_Model):
    move: str | None = Field(default=None, pattern=_ID)
    parent: str | None = Field(default=None, pattern=_ID)
    text: str | None = Field(default=None, min_length=1)
    under: bool = False
    reveal: str | None = Field(default=None, pattern=_ID)
    accompany: str | None = Field(default=None, pattern=_ID)
    with_: str | None = Field(default=None, alias="with", pattern=_ID)
    set_axis: str | None = Field(default=None, pattern=_ID)
    value: str | None = None

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)

    @model_validator(mode="after")
    def one_shape(self) -> WorldEffect:
        values = self.model_dump(exclude_none=True, exclude_defaults=True, by_alias=True)
        if self.move is not None:
            valid = set(values) <= {"move", "parent", "text", "under"} and self.parent is not None
        elif self.reveal is not None:
            valid = set(values) == {"reveal"}
        elif self.accompany is not None:
            valid = set(values) == {"accompany", "with"} and self.with_ is not None
        elif self.set_axis is not None:
            valid = set(values) == {"set_axis", "value"} and self.value is not None
        else:
            valid = False
        if not valid:
            raise ValueError("world effect must use exactly one supported shape")
        return self


_LEADING_DETERMINERS = frozenset({"the", "a", "an", "this", "that", "her", "his", "their", "its"})


def normalize_term(value: str) -> str:
    """Remove one leading determiner from a multi-word lookup phrase."""

    words = value.casefold().split()
    if len(words) > 1 and words[0] in _LEADING_DETERMINERS:
        return " ".join(words[1:])
    return value.casefold()


def term_lookup_forms(value: str) -> tuple[str, ...]:
    """Return the exact and determiner-normalized forms for an index lookup."""

    folded = value.casefold()
    normalized = normalize_term(value)
    if normalized == folded:
        return (folded,)
    return (folded, normalized)


def entity_surface_forms(entity: Entity) -> tuple[str, ...]:
    """Return authored display-name and alias forms for deterministic screening."""

    forms = {entity.name.casefold(), *(alias.casefold() for alias in entity.aliases)}
    return tuple(sorted(form for form in forms if form))


class ItemPlacement(_Model):
    placement: str | None = Field(default=None, min_length=1)
    while_fact_false: str | None = Field(default=None, pattern=_ID)
    while_fact_true: str | None = Field(default=None, pattern=_ID)
    parent: str | None = Field(default=None, pattern=_ID)
    text: str | None = Field(default=None, min_length=1)
    under: bool = False
    part_of: bool = False

    @model_validator(mode="after")
    def one_visibility_guard(self) -> ItemPlacement:
        old_form = self.placement is not None
        new_form = self.parent is not None
        if old_form == new_form:
            raise ValueError("item placement must use exactly one of placement or parent")
        if old_form and (self.text is not None or self.under or self.part_of):
            raise ValueError("old-form item placement cannot use text, under, or part_of")
        if new_form and (self.while_fact_false is not None or self.while_fact_true is not None):
            raise ValueError("new-form item placement cannot use visibility guards")
        if self.under and self.part_of:
            raise ValueError("item placement cannot be both under and part_of")
        if self.while_fact_false is not None and self.while_fact_true is not None:
            raise ValueError("item placement may have at most one visibility guard")
        return self


def placement_text(placement: str | ItemPlacement) -> str | None:
    if isinstance(placement, str):
        return placement
    return placement.placement if placement.placement is not None else placement.text


def item_placement_is_visible(placement: str | ItemPlacement, facts) -> bool:
    """Return whether a placement is visible under the supplied fact store."""

    if isinstance(placement, str):
        return True
    true_facts = {
        fact.predicate for fact in facts.asserted if (fact.value if fact.value is not None else fact.object) == "true"
    }
    if placement.while_fact_false is not None:
        return placement.while_fact_false not in true_facts
    if placement.while_fact_true is not None:
        return placement.while_fact_true in true_facts
    return True


class Character(_Model):
    """One principal character and the biography the narrator may be told."""

    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1)
    bio: str = Field(min_length=1)


class KindDeclaration(_Model):
    id: str = Field(pattern=_ID)
    is_: tuple[str, ...] = Field(default=(), alias="is")

    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class WorldSource(_Model):
    story_id: str = Field(pattern=_ID)
    protagonist_id: str = Field(pattern=_ID)
    locations: tuple[Location, ...]
    npcs: tuple[Entity, ...]
    items: tuple[Item, ...]
    kinds: tuple[KindDeclaration, ...] = ()
    facts: tuple[str, ...] = ()
    fact_effects: Mapping[str, tuple[WorldEffect, ...]] = {}
    protected_knowledge: tuple[str, ...] = ()

    @model_validator(mode="before")
    @classmethod
    def split_fact_effects(cls, data):
        if not isinstance(data, Mapping):
            return data
        values = dict(data)
        if "facts" not in values:
            return values
        facts = []
        effects = dict(values.get("fact_effects", {}))
        for entry in values.get("facts", ()):
            if isinstance(entry, str):
                facts.append(entry)
            elif isinstance(entry, Mapping):
                fact_id = entry.get("id")
                facts.append(fact_id)
                effects[fact_id] = entry.get("on_assert", ())
            else:
                facts.append(entry)
        values["facts"] = facts
        values["fact_effects"] = effects
        return values


class SceneMetadata(_Model):
    scene_id: str = Field(pattern=_SCENE_ID)
    location_id: str = Field(pattern=_ID)
    freytag_phase: Literal[
        "exposition", "inciting_incident", "rising_action", "crisis", "climax", "falling_action", "resolution"
    ]
    objective: str = Field(min_length=1)
    participant_ids: tuple[str, ...] = ()
    item_ids: tuple[str, ...] = ()
    entry_text: str = Field(min_length=1)
    transition_ids: tuple[str, ...] = ()
    bridge_text: Mapping[str, str] = {}
    item_placements: Mapping[str, str | ItemPlacement] = {}
    setting_facts: tuple[str, ...] = ()

    @field_validator("setting_facts")
    @classmethod
    def non_blank_setting_facts(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(not value.strip() for value in values):
            raise ValueError("setting_facts entries must not be empty or whitespace-only")
        return values


class SceneBeat(_Model):
    """One authored sub-beat of a scene and its concrete delivery details."""

    id: str = Field(pattern=r"^[1-9][A-Z]\.[1-9]$")
    anchor: str = Field(pattern=r"^[a-z0-9-]+$")
    title: str = Field(min_length=1)
    prose: str = Field(min_length=1)
    details: tuple[str, ...] = Field(min_length=3, max_length=7)


class Scene(_Model):
    metadata: SceneMetadata
    prose: str = Field(min_length=1)
    beats: Mapping[str, SceneBeat]
    opening_beat: SceneBeat


class Transition(_Model):
    id: str = Field(pattern=_ID)
    source_scene_id: str = Field(pattern=_SCENE_ID)
    target_scene_id: str = Field(pattern=_SCENE_ID)
    priority: int = Field(ge=0)
    triggers: tuple[FactPredicate, ...] = Field(min_length=1)
    required_dependencies: tuple[str, ...] = ()


class ScenePacing(_Model):
    scene_id: str = Field(pattern=_SCENE_ID)
    min_turns: int = Field(ge=0)
    nudge_after_turns: int = Field(ge=1)
    handoff_after_turns: int = Field(ge=1)

    @model_validator(mode="after")
    def ordered(self) -> ScenePacing:
        if not self.min_turns <= self.nudge_after_turns <= self.handoff_after_turns:
            raise ValueError("pacing turn allocations must be ordered")
        return self


class PacingRealization(_Model):
    """One player-safe, observable realization of a pacing event."""

    when: tuple[FactPredicate, ...] = ()
    text: str = Field(min_length=1)

    @field_validator("text")
    @classmethod
    def non_blank_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("text must not be empty")
        return value


class PacingEvent(_Model):
    """A package-declared, deterministic deadline complication."""

    id: str = Field(pattern=_ID)
    scene_id: str = Field(pattern=_SCENE_ID)
    at_turn: int = Field(ge=0)
    when: tuple[FactPredicate, ...] = Field(
        default=(), description="Conditions that must also hold before the event fires."
    )
    effects: tuple[FactPredicate, ...] = Field(min_length=1)
    transition_id: str | None = Field(default=None, pattern=_ID)
    realizations: tuple[PacingRealization, ...] = ()


class PacingSource(_Model):
    budget_seconds: int = Field(ge=0)
    scenes: tuple[ScenePacing, ...]
    transitions: tuple[Transition, ...]
    events: tuple[PacingEvent, ...] = ()


class Storylet(_Model):
    id: str = Field(pattern=r"^SL-[1-9][A-Z]-[A-Z]$")
    scene_id: str = Field(pattern=_SCENE_ID)
    title: str = Field(min_length=1)
    source_links: tuple[str, ...] = Field(min_length=1)
    sections: dict[str, str]
    earliest_turn: int = Field(ge=0)
    target_turn: int = Field(ge=0)
    latest_turn: int = Field(ge=0)

    @model_validator(mode="after")
    def ordered(self) -> Storylet:
        if not self.earliest_turn <= self.target_turn <= self.latest_turn:
            raise ValueError("storylet turn offsets must be ordered")
        return self


class RouteOperation(_Model):
    op: Literal["assert", "retract"]
    fact_id: str = Field(pattern=_ID)
    value: str | bool | int | None = None


class FactDelivery(_Model):
    """A diegetic, player-safe way to carry an unearned fact forward."""

    fact_id: str = Field(pattern=_ID)
    scene_id: str = Field(pattern=_SCENE_ID)
    source_kind: Literal["message", "npc", "broadcast", "observation", "inference"]
    source_entity_id: str | None = None
    must_convey: tuple[tuple[str, ...], ...] = Field(min_length=2)
    fallback_text: str = Field(min_length=1)
    cue_text: str | None = None
    costs: tuple[RouteOperation, ...] = ()

    @field_validator("cue_text")
    @classmethod
    def non_empty_cue_text(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("cue_text must not be empty")
        return value


class RouteRealization(_Model):
    id: str = Field(min_length=1)
    dramatic_intent: str = Field(min_length=1)
    source_beats: tuple[str, ...] = ()
    operations: tuple[RouteOperation, ...] = ()
    eligible_storylet_event_id: str | None = None
    helps_transition_triggers: tuple[str, ...] = ()
    protected_knowledge_boundaries: tuple[str, ...] = ()


class StoryletRoute(_Model):
    id: str = Field(pattern=r"^SL-[1-9][A-Z]-[A-Z]$")
    scene_id: str = Field(pattern=_SCENE_ID)
    title: str = Field(min_length=1)
    activation_conditions: tuple[FactPredicate, ...] = ()
    earliest_turn: int = Field(ge=0)
    target_turn: int = Field(ge=0)
    latest_turn: int = Field(ge=0)
    pressure_role: str = Field(min_length=1)
    realizations: tuple[RouteRealization, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def ordered(self) -> StoryletRoute:
        if not self.earliest_turn <= self.target_turn <= self.latest_turn:
            raise ValueError("storylet route turn offsets must be ordered")
        return self


class CanonicalRouteEvent(_Model):
    id: str = Field(min_length=1)
    scene_id: str = Field(pattern=_SCENE_ID)
    activation: ActivationRule
    operations: tuple[RouteOperation, ...] = Field(min_length=1)
    realization_storylets: tuple[str, ...] = ()
    fallback_text: str | None = None


class StoryletRoutesSource(_Model):
    story_id: str = Field(pattern=_ID)
    canonical_scene_chain: tuple[str, ...] = Field(min_length=1)
    sole_ending_scene_id: str = Field(pattern=_SCENE_ID)
    storylets: tuple[StoryletRoute, ...]
    bridge_events: tuple[CanonicalRouteEvent, ...] = ()
    resolution_events: tuple[CanonicalRouteEvent, ...] = ()


class StoryPackage(_Model):
    """The immutable input to the future scene runtime."""

    story_id: str = Field(pattern=_ID)
    protagonist_id: str = Field(pattern=_ID)
    genre: str = ""
    characters: tuple[Character, ...] = ()
    scenes: tuple[Scene, ...]
    world: WorldSource
    pacing: PacingSource
    storylets: tuple[Storylet, ...]
    storylet_routes: StoryletRoutesSource
    knowledge: KnowledgeCatalog
    knowledge_indexes: KnowledgeIndexes
    deliveries: tuple[FactDelivery, ...]

    @property
    def fact_ids(self) -> frozenset[str]:
        return frozenset(self.world.facts)

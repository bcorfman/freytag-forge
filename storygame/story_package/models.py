"""Immutable contracts for a Markdown story package."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

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
    must_convey: tuple[tuple[str, ...], ...] = ()


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


class Entity(_Model):
    id: str = Field(pattern=_ID)
    name: str = Field(min_length=1)
    aliases: tuple[str, ...] = ()
    fallback_ids: tuple[str, ...] = ()


class WorldSource(_Model):
    story_id: str = Field(pattern=_ID)
    protagonist_id: str = Field(pattern=_ID)
    locations: tuple[Entity, ...]
    npcs: tuple[Entity, ...]
    items: tuple[Entity, ...]
    facts: tuple[str, ...] = ()
    protected_knowledge: tuple[str, ...] = ()


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


class SceneBeat(_Model):
    """One authored sub-beat of a scene, quoted verbatim as narration context."""

    id: str = Field(pattern=r"^[1-9][A-Z]\.[1-9]$")
    title: str = Field(min_length=1)
    prose: str = Field(min_length=1)


class Scene(_Model):
    metadata: SceneMetadata
    prose: str = Field(min_length=1)
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


class PacingEvent(_Model):
    """A package-declared, deterministic deadline complication."""

    id: str = Field(pattern=_ID)
    scene_id: str = Field(pattern=_SCENE_ID)
    at_turn: int = Field(ge=0)
    effects: tuple[FactPredicate, ...] = Field(min_length=1)
    transition_id: str | None = Field(default=None, pattern=_ID)


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
    pacing_impact: Literal["none", "brief_delay", "pressure_increase", "advance_readiness"]

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
    costs: tuple[RouteOperation, ...] = ()


class RouteRealization(_Model):
    id: str = Field(min_length=1)
    dramatic_intent: str = Field(min_length=1)
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

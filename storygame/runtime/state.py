"""Canonical scene runtime state and durable game-break decisions."""

from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator

from storygame.runtime.contracts import FactOperation, GameBreakWarning, ResolvedTurnProposal
from storygame.runtime.facts import Fact, FactStore
from storygame.story_package.models import StoryPackage

SNAPSHOT_VERSION = 2


class RuntimeStateError(ValueError):
    """Raised for invalid state transitions or unresolved game breaks."""


class TurnRecord(BaseModel):
    """Bounded fact-derived continuity; display prose is intentionally excluded."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    id: str
    reveal_ids: tuple[str, ...] = ()
    affected_entity_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    transition_id: str | None = None
    fact_keys: tuple[str, ...] = ()


class TurnDelivery(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    beats_projected: tuple[str, ...] = ()
    must_convey_misses: tuple[str, ...] = ()
    recovery_used: bool = False
    fallback_used: bool = False
    hint_staged: bool = False
    handoff_staged: bool = False


class RuntimeSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: int = Field(default=SNAPSHOT_VERSION, ge=1)
    current_scene_id: str
    phase: str
    active_event_ids: tuple[str, ...]
    fired_event_ids: tuple[str, ...]
    facts: FactStore
    turn_index: int = Field(ge=0)
    scene_entered_at_turn: int = Field(ge=0)
    narrative_history: tuple[str, ...] = ()
    turn_records: tuple[TurnRecord, ...] = ()
    staged_hint_fact_ids: tuple[str, ...] = ()
    staged_handoff_fact_ids: tuple[str, ...] = ()


class RuntimeState(BaseModel):
    """The mutable session authority; package data is always immutable input."""

    model_config = ConfigDict(extra="forbid")
    package: StoryPackage
    current_scene_id: str
    phase: str
    active_event_ids: set[str] = Field(default_factory=set)
    fired_event_ids: set[str] = Field(default_factory=set)
    facts: FactStore = Field(default_factory=FactStore)
    turn_index: int = Field(default=0, ge=0)
    scene_entered_at_turn: int = Field(default=0, ge=0)
    narrative_history: list[str] = Field(default_factory=list)
    turn_records: list[TurnRecord] = Field(default_factory=list)
    pending_break: GameBreakWarning | None = None
    pending_snapshot: RuntimeSnapshot | None = None
    pending_proposal: ResolvedTurnProposal | None = None
    staged_hint_fact_ids: tuple[str, ...] = ()
    staged_handoff_fact_ids: tuple[str, ...] = ()
    last_turn_delivery: TurnDelivery = TurnDelivery()

    @model_validator(mode="after")
    def scene_and_phase_match_package(self) -> RuntimeState:
        scene = next((item for item in self.package.scenes if item.metadata.scene_id == self.current_scene_id), None)
        if scene is None:
            raise ValueError("current scene is not in the story package")
        if self.phase != scene.metadata.freytag_phase:
            raise ValueError("phase must match the current scene")
        if (self.pending_break is None) != (self.pending_snapshot is None):
            raise ValueError("a pending break requires exactly one pre-action snapshot")
        if (self.pending_break is None) != (self.pending_proposal is None):
            raise ValueError("a pending break requires exactly one candidate proposal")
        return self

    @classmethod
    def bootstrap(cls, package: StoryPackage) -> RuntimeState:
        first = package.scenes[0].metadata
        state = cls(package=package, current_scene_id=first.scene_id, phase=first.freytag_phase)
        state._assert_scene_entry_fact(first.scene_id)
        return state

    @property
    def has_pending_break(self) -> bool:
        return self.pending_break is not None

    def require_turn_allowed(self) -> None:
        if self.has_pending_break:
            raise RuntimeStateError("resolve the pending game break with proceed or return_to_scene")

    def snapshot(self) -> RuntimeSnapshot:
        return RuntimeSnapshot(
            current_scene_id=self.current_scene_id,
            phase=self.phase,
            active_event_ids=tuple(sorted(self.active_event_ids)),
            fired_event_ids=tuple(sorted(self.fired_event_ids)),
            facts=self.facts.clone(),
            turn_index=self.turn_index,
            scene_entered_at_turn=self.scene_entered_at_turn,
            narrative_history=tuple(self.narrative_history),
            turn_records=tuple(self.turn_records),
            staged_hint_fact_ids=self.staged_hint_fact_ids,
            staged_handoff_fact_ids=self.staged_handoff_fact_ids,
        )

    def set_pending_break(
        self,
        warning: GameBreakWarning,
        *,
        snapshot: RuntimeSnapshot | None = None,
        proposal: ResolvedTurnProposal | None = None,
    ) -> None:
        self.require_turn_allowed()
        if warning.snapshot_id == "":
            raise RuntimeStateError("game break requires a snapshot ID")
        self.pending_snapshot = snapshot or self.snapshot()
        self.pending_break = warning
        self.pending_proposal = proposal or ResolvedTurnProposal(
            segments=({"kind": "narration", "text": "Pending game-break candidate."},)
        )

    def apply_proposal(self, proposal: ResolvedTurnProposal, *, canonical_event_ids: tuple[str, ...] = ()) -> None:
        """Validate a complete candidate before replacing canonical session state.

        A warning intentionally commits no candidate facts: only the explicit
        ``proceed`` decision may allow later progression to continue.
        """

        self.require_turn_allowed()
        before = self.snapshot()
        candidate_facts = self.facts.clone()
        candidate_active = set(self.active_event_ids)
        candidate_fired = set(self.fired_event_ids)
        canonical_events = {
            event.id: event
            for event in (*self.package.storylet_routes.bridge_events, *self.package.storylet_routes.resolution_events)
        }
        for event_id in canonical_event_ids:
            event = canonical_events.get(event_id)
            if event is None or event.scene_id != self.current_scene_id or event_id in candidate_fired:
                raise RuntimeStateError("canonical event is not eligible")
            candidate_fired.add(event_id)
        for operation in proposal.operations:
            self._apply_operation(candidate_facts, operation)
        for event in proposal.events:
            if event.event_id not in candidate_active or event.event_id in candidate_fired:
                raise RuntimeStateError("event is not eligible")
            for operation in event.operations:
                self._apply_operation(candidate_facts, operation)
            candidate_active.remove(event.event_id)
            candidate_fired.add(event.event_id)
        next_scene_id = self.current_scene_id
        next_phase = self.phase
        if proposal.transition:
            transition = next(
                (item for item in self.package.pacing.transitions if item.id == proposal.transition.transition_id), None
            )
            if transition is None or transition.source_scene_id != self.current_scene_id:
                raise RuntimeStateError("transition is not valid from the current scene")
            scene = next(item for item in self.package.scenes if item.metadata.scene_id == transition.target_scene_id)
            next_scene_id, next_phase = scene.metadata.scene_id, scene.metadata.freytag_phase
        if proposal.game_break:
            self.set_pending_break(
                proposal.game_break, snapshot=before, proposal=proposal.model_copy(update={"game_break": None})
            )
            return
        self.facts = candidate_facts
        self.active_event_ids = candidate_active
        self.fired_event_ids = candidate_fired
        changed_scene = next_scene_id != self.current_scene_id
        self.current_scene_id = next_scene_id
        self.phase = next_phase
        if changed_scene:
            self.active_event_ids.clear()
            self._assert_scene_entry_fact(next_scene_id)

    def _assert_scene_entry_fact(self, scene_id: str) -> None:
        """Commit the typed scene-entry reveal before any opening can render."""

        self.scene_entered_at_turn = self.turn_index
        self.staged_hint_fact_ids = ()
        self.staged_handoff_fact_ids = ()
        self.facts.assert_fact(Fact(predicate=f"scene_{scene_id.lower()}_entry_known", subject="story", value="true"))

    @staticmethod
    def _apply_operation(store: FactStore, operation: FactOperation) -> None:
        if operation.operation == "assert":
            store.assert_fact(operation.fact)
        elif operation.operation == "retract":
            store.retract_fact(operation.fact)

    def resolve_break(self, decision: str) -> None:
        if not self.pending_break or not self.pending_snapshot or not self.pending_proposal:
            raise RuntimeStateError("there is no pending game break")
        if decision == "return_to_scene":
            snapshot = self.pending_snapshot
            self.current_scene_id = snapshot.current_scene_id
            self.phase = snapshot.phase
            self.active_event_ids = set(snapshot.active_event_ids)
            self.fired_event_ids = set(snapshot.fired_event_ids)
            self.facts = snapshot.facts.clone()
            self.turn_index = snapshot.turn_index
            self.scene_entered_at_turn = snapshot.scene_entered_at_turn
            self.narrative_history = list(snapshot.narrative_history)
            self.turn_records = list(snapshot.turn_records)
            self.staged_hint_fact_ids = snapshot.staged_hint_fact_ids
            self.staged_handoff_fact_ids = snapshot.staged_handoff_fact_ids
        elif decision != "proceed":
            raise RuntimeStateError("game break decision must be proceed or return_to_scene")
        else:
            candidate = self.pending_proposal
            self.pending_break = None
            self.pending_snapshot = None
            self.pending_proposal = None
            self.apply_proposal(candidate)
            return
        self.pending_break = None
        self.pending_snapshot = None
        self.pending_proposal = None

    def new_snapshot_id(self) -> str:
        return f"snapshot_{uuid4().hex}"

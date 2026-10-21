"""LLM-first turn coordinator; it normalizes player commands before narration."""

from __future__ import annotations

import re
from copy import deepcopy
from os import getenv
from typing import Protocol, runtime_checkable

from storygame.runtime.attempt_bundle import (
    AttemptBundle,
    AttemptCommand,
    AttemptError,
    AttemptIdentity,
    AttemptPreState,
    CommittedDelta,
    CueStage,
    ModelStage,
    RevealSelection,
    SelectedReveal,
)
from storygame.runtime.canonical_events import CanonicalEventMixin
from storygame.runtime.capture import WorldCapture
from storygame.runtime.cloudflare import NarrationProviderError
from storygame.runtime.command_split import split_command
from storygame.runtime.contracts import (
    FactOperation,
    GameBreakWarning,
    NarrationSegment,
    ResolvedTurnProposal,
    RuntimeContractError,
    SceneTransitionProposal,
    parse_turn_proposal,
)
from storygame.runtime.facts import Fact
from storygame.runtime.knowledge import KnowledgeProjector, TurnKnowledgeContext
from storygame.runtime.narration_safety import NarrationSafetyValidator
from storygame.runtime.reference_resolution import (
    Clarification,
    ReferenceResult,
    clarification_text,
    resolve_references,
)
from storygame.runtime.reveal_eligibility import ALREADY_ESTABLISHED, STORYLET_SPENT, explain_reveal
from storygame.runtime.state import CueStage as RuntimeCueStage
from storygame.runtime.state import RuntimeState, TurnDelivery, TurnRecord
from storygame.runtime.validation import (
    ProgressionValidator,
    ProposalValidationError,
    SelectedRevealResolver,
    predicate_matches,
    unconveyed_terms,
)
from storygame.runtime.world_model import apply_world_effects
from storygame.story_package.models import FactDelivery
from storygame.story_package.obligations import required_storylet_ids

SCENE_ENTRY_REQUEST = "Narrate the opening of this scene."
OPENING_ATTEMPTS = 3
TURN_NARRATION_ATTEMPTS = 2


class TurnProvider(Protocol):
    def __call__(self, player_input: str) -> object: ...


@runtime_checkable
class TurnProviderHandoff(Protocol):
    authored_handoff: object | None

    def authored_handoff_id(self) -> str | None: ...

    def clear_authored_handoff(self) -> None: ...


@runtime_checkable
class TurnProviderRejection(Protocol):
    def note_rejection(self, code: str | None, term: str | None = None) -> None: ...


@runtime_checkable
class TurnProviderBudget(Protocol):
    def begin_turn(self) -> None: ...

    def end_turn(self) -> None: ...

    def request_budget_remaining(self) -> int: ...


class StoryCompleteTurn:
    """A fixed, provider-free response after the authored ending has fired."""

    def __init__(self, marker: str) -> None:
        self.segments = (NarrationSegment(kind="narration", text=marker),)
        self.game_break = None
        self.story_complete = True
        self.ending_marker = marker

    @property
    def narration(self) -> str:
        return self.segments[0].text


class EngineRefusalTurn:
    """A fixed, provider-free response for an engine-owned refusal."""

    def __init__(self, text: str) -> None:
        self.segments = (NarrationSegment(kind="narration", text=text),)
        self.selected_knowledge_ids = ()
        self.events = ()
        self.game_break = None
        self.story_complete = False

    @property
    def narration(self) -> str:
        return self.segments[0].text


class ClarificationTurn:
    """A fixed, provider-free response when a scene-local noun is ambiguous."""

    def __init__(self, clarification: Clarification) -> None:
        self.segments = (NarrationSegment(kind="narration", text=clarification_text(clarification)),)
        self.selected_knowledge_ids = ()
        self.events = ()
        self.game_break = None
        self.story_complete = False
        self.clarification = clarification

    @property
    def narration(self) -> str:
        return self.segments[0].text


class RuntimeEngine(CanonicalEventMixin):
    def __init__(
        self,
        state: RuntimeState,
        provider: TurnProvider,
        *,
        projector: KnowledgeProjector | None = None,
        capture: WorldCapture | None = None,
        refusal_mode: str = "off",
    ) -> None:
        if refusal_mode not in {"off", "clause", "repair", "renarrate"}:
            raise ValueError("refusal_mode must be off, clause, repair, or renarrate")
        self.state = state
        self.provider = provider
        self.validator = ProgressionValidator(state.package)
        self.reveal_resolver = SelectedRevealResolver(state.package)
        self.projector = projector or KnowledgeProjector()
        self.narration_validator = NarrationSafetyValidator()
        self.last_projection: TurnKnowledgeContext | None = None
        self.last_player_command: str | None = None
        self.capture = capture
        self.refusal_mode = refusal_mode
        self.refusal_extra_calls = 0
        self.attempts: list[AttemptBundle] = []
        self.last_attempt: AttemptBundle | None = None
        self.last_guard_rejections: list[dict[str, object]] = []
        self.last_reference_resolution: ReferenceResult | None = None

    def _provider_handoff(self) -> TurnProviderHandoff | None:
        return self.provider if isinstance(self.provider, TurnProviderHandoff) else None

    def _provider_rejection(self) -> TurnProviderRejection | None:
        return self.provider if isinstance(self.provider, TurnProviderRejection) else None

    def _provider_budget(self) -> TurnProviderBudget | None:
        return self.provider if isinstance(self.provider, TurnProviderBudget) else None

    def _begin_provider_turn(self) -> None:
        budget = self._provider_budget()
        if budget is not None:
            budget.begin_turn()

    def _provider_has_active_handoff(self) -> bool:
        handoff = self._provider_handoff()
        return handoff is not None and handoff.authored_handoff is not None

    def _clear_provider_handoff(self) -> None:
        handoff = self._provider_handoff()
        if handoff is not None:
            handoff.clear_authored_handoff()

    def opening(self) -> ResolvedTurnProposal:
        """Open on the authored entry text, then the provider's embellishment; an opening commits no canon.

        The package owns the first words verbatim, so the scene always starts the
        way plot.md wrote it. The provider only continues from there, embellishing
        the scene's first authored beat, and no scene text is written in the runtime.
        """

        self.last_projection = self.projector.project(self.state, "player", "")
        scene = next(
            item for item in self.state.package.scenes if item.metadata.scene_id == self.state.current_scene_id
        )
        request = getattr(self.provider, "opening", None)
        for attempt in range(OPENING_ATTEMPTS):
            proposal = parse_turn_proposal(request() if callable(request) else self.provider(SCENE_ENTRY_REQUEST))
            opening_proposal = ResolvedTurnProposal(segments=proposal.segments)
            try:
                self.narration_validator.validate(self.state, self.state, opening_proposal, self.projector, "")
            except ProposalValidationError:
                if attempt == OPENING_ATTEMPTS - 1:
                    raise
                continue
            break
        entry = NarrationSegment(kind="narration", text=scene.metadata.entry_text)
        return ResolvedTurnProposal(segments=(entry, *proposal.segments))

    def turn(
        self,
        player_input: str,
        *,
        clock_seconds: int | None = None,
        clarifies: str | None = None,
        clarification_round: int = 0,
    ) -> ResolvedTurnProposal:
        """Call the provider once, then validate before any canonical mutation."""

        self.last_guard_rejections = []
        self.last_reference_resolution = None
        if not self.state.story_complete and not self.state.has_pending_break:
            reference = resolve_references(
                self.state,
                player_input,
                clarifies=clarifies,
                clarification_round=clarification_round,
            )
            self.last_reference_resolution = reference
            if reference.question is not None:
                return ClarificationTurn(reference.question)
            if reference.outcome in {"answered", "capped"}:
                player_input = reference.command
        budget = self._provider_budget()
        try:
            self._begin_provider_turn()
            return self._turn_active(player_input, clock_seconds=clock_seconds)
        finally:
            if budget is not None:
                budget.end_turn()

    def _turn_active(self, player_input: str, *, clock_seconds: int | None = None) -> ResolvedTurnProposal:
        """Call the provider once, then validate before any canonical mutation."""

        command_text = " ".join(split_command(player_input))
        self.refusal_extra_calls = 0
        self.last_player_command = command_text
        self._clear_provider_handoff()
        if self.state.story_complete:
            before = self.state.snapshot()
            marker = self.state.package.pacing.ending.marker
            result = StoryCompleteTurn(marker)
            self._record_attempt(player_input, command_text, before, outcome="committed")
            return result
        self.state.require_turn_allowed()
        already = set(self.validator.unsatisfied_dependencies(self.state.current_scene_id, self.state.facts))
        before = self.state.snapshot()
        provider_reply = None
        provider_proposal = None
        canonical_event_id = None
        entry_segments = None
        resolution_segments = None
        refusal_segment = None
        forced_handoff = False
        try:
            self.state.last_turn_delivery = TurnDelivery()
            self.state.turn_index += 1
            capture_record = self.capture.before_turn(command_text) if self.capture else {}
            if capture_record.get("engine_refusal"):
                refusal = capture_record["engine_refusal"]
                if self.capture:
                    self.capture.discard()
                self.state.restore_snapshot(before)
                self._clear_provider_handoff()
                result = EngineRefusalTurn(refusal)
                self._record_attempt(
                    player_input,
                    command_text,
                    before,
                    outcome="rejected",
                )
                return result
            if self.capture:
                self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                    update={
                        "capture_steps": tuple(capture_record.get("steps", ())),
                        "capture_issues": tuple(capture_record.get("issues", ())),
                    }
                )
            self._activate_pacing(realize_complications=True)
            self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                update={
                    "cue_fact_id": self.state.staged_cue_fact_id,
                    "handoff_staged": bool(self.state.staged_handoff_fact_ids),
                }
            )
            self.last_projection = self.projector.project(self.state, "player", command_text)
            for attempt in range(TURN_NARRATION_ATTEMPTS):
                provider_reply = self.provider(command_text)
                provider_proposal = parse_turn_proposal(provider_reply)
                self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                    update={"handoff_staged": bool(self.state.staged_handoff_fact_ids)}
                )
                handoff = self._provider_handoff()
                authored_handoff_id = handoff.authored_handoff_id() if handoff is not None else None
                proposal, _ = self.reveal_resolver.resolve(
                    self.state,
                    self.last_projection,
                    provider_proposal,
                    self.projector,
                    command_text,
                    authored_handoff_id=authored_handoff_id,
                )
                if self.state.last_turn_delivery.complication_verbatim:
                    proposal = proposal.model_copy(
                        update={
                            "segments": (
                                *proposal.segments,
                                NarrationSegment(
                                    kind="narration",
                                    text=self.state.last_turn_delivery.complication_text or "",
                                ),
                            )
                        }
                    )
                self.validator.validate_effects(self.state, proposal)
                candidate_state = deepcopy(self.state)
                candidate_state.apply_proposal(proposal, apply_world=False)
                try:
                    self.narration_validator.validate(
                        self.state, candidate_state, proposal, self.projector, command_text
                    )
                except ProposalValidationError as error:
                    if attempt == TURN_NARRATION_ATTEMPTS - 1:
                        raise
                    budget = self._provider_budget()
                    if budget is not None and budget.request_budget_remaining() <= 0:
                        raise
                    self.last_guard_rejections.append(
                        {
                            "code": error.code,
                            "message": str(error),
                            "rejected_narration": getattr(proposal, "narration", None),
                        }
                    )
                    rejection = self._provider_rejection()
                    if rejection is not None:
                        typed_term = (
                            error.term
                            if error.term
                            and error.term.casefold() in command_text.casefold()
                            and re.search(
                                rf"(?<!\w){re.escape(error.term)}(?!\w)",
                                command_text,
                                flags=re.IGNORECASE,
                            )
                            else None
                        )
                        if typed_term is None:
                            rejection.note_rejection(error.code)
                        else:
                            rejection.note_rejection(error.code, typed_term)
                    self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                        update={"guard_retry_used": True}
                    )
                    continue
                break
        except NarrationProviderError as error:
            self.state.restore_snapshot(before)
            self._clear_provider_handoff()
            self._record_attempt(
                player_input,
                command_text,
                before,
                provider_reply=provider_reply,
                outcome="operational_failure",
                operational_failure=AttemptError(code=error.error_code or type(error).__name__, message=error.message),
            )
            raise
        except (ProposalValidationError, RuntimeContractError) as error:
            if self.capture:
                self.capture.discard()
            self.state.restore_snapshot(before)
            self._clear_provider_handoff()
            self._record_attempt(
                player_input,
                command_text,
                before,
                provider_reply=provider_reply,
                outcome="rejected",
                rejection=AttemptError(code=getattr(error, "code", None) or type(error).__name__, message=str(error)),
            )
            raise
        # Keep the package's existing future-dependency analysis as the final
        # pre-commit check, after narration safety has accepted the candidate.
        at_risk = tuple(id_ for id_ in self.validator.validate(self.state, proposal) if id_ not in already)
        if at_risk:
            warning = GameBreakWarning(
                warning_id="future_dependency_at_risk",
                reason="This consequence would leave a required future dependency unavailable.",
                affected_ids=at_risk,
                snapshot_id=self.state.new_snapshot_id(),
            )
            self.state.set_pending_break(
                warning,
                snapshot=before,
                proposal=proposal,
                capture=self.capture.context() if self.capture else None,
            )
            self._record_attempt(
                player_input,
                command_text,
                before,
                provider_reply=provider_reply,
                provider_proposal=provider_proposal,
                outcome="game_break",
            )
            return proposal.model_copy(update={"game_break": warning})
        if self.state.staged_handoff_fact_ids and not provider_proposal.selected_knowledge_ids:
            forced_handoff = True
            proposal, canonical_event_id = self._prepare_handoff(proposal)
        staged_cue_fact_id = self.state.staged_cue_fact_id
        staged_cue_stage = self.state.staged_cue_stage
        self.state.apply_proposal(proposal, canonical_event_ids=(canonical_event_id,) if canonical_event_id else ())
        if proposal.selected_knowledge_ids:
            self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                update={"revealed_knowledge_ids": proposal.selected_knowledge_ids}
            )
        if self.capture:
            context = self.capture.context()
            capture_record = self.capture.after_commit(
                command_text,
                proposal.narration,
                entered_scene=self.state.current_scene_id != before.current_scene_id,
            )
            delivery = self.state.last_turn_delivery
            self.state.last_turn_delivery = delivery.model_copy(
                update={
                    "capture_issues": (*delivery.capture_issues, *capture_record["issues"]),
                    "capture_unplaced": tuple(
                        item.get("name", "")
                        for item in capture_record["unplaced"]
                        if isinstance(item, dict) and item.get("name")
                    ),
                }
            )
            proposal, refusal_segment = self._handle_refusal(proposal, capture_record, command_text, provider_proposal)
            newly = (
                set(self.validator.unsatisfied_dependencies(self.state.current_scene_id, self.state.facts)) - already
            )
            if newly:
                warning = GameBreakWarning(
                    warning_id="future_dependency_at_risk",
                    reason="This consequence would leave a required future dependency unavailable.",
                    affected_ids=tuple(sorted(newly)),
                    snapshot_id=self.state.new_snapshot_id(),
                )
                self.state.restore_snapshot(before)
                self._clear_provider_handoff()
                self.state.set_pending_break(
                    warning,
                    snapshot=before,
                    proposal=proposal,
                    capture=context,
                )
                return proposal.model_copy(update={"game_break": warning})
        self._record_turn(proposal)
        self._advance_pacing(proposal.narrative_seconds if clock_seconds is None else clock_seconds)
        self._activate_pacing()
        if not (canonical_event_id and proposal.transition):
            canonical_segments = self._apply_canonical_route_events()
        else:
            canonical_segments = ()
        self._activate_pacing()
        entry_segments = self._apply_authored_transition()
        self._activate_pacing()
        resolution_segments, deadline_event_ids = self._apply_resolution_deadline_backstop()
        if deadline_event_ids:
            self.state.turn_records[-1] = self.state.turn_records[-1].model_copy(
                update={"deadline_event_ids": deadline_event_ids}
            )
        if (
            staged_cue_fact_id
            and self.state.current_scene_id == before.current_scene_id
            and not (self.last_projection and self.last_projection.handoff_deliveries)
            and not self._provider_has_active_handoff()
        ):
            if staged_cue_fact_id not in self.state.delivered_cue_ids:
                self.state.delivered_cue_ids = (*self.state.delivered_cue_ids, staged_cue_fact_id)
            self.state.cue_stages = (
                *(stage for stage in self.state.cue_stages if stage.fact_id != staged_cue_fact_id),
                RuntimeCueStage(
                    fact_id=staged_cue_fact_id,
                    stage=staged_cue_stage,
                    last_turn=self.state.turn_index,
                    visit_entered_at=before.scene_entered_at_turn,
                ),
            )
            self.state.staged_cue_fact_id = None
            self.state.staged_cue_stage = 1
        elif staged_cue_fact_id and self.state.current_scene_id != before.current_scene_id:
            self.state.staged_cue_fact_id = staged_cue_fact_id
            cue_text = next(
                (
                    delivery.escalation_text if staged_cue_stage == 2 else delivery.cue_text
                    for delivery in self.state.package.deliveries
                    if delivery.fact_id == staged_cue_fact_id
                    and (delivery.escalation_text if staged_cue_stage == 2 else delivery.cue_text)
                ),
                None,
            )
            if cue_text is not None:
                proposal = proposal.model_copy(
                    update={"segments": tuple(segment for segment in proposal.segments if segment.text != cue_text)}
                )
        if canonical_segments or entry_segments or resolution_segments or refusal_segment:
            result = proposal.model_copy(
                update={
                    "segments": (
                        *proposal.segments,
                        *canonical_segments,
                        *(entry_segments or ()),
                        *(resolution_segments or ()),
                        *((refusal_segment,) if refusal_segment else ()),
                    )
                }
            )
        else:
            result = proposal
        result = self._finish_ending(result)
        self._record_attempt(
            player_input,
            command_text,
            before,
            provider_reply=provider_reply,
            provider_proposal=provider_proposal,
            outcome="game_break" if result.game_break else "committed",
            forced_handoff=forced_handoff,
        )
        return result

    def _finish_ending(self, proposal):
        ending = self.state.package.pacing.ending
        if (
            ending is not None
            and not self.state.story_complete
            and self.state.current_scene_id == ending.scene_id
            and all(self._predicate_matches(predicate) for predicate in ending.when)
        ):
            self.state.story_complete = True
            return proposal.model_copy(
                update={
                    "segments": (*proposal.segments, NarrationSegment(kind="narration", text=ending.text)),
                }
            )
        return proposal

    def _refusal_names(self, capture_record):
        provider = getattr(self.capture, "provider", None) if self.capture else None
        if provider is None:
            return ()
        world = provider._world()
        names = []
        for entry in capture_record.get("refused", ()):
            entity_id = entry.get("id") if isinstance(entry, dict) else None
            if entity_id and not world.is_hidden(entity_id):
                label = provider._entity_label(world, entity_id)
                if label not in names:
                    names.append(label[:1].upper() + label[1:])
        return tuple(names)

    def _refusal_segment(self, capture_record):
        names = self._refusal_names(capture_record)
        if not names:
            return None
        joined = " and ".join(names)
        verb = "has" if len(names) == 1 else "have"
        return NarrationSegment(kind="narration", text=f"{joined} {verb} not moved.")

    def _handle_refusal(self, proposal, capture_record, command_text, provider_proposal=None):
        names = self._refusal_names(capture_record)
        if not names:
            return proposal, None
        if self.refusal_mode in {"repair", "renarrate"}:
            replacement = self._refusal_rewrite(proposal, command_text, names, provider_proposal)
            if replacement is not None:
                label = "repaired" if self.refusal_mode == "repair" else "re-narrated"
                authored_texts = self._authored_delivery_texts()
                authored_preserved = any(segment.text in authored_texts for segment in proposal.segments)
                self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                    update={
                        "capture_issues": (
                            *self.state.last_turn_delivery.capture_issues,
                            *(f"refusal {label} for {name}" for name in names),
                            *(("refusal kept authored text",) if authored_preserved else ()),
                        )
                    }
                )
                return replacement, None
            reason = getattr(self, "_refusal_failure_reason", "unknown error")
            self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                update={
                    "capture_issues": (
                        *self.state.last_turn_delivery.capture_issues,
                        f"refusal re-narration failed: {reason}",
                    )
                }
            )
        if self.refusal_mode == "off":
            self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                update={
                    "capture_issues": (
                        *self.state.last_turn_delivery.capture_issues,
                        *(f"refusal detected for {name}" for name in names),
                    )
                }
            )
            return proposal, None
        refusal_segment = self._refusal_segment(capture_record)
        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
            update={
                "capture_issues": (
                    *self.state.last_turn_delivery.capture_issues,
                    *(f"refusal clause added for {name}" for name in names),
                )
            }
        )
        return proposal, refusal_segment

    def _refusal_rewrite(self, proposal, command_text, names, provider_proposal=None):
        try:
            provider_proposal = provider_proposal or proposal
            payload = self._build_refusal_payload(command_text, names, proposal, provider_proposal)
            response = self._call_refusal_provider(payload)
            replacement = parse_turn_proposal(response)
            segments = tuple(segment for segment in replacement.segments if segment.kind in {"narration", "dialogue"})
            if not segments:
                raise RuntimeContractError("replacement contains no narration or dialogue")
            candidate = proposal.model_copy(
                update={"segments": self._splice_refusal_segments(proposal, provider_proposal, segments)}
            )
            self.narration_validator.validate(self.state, self.state, candidate, self.projector, command_text)
            return candidate
        except Exception as error:  # fallback is intentionally local to this arm
            self._refusal_failure_reason = str(error) or type(error).__name__
            return None

    def _authored_delivery_texts(self):
        return {
            text
            for delivery in self.state.package.deliveries
            for text in (delivery.cue_text, delivery.escalation_text, delivery.fallback_text)
            if text is not None
        }

    def _build_refusal_payload(self, command_text, names, proposal, provider_proposal=None):
        assembler = getattr(self.provider, "assemble_turn_prompt", None)
        base = assembler(command_text) if callable(assembler) else {"system": "", "user": command_text}
        if not isinstance(base, dict):
            base = {"system": "", "user": str(base)}
        user = base.get("user")
        if user is None and "context" in base:
            render = getattr(self.provider, "_section_user_prompt", None)
            user = render(base["context"]) if callable(render) else str(base["context"])
        provider_proposal = provider_proposal or proposal
        provider_segments = {(segment.kind, segment.text) for segment in provider_proposal.segments}
        authored_texts = self._authored_delivery_texts()
        original = "\n".join(
            segment.text
            for segment in proposal.segments
            if (
                (segment.kind, segment.text) in provider_segments
                and segment.kind in {"narration", "dialogue"}
                and segment.text not in authored_texts
            )
        )
        joined = " and ".join(names)
        if self.refusal_mode == "repair":
            instruction = (
                f"Rewrite ONLY the sentences that say {joined} moved or changed so they say it stayed put. "
                "Keep every other sentence word for word. Return the same JSON shape.\n"
                f"ORIGINAL REPLY:\n{original}"
            )
        else:
            instruction = (
                f"CORRECTION: {joined} cannot be moved or changed that way and did not move. Narrate the attempt "
                "as it actually ends: the player tries, and the thing stays where it was. Do not claim the move."
            )
        return {"system": base.get("system", ""), "user": f"{user}\n\n{instruction}"}

    def _call_refusal_provider(self, payload):
        self.refusal_extra_calls += 1
        missing = object()
        previous_prompt = getattr(self.provider, "last_prompt", missing)
        try:
            request = getattr(self.provider, "_request_allowing_one_transient_retry", None)
            if callable(request):
                return request(payload)
            return self.provider(payload["user"])
        finally:
            discard = getattr(self.provider, "discard_pending_item_facts", None)
            if callable(discard):
                discard()
            if previous_prompt is not missing:
                self.provider.last_prompt = previous_prompt

    def _splice_refusal_segments(self, proposal, provider_proposal, replacement):
        provider_segments = {(segment.kind, segment.text) for segment in provider_proposal.segments}
        authored_texts = self._authored_delivery_texts()
        preserved_authored_texts = {segment.text for segment in proposal.segments if segment.text in authored_texts}
        replacement = tuple(segment for segment in replacement if segment.text not in preserved_authored_texts)
        result = []
        inserted = False
        for segment in proposal.segments:
            replaceable = (segment.kind, segment.text) in provider_segments and segment.text not in authored_texts
            if replaceable:
                if not inserted:
                    result.extend(replacement)
                    inserted = True
            else:
                result.append(segment)
        if not inserted:
            raise RuntimeContractError("no provider segments")
        return tuple(result)

    def _record_attempt(
        self,
        raw_input: str,
        command_text: str,
        before,
        *,
        provider_reply=None,
        provider_proposal=None,
        outcome: str,
        rejection: AttemptError | None = None,
        operational_failure: AttemptError | None = None,
        forced_handoff: bool = False,
    ) -> None:
        """Record whether a scene exit was earned or opened by a deadline event.

        A staged handoff that changes the scene is forced. For other exits,
        compare the taken transition with the pre-exit facts after removing
        facts asserted by deadline events in the current scene visit. If the
        transition would not have been eligible without those facts, it is
        timer-driven. The decision comes only from bounded turn history and
        the immutable story package.
        """
        after_scene = self.state.current_scene_id
        changed = after_scene != before.current_scene_id
        if not changed:
            cause = "none"
        elif forced_handoff:
            cause = "forced"
        else:
            cause = self._deadline_transition_cause(before)
        before_facts = {fact.predicate for fact in before.facts.asserted}
        after_facts = {fact.predicate for fact in self.state.facts.asserted}
        delivery = self.state.last_turn_delivery
        selected = tuple(getattr(provider_proposal, "selected_knowledge_ids", ()))
        delivery_ids: list[str] = []
        for knowledge_id in selected:
            knowledge = self.state.package.knowledge_indexes.by_id.get(knowledge_id)
            if knowledge is not None:
                delivery_ids.extend(
                    effect.fact_id
                    for effect in knowledge.establishes
                    if any(delivery.fact_id == effect.fact_id for delivery in self.state.package.deliveries)
                )
        stages = self._attempt_stages(provider_reply)
        raw_reveal_selection = getattr(self.provider, "last_reveal_selection", None)
        reveal_selection = None
        if isinstance(raw_reveal_selection, dict) and isinstance(raw_reveal_selection.get("outcome"), str):
            reveal_selection = RevealSelection(
                outcome=raw_reveal_selection["outcome"],
                matched=raw_reveal_selection.get("matched"),
                universe_size=raw_reveal_selection.get("universe_size", 0),
                shortlist_size=raw_reveal_selection.get("shortlist_size", 0),
            )
        contract_shadow = getattr(self.provider, "last_contract_shadow", None)
        bundle = AttemptBundle(
            identity=AttemptIdentity(
                code_sha=getenv("FREYTAG_DEPLOYMENT_SHA", "").strip()
                or getenv("RAILWAY_GIT_COMMIT_SHA", "").strip()
                or None,
                package_id=self.state.package.story_id,
                semantic_fallback=getenv("FREYTAG_SEMANTIC_REVEAL", "1") != "0",
                projection_cap=getattr(self.projector, "max_candidates", None),
            ),
            pre_state=AttemptPreState(
                scene_id=before.current_scene_id,
                turn_index=before.turn_index,
                turns_since_scene_entry=before.turn_index - before.scene_entered_at_turn,
                staged_cue_fact_id=before.staged_cue_fact_id,
                staged_handoff_fact_ids=tuple(before.staged_handoff_fact_ids),
                delivered_cue_ids=tuple(sorted(before.delivered_cue_ids)),
                fact_predicates=tuple(sorted(before_facts)),
            ),
            command=AttemptCommand(raw=raw_input, normalized=command_text),
            stages=stages,
            selected_reveal=SelectedReveal(knowledge_ids=selected, delivery_fact_ids=tuple(delivery_ids)),
            reveal_selection=reveal_selection,
            contract_shadow=contract_shadow,
            committed_delta=CommittedDelta(
                fact_predicates=tuple(sorted(after_facts - before_facts)),
                scene_from=before.current_scene_id if changed else None,
                scene_to=after_scene if changed else None,
            ),
            cue_stage=CueStage(
                fact_id=before.staged_cue_fact_id,
                delivered=before.staged_cue_fact_id in self.state.delivered_cue_ids
                or any(
                    stage.fact_id == before.staged_cue_fact_id and stage.stage == 2 for stage in self.state.cue_stages
                ),
                consumed=before.staged_cue_fact_id is not None
                and before.staged_cue_fact_id not in self.state.delivered_cue_ids
                and delivery.cue_fact_id != before.staged_cue_fact_id,
            ),
            transition_cause=cause,
            outcome=outcome,
            rejection=rejection,
            operational_failure=operational_failure,
            story_complete=self.state.story_complete,
        )
        self.last_attempt = bundle
        self.attempts.append(bundle)
        del self.attempts[:-24]

    def _deadline_transition_cause(self, before) -> str:
        """Return the cause of an authored exit using only the current visit history."""

        visit_length = self.state.turn_index - before.scene_entered_at_turn
        if visit_length <= 0 or visit_length > 24 or visit_length > len(self.state.turn_records):
            return "earned"
        visit_records = self.state.turn_records[-visit_length:]
        if len(visit_records) != visit_length:
            return "earned"
        deadline_ids = {event_id for record in visit_records for event_id in record.deadline_event_ids}
        if not deadline_ids:
            return "earned"
        transition_id = self.state.turn_records[-1].transition_id
        if transition_id is None:
            return "earned"
        transition = next(
            (item for item in self.state.package.pacing.transitions if item.id == transition_id),
            None,
        )
        if transition is None:
            return "earned"
        facts = self.state.facts.clone()
        resolution_events = {event.id: event for event in self.state.package.storylet_routes.resolution_events}
        asserted_fact_ids = {
            operation.fact_id
            for event_id in deadline_ids
            if (event := resolution_events.get(event_id)) is not None
            for operation in event.operations
            if operation.op == "assert"
        }
        facts.asserted = {fact for fact in facts.asserted if fact.predicate not in asserted_fact_ids}
        if all(predicate_matches(trigger, facts) for trigger in transition.triggers):
            return "earned"
        return "timer"

    def _attempt_stages(self, provider_reply) -> tuple[ModelStage, ...]:
        stages: list[ModelStage] = []
        prompt = getattr(self.provider, "last_prompt", None)
        stages.append(ModelStage(kind="narration", request=prompt, reply=self._stage_value(provider_reply)))
        semantic = getattr(self.provider, "last_semantic_match", None)
        if semantic is not None:
            stages.append(ModelStage(kind="semantic_match", reply=self._stage_value(semantic)))
        if self.capture is not None:
            before = getattr(self.capture, "last_before", None)
            after = getattr(self.capture, "last_after", None)
            if before is not None or after is not None:
                stages.append(
                    ModelStage(
                        kind="capture",
                        request=self._stage_value(before),
                        reply=self._stage_value(after),
                    )
                )
        return tuple(stages)

    @staticmethod
    def _stage_value(value):
        if value is None or isinstance(value, (str, dict, list)):
            return deepcopy(value)
        model_dump = getattr(value, "model_dump", None)
        if callable(model_dump):
            return model_dump(mode="json")
        return None

    def _record_turn(self, proposal: ResolvedTurnProposal) -> None:
        event_ids = tuple(sorted(event.event_id for event in proposal.events))
        reveal_ids = tuple(
            knowledge_id
            for event in proposal.events
            for knowledge_id in self.state.package.knowledge_indexes.source_to_knowledge.get(
                f"storylet:{event.event_id}:{event.realization_id}", ()
            )
        )
        fact_keys = tuple(
            sorted(
                {operation.fact.predicate for operation in proposal.operations}
                | {operation.fact.predicate for event in proposal.events for operation in event.operations}
            )
        )
        event_operations = tuple(operation for event in proposal.events for operation in event.operations)
        all_operations = (*proposal.operations, *event_operations)
        affected_entity_ids = tuple(
            sorted(
                {
                    entity_id
                    for operation in all_operations
                    for entity_id in (operation.fact.subject, operation.fact.object)
                    if entity_id is not None
                }
            )
        )
        self.state.turn_records.append(
            TurnRecord(
                id=f"turn_{len(self.state.turn_records) + 1}",
                reveal_ids=reveal_ids,
                affected_entity_ids=affected_entity_ids,
                event_ids=event_ids,
                transition_id=proposal.transition.transition_id if proposal.transition else None,
                fact_keys=fact_keys,
            )
        )
        del self.state.turn_records[:-24]

    def resolve_break(self, decision: str) -> ResolvedTurnProposal | None:
        self.refusal_extra_calls = 0
        pending = self.state.pending_proposal
        pending_capture = self.state.pending_capture
        pending_scene = self.state.pending_snapshot.current_scene_id if self.state.pending_snapshot else None
        self.state.resolve_break(decision)
        if decision != "proceed" or pending is None:
            self._clear_provider_handoff()
            return None
        if self.capture and pending_capture is not None:
            self.capture.resume(pending_capture)
            capture_record = self.capture.after_commit(
                pending_capture.get("command", ""),
                pending.narration,
                entered_scene=pending_scene is not None and self.state.current_scene_id != pending_scene,
            )
            delivery = self.state.last_turn_delivery
            self.state.last_turn_delivery = delivery.model_copy(
                update={
                    "capture_issues": (*delivery.capture_issues, *capture_record["issues"]),
                    "capture_unplaced": tuple(
                        item.get("name", "")
                        for item in capture_record["unplaced"]
                        if isinstance(item, dict) and item.get("name")
                    ),
                }
            )
            pending, refusal_segment = self._handle_refusal(
                pending, capture_record, pending_capture.get("command", ""), pending
            )
        else:
            refusal_segment = None
        self._record_turn(pending)
        self._advance_pacing(pending.narrative_seconds)
        self._activate_pacing()
        canonical_segments = self._apply_canonical_route_events()
        self._activate_pacing()
        entry_segments = self._apply_authored_transition()
        self._activate_pacing()
        if canonical_segments or entry_segments:
            pending = pending.model_copy(
                update={"segments": (*pending.segments, *canonical_segments, *(entry_segments or ()))}
            )
        if refusal_segment:
            pending = pending.model_copy(update={"segments": (*pending.segments, refusal_segment)})
        return self._finish_ending(pending)

    def _apply_authored_transition(self) -> tuple[NarrationSegment, ...] | None:
        """Advance along the highest-priority authored transition once its declared triggers hold.

        The source scene's min_turns is a hard pacing floor so committed
        triggers cannot rush the player out before the scene has had its minimum play.
        Returns the source bridge and entered scene's authored entry as two
        narration segments so both package-owned paragraphs reach the player.
        """

        if self.state.has_pending_break:
            return None
        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        windows = {window.scene_id: window for window in self.state.package.pacing.scenes}
        for transition in self.validator.eligible_transitions(self.state):
            if turns_since_entry < windows[transition.source_scene_id].min_turns:
                continue
            if not self.validator.transition_dependencies_available(transition, self.state.facts):
                continue
            scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.target_scene_id
            )
            source_scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.source_scene_id
            )
            bridge = NarrationSegment(kind="narration", text=source_scene.metadata.bridge_text[transition.id])
            entry = NarrationSegment(kind="narration", text=scene.metadata.entry_text)
            self.state.apply_proposal(
                ResolvedTurnProposal(
                    segments=(bridge, entry),
                    transition={"transition_id": transition.id},
                )
            )
            if self.state.turn_records:
                self.state.turn_records[-1] = self.state.turn_records[-1].model_copy(
                    update={"transition_id": transition.id}
                )
            return bridge, entry
        return None

    def _activate_pacing(self, *, realize_complications: bool = False) -> None:
        """Activate only package-declared, scene-bound optional storylets."""

        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        required_ids = required_storylet_ids(self.state.package)
        for storylet in self.state.package.storylet_routes.storylets:
            if storylet.scene_id != self.state.current_scene_id:
                continue
            if storylet.id not in required_ids and turns_since_entry > storylet.latest_turn:
                self.state.active_event_ids.discard(storylet.id)
                continue
            earlier_storylets = tuple(
                earlier
                for earlier in self.state.package.storylet_routes.storylets
                if earlier.scene_id == self.state.current_scene_id and earlier.target_turn < storylet.target_turn
            )
            clock_opened = storylet.earliest_turn <= turns_since_entry
            earned_forward = all(earlier.id in self.state.fired_event_ids for earlier in earlier_storylets)
            if (
                (clock_opened or earned_forward)
                and all(self._predicate_matches(predicate) for predicate in storylet.activation_conditions)
                and storylet.id not in self.state.fired_event_ids
            ):
                self.state.active_event_ids.add(storylet.id)
        self._apply_world_actions()
        for event in self.state.package.pacing.events:
            if (
                event.scene_id == self.state.current_scene_id
                and event.id not in self.state.fired_event_ids
                and turns_since_entry >= event.at_turn
                and all(self._predicate_matches(predicate) for predicate in event.when)
            ):
                for effect in event.effects:
                    self.state.facts.assert_fact(
                        Fact(predicate=effect.fact_id, subject="story", value=str(effect.equals).lower())
                    )
                self.state.fired_event_ids.add(event.id)
                if realize_complications and self.state.last_turn_delivery.complication_text is None:
                    realization = next(
                        (
                            realization
                            for realization in event.realizations
                            if all(self._predicate_matches(predicate) for predicate in realization.when)
                        ),
                        None,
                    )
                    if realization is not None:
                        self.state.last_turn_delivery = self.state.last_turn_delivery.model_copy(
                            update={
                                "complication_text": realization.text,
                                "complication_verbatim": realization.verbatim,
                            }
                        )
                if event.transition_id:
                    self.state.apply_proposal(
                        ResolvedTurnProposal(
                            segments=(
                                NarrationSegment(
                                    kind="narration", text="A declared pacing event changes the situation."
                                ),
                            ),
                            transition={"transition_id": event.transition_id},
                        )
                    )
        apply_world_effects(self.state.package, self.state.facts)
        windows = {window.scene_id: window for window in self.state.package.pacing.scenes}
        window = windows[self.state.current_scene_id]
        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        # Cue staging is available in every scene. Deadline staging stays out of resolution.
        missing = self._bridge_delivery_fact_ids()
        deliveries = {delivery.fact_id: delivery for delivery in self.state.package.deliveries}
        staged = self.state.staged_cue_fact_id
        if not (
            staged
            and (
                (self.state.staged_cue_stage == 1 and staged not in self.state.delivered_cue_ids)
                or (self.state.staged_cue_stage == 2 and staged in self.state.delivered_cue_ids)
            )
            and staged in missing
            and deliveries.get(staged) is not None
            and (deliveries[staged].cue_text if self.state.staged_cue_stage == 1 else True)
            and self._cue_reveal_available(staged)
        ):
            self.state.staged_cue_fact_id = next(
                (
                    fact_id
                    for fact_id in self._ranked_cue_fact_ids()
                    if fact_id not in self.state.delivered_cue_ids
                    and deliveries.get(fact_id) is not None
                    and deliveries[fact_id].cue_text
                    and self._cue_reveal_available(fact_id)
                ),
                None,
            )
            self.state.staged_cue_stage = 1
        if self._should_stage_escalation(window, turns_since_entry, deliveries):
            self.state.staged_cue_fact_id = next(
                (
                    fact_id
                    for fact_id in self.state.delivered_cue_ids
                    if self._cue_escalation_available(fact_id, deliveries, turns_since_entry)
                ),
                None,
            )
            if self.state.staged_cue_fact_id is not None:
                self.state.staged_cue_stage = 2
        if self._escalation_eligible() and turns_since_entry >= window.handoff_after_turns:
            self.state.staged_handoff_fact_ids = missing or self._bridge_missing_fact_ids()
        elif not self._escalation_eligible():
            self.state.staged_handoff_fact_ids = ()

    def _cue_reveal_available(self, fact_id: str) -> bool:
        """Return whether a scene reveal that establishes a cue fact can be earned; spent costs cannot re-cue."""

        delivery = next(
            (delivery for delivery in self.state.package.deliveries if delivery.fact_id == fact_id),
            None,
        )
        if delivery is not None and any(
            cost.op == "assert"
            and any(
                fact.predicate == cost.fact_id and str(fact.value).lower() == "true"
                for fact in self.state.facts.asserted
            )
            for cost in delivery.costs
        ):
            return False
        reveal_fact_ids = {fact_id}
        if delivery is not None:
            reveal_fact_ids.update(cost.fact_id for cost in delivery.costs if cost.op == "assert")
        reveals = tuple(
            knowledge
            for knowledge in self.state.package.knowledge.knowledge
            if self.state.current_scene_id in knowledge.available_in_scenes
            and any(effect.op == "assert" and effect.fact_id in reveal_fact_ids for effect in knowledge.establishes)
        )
        return not reveals or any(
            all(predicate_matches(predicate, self.state.facts) for predicate in knowledge.requires)
            and explain_reveal(self.state, "player", knowledge).reason not in {STORYLET_SPENT, ALREADY_ESTABLISHED}
            for knowledge in reveals
        )

    def _ranked_cue_fact_ids(self) -> tuple[str, ...]:
        """Rank missing bridge facts by their earliest eligible source window."""

        missing = self._bridge_delivery_fact_ids()
        pacing_fact_ids = {effect.fact_id for event in self.state.package.pacing.events for effect in event.effects}
        eligible_latest_turns: dict[str, int] = {}
        for storylet in self.state.package.storylet_routes.storylets:
            if storylet.scene_id != self.state.current_scene_id or storylet.id in self.state.fired_event_ids:
                continue
            if not all(self._predicate_matches(predicate) for predicate in storylet.activation_conditions):
                continue
            for realization in storylet.realizations:
                for operation in realization.operations:
                    if operation.op != "assert" or operation.fact_id not in missing:
                        continue
                    current = eligible_latest_turns.get(operation.fact_id)
                    if current is None or storylet.latest_turn < current:
                        eligible_latest_turns[operation.fact_id] = storylet.latest_turn
        return tuple(
            sorted(
                (fact_id for fact_id in missing if fact_id not in pacing_fact_ids),
                key=lambda fact_id: (
                    0 if fact_id in eligible_latest_turns else 1,
                    eligible_latest_turns.get(fact_id, 0),
                    missing.index(fact_id),
                ),
            )
        )

    def _escalation_eligible(self) -> bool:
        """Return whether Deadline staging is allowed."""

        scene = next(
            scene for scene in self.state.package.scenes if scene.metadata.scene_id == self.state.current_scene_id
        )
        return scene.metadata.freytag_phase != "resolution"

    def _should_stage_escalation(self, window, turns_since_entry: int, deliveries: dict[str, FactDelivery]) -> bool:
        return (
            self.state.staged_cue_fact_id is None
            and turns_since_entry >= window.nudge_after_turns
            and any(
                self._cue_escalation_available(fact_id, deliveries, turns_since_entry)
                for fact_id in self.state.delivered_cue_ids
            )
        )

    def _cue_escalation_available(
        self, fact_id: str, deliveries: dict[str, FactDelivery], turns_since_entry: int
    ) -> bool:
        delivery = deliveries.get(fact_id)
        if delivery is None or delivery.scene_id != self.state.current_scene_id:
            return False
        if any(fact.predicate == fact_id and str(fact.value).lower() == "true" for fact in self.state.facts.asserted):
            return False
        stage = next((stage for stage in self.state.cue_stages if stage.fact_id == fact_id), None)
        if stage is not None:
            if stage.visit_entered_at != self.state.scene_entered_at_turn or stage.stage >= 2:
                return False
        elif fact_id not in self.state.delivered_cue_ids:
            return False
        return self._cue_reveal_available(fact_id) and turns_since_entry >= self._nudge_after_turns()

    def _nudge_after_turns(self) -> int:
        return next(
            window.nudge_after_turns
            for window in self.state.package.pacing.scenes
            if window.scene_id == self.state.current_scene_id
        )

    def _bridge_delivery_fact_ids(self) -> tuple[str, ...]:
        """Cue ranking only foregrounds content whose activation conditions already hold.
        It never activates anything past a guard.
        For resolution events, the cue points at what the remaining required storylets would establish."""

        true_facts = frozenset(
            fact.predicate for fact in self.state.facts.asserted if str(fact.value).lower() == "true"
        )
        deliveries = {delivery.fact_id for delivery in self.state.package.deliveries}
        for event in self.state.package.storylet_routes.bridge_events:
            if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                continue
            if event.activation.is_satisfied(true_facts):
                continue
            missing = event.activation.minimal_undelivered_facts(true_facts)
            bridge_deliveries = tuple(fact_id for fact_id in missing if fact_id in deliveries)
            if bridge_deliveries:
                return bridge_deliveries
            break

        selected: list[str] = []
        resolution_events = self.state.package.storylet_routes.resolution_events
        storylets = {storylet.id: storylet for storylet in self.state.package.storylet_routes.storylets}
        for event in resolution_events:
            if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                continue
            for storylet_id in event.realization_storylets:
                if storylet_id in self.state.fired_event_ids:
                    continue
                storylet = storylets.get(storylet_id)
                if storylet is None:
                    continue
                for realization in storylet.realizations:
                    for operation in realization.operations:
                        if (
                            operation.op == "assert"
                            and operation.fact_id in deliveries
                            and operation.fact_id not in true_facts
                            and operation.fact_id not in selected
                        ):
                            selected.append(operation.fact_id)

        for event in resolution_events:
            if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                continue
            if event.activation.is_satisfied(true_facts):
                continue
            missing = event.activation.minimal_undelivered_facts(true_facts)
            for fact_id in missing:
                if fact_id in deliveries and fact_id not in true_facts and fact_id not in selected:
                    selected.append(fact_id)
        return tuple(selected)

    def _bridge_missing_fact_ids(self) -> tuple[str, ...]:
        """Return the pending bridge's smallest set of facts still needed."""

        true_facts = frozenset(
            fact.predicate for fact in self.state.facts.asserted if str(fact.value).lower() == "true"
        )
        for event in self.state.package.storylet_routes.bridge_events:
            if event.scene_id != self.state.current_scene_id or event.id in self.state.fired_event_ids:
                continue
            if event.activation.is_satisfied(true_facts):
                continue
            return event.activation.minimal_undelivered_facts(true_facts)
        return ()

    def _apply_world_actions(self) -> None:
        """Apply active, player-hidden route effects once their prerequisites hold."""

        for knowledge in self.state.package.knowledge.knowledge:
            if (
                knowledge.audience.kind != "world_only"
                or self.state.current_scene_id not in knowledge.available_in_scenes
                or knowledge.source.storylet_id not in self.state.active_event_ids
                or knowledge.source.storylet_id in self.state.fired_event_ids
                or not all(predicate_matches(predicate, self.state.facts) for predicate in knowledge.requires)
                or not any(
                    self._knowledge_effect_established(effect.fact_id, effect.op, effect.value)
                    for effect in knowledge.establishes
                )
            ):
                continue
            for effect in knowledge.establishes:
                fact = Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower())
                if effect.op == "assert":
                    self.state.facts.assert_fact(fact)
                else:
                    self.state.facts.retract_fact(fact)

    def _knowledge_effect_established(self, fact_id: str, operation: str, value: object) -> bool:
        expected = str(value).lower()
        matched = any(
            (fact.value if fact.value is not None else fact.object) == expected
            for fact in self.state.facts.matching(fact_id)
        )
        return matched if operation == "assert" else not matched

    def _prepare_handoff(self, proposal: ResolvedTurnProposal) -> tuple[ResolvedTurnProposal, str | None]:
        deliveries = {
            delivery.fact_id: delivery
            for delivery in self.state.package.deliveries
            if delivery.fact_id in self.state.staged_handoff_fact_ids
        }
        segments = proposal.segments
        missing = self._missing_handoff_terms(deliveries.values(), proposal.narration)
        if missing:
            segments = tuple(
                NarrationSegment(kind="narration", text=delivery.fallback_text) for delivery in deliveries.values()
            )
        delivery_operations = tuple(
            operation for delivery in deliveries.values() for operation in self._delivery_operations(delivery)
        )
        candidate_facts = self.state.facts.clone()
        for operation in (*proposal.operations, *delivery_operations):
            self.state._apply_operation(candidate_facts, operation)
        for event in proposal.events:
            for operation in event.operations:
                self.state._apply_operation(candidate_facts, operation)
        pending_bridge_event = next(
            (
                event
                for event in self.state.package.storylet_routes.bridge_events
                if event.scene_id == self.state.current_scene_id
                and event.id not in self.state.fired_event_ids
                and not event.activation.is_satisfied(self._true_facts(self.state.facts))
            ),
            None,
        )
        world_only_operations = (
            self._world_only_bridge_operations(pending_bridge_event, candidate_facts)
            if pending_bridge_event is not None
            else ()
        )
        for operation in world_only_operations:
            self.state._apply_operation(candidate_facts, operation)
        world_operations = self._world_action_operations(candidate_facts)
        for operation in world_operations:
            self.state._apply_operation(candidate_facts, operation)
        bridge_event = next(
            (
                event
                for event in self.state.package.storylet_routes.bridge_events
                if event.scene_id == self.state.current_scene_id
                and event.id not in self.state.fired_event_ids
                and event.activation.is_satisfied(self._true_facts(candidate_facts))
            ),
            None,
        )
        bridge_operations = (
            tuple(
                FactOperation(
                    operation=operation.op,
                    fact=Fact(predicate=operation.fact_id, subject="story", value=str(operation.value).lower()),
                )
                for operation in bridge_event.operations
            )
            if bridge_event
            else ()
        )
        for operation in bridge_operations:
            self.state._apply_operation(candidate_facts, operation)
        transition = self._handoff_transition(candidate_facts) if bridge_event else None
        if transition:
            source_scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.source_scene_id
            )
            target_scene = next(
                item for item in self.state.package.scenes if item.metadata.scene_id == transition.target_scene_id
            )
            segments = (
                *segments,
                NarrationSegment(kind="narration", text=source_scene.metadata.bridge_text[transition.id]),
                NarrationSegment(kind="narration", text=target_scene.metadata.entry_text),
            )
        combined = proposal.model_copy(
            update={
                "segments": segments,
                "operations": (
                    *proposal.operations,
                    *delivery_operations,
                    *world_only_operations,
                    *world_operations,
                    *bridge_operations,
                ),
                "transition": SceneTransitionProposal(transition_id=transition.id) if transition else None,
            }
        )
        return combined, bridge_event.id if bridge_event else None

    @staticmethod
    def _true_facts(facts) -> frozenset[str]:
        return frozenset(fact.predicate for fact in facts.asserted if str(fact.value).lower() == "true")

    @staticmethod
    def _delivery_operations(delivery: FactDelivery) -> tuple[FactOperation, ...]:
        operations = [
            FactOperation(operation="assert", fact=Fact(predicate=delivery.fact_id, subject="story", value="true"))
        ]
        operations.extend(
            FactOperation(
                operation=cost.op,
                fact=Fact(predicate=cost.fact_id, subject="story", value=str(cost.value).lower()),
            )
            for cost in delivery.costs
        )
        return tuple(operations)

    def _world_only_bridge_operations(self, event, facts) -> tuple[FactOperation, ...]:
        player_safe_fact_ids = {
            effect.fact_id
            for knowledge in self.state.package.knowledge.knowledge
            if knowledge.audience.player_visible
            for effect in knowledge.establishes
        }
        missing_fact_ids = event.activation.minimal_undelivered_facts(self._true_facts(facts))
        return tuple(
            FactOperation(
                operation="assert",
                fact=Fact(predicate=fact_id, subject="story", value="true"),
            )
            for fact_id in missing_fact_ids
            if fact_id not in player_safe_fact_ids
        )

    def _world_action_operations(self, facts) -> tuple[FactOperation, ...]:
        operations: list[FactOperation] = []
        for knowledge in self.state.package.knowledge.knowledge:
            if (
                knowledge.audience.kind != "world_only"
                or self.state.current_scene_id not in knowledge.available_in_scenes
                or knowledge.source.storylet_id not in self.state.active_event_ids
                or knowledge.source.storylet_id in self.state.fired_event_ids
                or not all(predicate_matches(predicate, facts) for predicate in knowledge.requires)
                or all(
                    self._fact_operation_established(facts, effect.op, effect.fact_id, effect.value)
                    for effect in knowledge.establishes
                )
            ):
                continue
            operations.extend(
                FactOperation(
                    operation=effect.op,
                    fact=Fact(predicate=effect.fact_id, subject="story", value=str(effect.value).lower()),
                )
                for effect in knowledge.establishes
            )
        return tuple(operations)

    @staticmethod
    def _fact_operation_established(facts, operation: str, fact_id: str, value: object) -> bool:
        expected = str(value).lower()
        matched = any(
            (fact.value if fact.value is not None else fact.object) == expected for fact in facts.matching(fact_id)
        )
        return matched if operation == "assert" else not matched

    @staticmethod
    def _missing_handoff_terms(deliveries, narration: str) -> tuple[str, ...]:
        missing: list[str] = []
        for delivery in deliveries:
            missing.extend(unconveyed_terms(delivery.must_convey, narration))
        return tuple(missing)

    def _handoff_transition(self, facts):
        turns_since_entry = self.state.turn_index - self.state.scene_entered_at_turn
        windows = {window.scene_id: window for window in self.state.package.pacing.scenes}
        eligible = [
            transition
            for transition in self.state.package.pacing.transitions
            if transition.source_scene_id == self.state.current_scene_id
            and turns_since_entry >= windows[transition.source_scene_id].min_turns
            and all(predicate_matches(trigger, facts) for trigger in transition.triggers)
            and self.validator.transition_dependencies_available(transition, facts)
        ]
        return max(eligible, key=lambda transition: transition.priority, default=None)

    def _predicate_matches(self, predicate: object) -> bool:
        from storygame.runtime.validation import predicate_matches

        return predicate_matches(predicate, self.state.facts)

    def _advance_pacing(self, seconds: int) -> None:
        previous = self._elapsed_seconds()
        self.state.facts.retract_fact(Fact(predicate="story_elapsed_seconds", subject="story", value=str(previous)))
        self.state.facts.assert_fact(
            Fact(predicate="story_elapsed_seconds", subject="story", value=str(previous + seconds))
        )

    def _elapsed_seconds(self) -> int:
        values = self.state.facts.matching("story_elapsed_seconds", "story")
        return int(values[-1].value) if values and values[-1].value is not None else 0

"""Offline, evidence-backed evaluation of conversation transcripts.

The evaluator deliberately does not infer quality from keywords, phrase lists, or
regexes. An injected model judges the complete accepted transcript alongside the
reviewed performance profiles. Local policy validates only the typed assessment,
its evidence references, and promotion thresholds.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from storygame.runtime.contracts import provider_json_payload
from storygame.runtime.engine import RuntimeEngine, TurnModel, TurnResponse
from storygame.runtime.state import RuntimeState

_CRITERIA = (
    "directness",
    "voice_specificity",
    "emotional_legibility",
    "embodied_behavior",
    "continuity",
    "player_responsiveness",
)
_QUALITY_THRESHOLD = 0.7
_MAX_REPETITION_RATE = 0.25


class ConversationCriticError(ValueError):
    """A fail-closed offline critic failure; never a playable turn result."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


class AuthoredProfile(BaseModel):
    """The reviewed voice context supplied to the independent critic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    participant_id: str = Field(min_length=1, max_length=80)
    public_manner: str = Field(min_length=1, max_length=600)
    voice: dict[str, object] = Field(min_length=1)


class TranscriptSegment(BaseModel):
    """One accepted, attributed rendering segment with optional material grounding."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["speech", "action"]
    speaker_id: str | None = Field(default=None, min_length=1, max_length=80)
    actor_id: str | None = Field(default=None, min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=4000)
    grounding: Literal["expressive", "material"] | None = None
    effect_refs: tuple[str, ...] = Field(default=(), max_length=16)


class TranscriptTurn(BaseModel):
    """A policy-labelled accepted or rejected runtime turn used only as evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    policy: str = Field(min_length=1, max_length=80)
    player_input: str = Field(min_length=1, max_length=4000)
    accepted: bool
    model_request_count: int = Field(ge=0, le=2)
    segments: tuple[TranscriptSegment, ...] = Field(default=(), max_length=32)
    fact_ids: tuple[str, ...] = Field(default=(), max_length=128)
    failure_code: str | None = Field(default=None, min_length=1, max_length=120)


class ReviewedTruth(BaseModel):
    """Reviewed semantic context, including material the critic must treat as protected."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, max_length=80)
    summary: str = Field(min_length=1, max_length=1200)
    protected: bool = False


class ConversationTranscript(BaseModel):
    """A fact-backed, reviewable projection of a simulated conversation run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1, max_length=160)
    genre: str = Field(min_length=1, max_length=80)
    profiles: tuple[AuthoredProfile, ...] = Field(min_length=2, max_length=32)
    reviewed_truths: tuple[ReviewedTruth, ...] = Field(default=(), max_length=256)
    turns: tuple[TranscriptTurn, ...] = Field(default=(), max_length=64)


class CriterionEvidence(BaseModel):
    """A critic citation that must resolve to a captured segment."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    criterion: Literal[
        "directness",
        "voice_specificity",
        "emotional_legibility",
        "embodied_behavior",
        "continuity",
        "player_responsiveness",
    ]
    turn_index: int = Field(ge=0)
    segment_index: int = Field(ge=0)


class ConversationQualityAssessment(BaseModel):
    """Typed semantic assessment returned by an independent conversation critic."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    directness: float = Field(ge=0, le=1)
    voice_specificity: float = Field(ge=0, le=1)
    emotional_legibility: float = Field(ge=0, le=1)
    embodied_behavior: float = Field(ge=0, le=1)
    continuity: float = Field(ge=0, le=1)
    player_responsiveness: float = Field(ge=0, le=1)
    initiation_rate: float = Field(ge=0, le=1)
    continuation_rate: float = Field(ge=0, le=1)
    refusal_handling_rate: float = Field(ge=0, le=1)
    repeated_tactic_rate: float = Field(ge=0, le=1)
    repeated_phrase_rate: float = Field(ge=0, le=1)
    speaker_substitution_failures: int = Field(ge=0)
    ungrounded_material_action_rate: float = Field(ge=0, le=1)
    protected_leaks: int = Field(ge=0)
    conversational_dead_ends: int = Field(ge=0)
    distinguishable_profile_count: int = Field(ge=0)
    evidence: tuple[CriterionEvidence, ...] = Field(min_length=6, max_length=48)
    rationale: str = Field(min_length=1, max_length=4000)

    @property
    def passed(self) -> bool:
        scores = tuple(getattr(self, criterion) for criterion in _CRITERIA)
        return (
            all(score >= _QUALITY_THRESHOLD for score in scores)
            and self.repeated_tactic_rate <= _MAX_REPETITION_RATE
            and self.repeated_phrase_rate <= _MAX_REPETITION_RATE
            and self.speaker_substitution_failures == 0
            and self.ungrounded_material_action_rate == 0
            and self.protected_leaks == 0
            and self.conversational_dead_ends == 0
            and self.distinguishable_profile_count >= 2
        )

    @classmethod
    def from_provider(cls, response: object) -> ConversationQualityAssessment:
        try:
            return cls.model_validate(provider_json_payload(response))
        except (ValidationError, ValueError, TypeError) as exc:
            raise ConversationCriticError("CONVERSATION_CRITIC_INVALID", str(exc)) from exc


class ConversationCritic(Protocol):
    """An offline model adapter; it is intentionally absent from live turn dependencies."""

    def review(self, transcript: ConversationTranscript, *, json_object: bool) -> object: ...


class ConversationSimulationError(ValueError):
    """A fail-closed error from the offline player-policy simulator."""

    def __init__(self, code: str, detail: str) -> None:
        self.code = code
        super().__init__(f"{code}: {detail}")


class ConversationPolicyInput(BaseModel):
    """One unconstrained natural-language player move proposed for an evaluation policy."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    player_input: str = Field(min_length=1, max_length=4000)

    @classmethod
    def from_provider(cls, response: object) -> ConversationPolicyInput:
        try:
            return cls.model_validate(provider_json_payload(response))
        except (ValidationError, ValueError, TypeError) as exc:
            raise ConversationSimulationError("CONVERSATION_POLICY_INVALID", str(exc)) from exc


class ConversationPolicyDriver(Protocol):
    """An offline player agent that turns a policy objective into a freeform move."""

    def propose(self, policy: str, transcript: ConversationTranscript, *, json_object: bool) -> object: ...


class ConversationSimulationCase(BaseModel):
    """One isolated runtime session driven by a semantic player policy."""

    model_config = ConfigDict(frozen=True)

    policy: str
    transcript: ConversationTranscript
    policy_request_count: int = Field(ge=0)
    assessment: ConversationQualityAssessment


class ConversationSimulationReport(BaseModel):
    """Offline evidence from policy-driven runtime conversations across a fixture."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = "conversation-simulation-v1"
    source_id: str
    cases: tuple[ConversationSimulationCase, ...]


def simulate_conversations(
    state_factory: Callable[[], RuntimeState],
    turn_model: TurnModel,
    policy_driver: ConversationPolicyDriver,
    critic: ConversationCritic,
    *,
    genre: str,
    policies: Sequence[str],
    max_turns: int = 4,
) -> ConversationSimulationReport:
    """Drive real engine turns with semantic policy agents, then judge their evidence offline.

    Policies influence only the simulated player's requests. They never enter the
    runtime context or constrain the player's live choices.
    """

    if max_turns < 1:
        raise ValueError("max_turns must be positive")
    cases = tuple(
        _simulate_conversation_policy(state_factory, turn_model, policy_driver, critic, genre, policy, max_turns)
        for policy in policies
    )
    source_id = cases[0].transcript.source_id if cases else "empty-conversation-simulation"
    return ConversationSimulationReport(source_id=source_id, cases=cases)


def write_conversation_simulation_report(path: Path, report: ConversationSimulationReport) -> None:
    """Persist non-runtime review evidence once; it can never overwrite a prior review."""

    if path.suffix != ".json" or not path.name.endswith(".conversation.json"):
        raise ValueError("CONVERSATION_OUTPUT_INVALID: output must end in .conversation.json")
    if path.exists():
        raise ValueError("CONVERSATION_OUTPUT_EXISTS: conversation reports never overwrite evidence")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def evaluate_conversation_transcript(
    transcript: ConversationTranscript, critic: ConversationCritic
) -> ConversationQualityAssessment:
    """Request one semantic assessment plus one bounded typed-output recovery."""

    last_error: ConversationCriticError | None = None
    for json_object in (True, False):
        try:
            assessment = ConversationQualityAssessment.from_provider(critic.review(transcript, json_object=json_object))
            _validate_evidence(transcript, assessment.evidence)
            return assessment
        except ConversationCriticError as exc:
            last_error = exc
    if last_error is not None and last_error.code == "CONVERSATION_CRITIC_EVIDENCE_INVALID":
        raise last_error
    raise ConversationCriticError(
        "CONVERSATION_CRITIC_EXHAUSTED", "critic output was invalid after one recovery request"
    ) from last_error


def _validate_evidence(transcript: ConversationTranscript, evidence: Sequence[CriterionEvidence]) -> None:
    cited_criteria = {item.criterion for item in evidence}
    if cited_criteria != set(_CRITERIA):
        raise ConversationCriticError("CONVERSATION_CRITIC_EVIDENCE_INVALID", "every rubric criterion needs a citation")
    for item in evidence:
        if item.turn_index >= len(transcript.turns):
            raise ConversationCriticError("CONVERSATION_CRITIC_EVIDENCE_INVALID", "citation names an unknown turn")
        if item.segment_index >= len(transcript.turns[item.turn_index].segments):
            raise ConversationCriticError("CONVERSATION_CRITIC_EVIDENCE_INVALID", "citation names an unknown segment")


def _simulate_conversation_policy(
    state_factory: Callable[[], RuntimeState],
    turn_model: TurnModel,
    policy_driver: ConversationPolicyDriver,
    critic: ConversationCritic,
    genre: str,
    policy: str,
    max_turns: int,
) -> ConversationSimulationCase:
    engine = RuntimeEngine(state_factory(), turn_model)
    transcript = _empty_transcript(engine.state, genre)
    turns: list[TranscriptTurn] = []
    policy_requests = 0
    for _ in range(max_turns):
        current = transcript.model_copy(update={"turns": tuple(turns)})
        player_input, requests = _policy_input(policy_driver, policy, current)
        policy_requests += requests
        response = engine.turn(player_input)
        turns.append(_record_turn(policy, player_input, response))
        if not response.ok:
            break
    transcript = transcript.model_copy(update={"turns": tuple(turns)})
    return ConversationSimulationCase(
        policy=policy,
        transcript=transcript,
        policy_request_count=policy_requests,
        assessment=evaluate_conversation_transcript(transcript, critic),
    )


def _empty_transcript(state: RuntimeState, genre: str) -> ConversationTranscript:
    package = state.narrative_package
    if package is None:
        raise ConversationSimulationError(
            "CONVERSATION_PACKAGE_UNAVAILABLE", "simulation needs a reviewed narrative package"
        )
    profiles = tuple(
        AuthoredProfile(
            participant_id=profile.participant_id,
            public_manner=profile.public_manner,
            voice=profile.voice.model_dump(),
        )
        for profile in package.npc_performance_profiles
    )
    if len(profiles) < 2:
        raise ConversationSimulationError("CONVERSATION_PROFILE_MINIMUM", "simulation needs two authored NPC profiles")
    reviewed_truths = tuple(
        ReviewedTruth(id=truth.id, summary=truth.summary, protected=truth.id in package.protected_truth_ids)
        for truth in package.truths
    )
    return ConversationTranscript(
        source_id=package.source_id, genre=genre, profiles=profiles, reviewed_truths=reviewed_truths
    )


def _policy_input(
    policy_driver: ConversationPolicyDriver, policy: str, transcript: ConversationTranscript
) -> tuple[str, int]:
    last_error: ConversationSimulationError | None = None
    for request_count, json_object in enumerate((True, False), start=1):
        try:
            proposed = ConversationPolicyInput.from_provider(
                policy_driver.propose(policy, transcript, json_object=json_object)
            )
            return proposed.player_input, request_count
        except ConversationSimulationError as exc:
            last_error = exc
    raise ConversationSimulationError(
        "CONVERSATION_POLICY_EXHAUSTED", "policy output was invalid after one recovery request"
    ) from last_error


def _record_turn(policy: str, player_input: str, response: TurnResponse) -> TranscriptTurn:
    accepted = response.ok
    rendered = response.segments if accepted else ()
    segments = tuple(_record_segment(segment) for segment in rendered)
    return TranscriptTurn(
        policy=policy,
        player_input=player_input,
        accepted=accepted,
        model_request_count=response.model_calls,
        segments=segments,
        failure_code=response.error.code if response.error is not None else None,
    )


def _record_segment(segment: dict[str, object]) -> TranscriptSegment:
    identity = segment.get("speaker") or segment.get("actor")
    participant_id = identity.get("id") if isinstance(identity, dict) else None
    raw_effect_refs = segment.get("effect_refs", ())
    effect_refs = raw_effect_refs if isinstance(raw_effect_refs, (list, tuple)) else ()
    return TranscriptSegment(
        kind=str(segment["kind"]),
        speaker_id=participant_id if segment.get("kind") == "speech" else None,
        actor_id=participant_id if segment.get("kind") == "action" else None,
        text=str(segment["text"]),
        grounding=segment.get("grounding"),
        effect_refs=tuple(str(value) for value in effect_refs),
    )

"""Phase-8 evidence-backed, model-judged conversation evaluation coverage."""

from __future__ import annotations

import pytest

from storygame.authoring.conversation_quality import (
    ConversationCriticError,
    ConversationSimulationError,
    ConversationTranscript,
    TranscriptTurn,
    evaluate_conversation_transcript,
    simulate_conversations,
    write_conversation_simulation_report,
)
from storygame.runtime.contracts import TurnResult
from storygame.runtime.engine import RuntimeEngine
from tests.test_phase6_group_scene_interaction import _group_proposal, _group_state


def _transcript() -> ConversationTranscript:
    return ConversationTranscript.model_validate(
        {
            "source_id": "cross-genre-fixture",
            "genre": "fantasy",
            "profiles": [
                {
                    "participant_id": "engineer",
                    "public_manner": "Focused and candid.",
                    "voice": {"register": "direct", "cadence": "brief", "diction": "practical"},
                },
                {
                    "participant_id": "navigator",
                    "public_manner": "Measured and alert.",
                    "voice": {"register": "precise", "cadence": "measured", "diction": "spatial"},
                },
            ],
            "turns": [
                {
                    "policy": "social",
                    "player_input": "What will this cost the crew?",
                    "accepted": True,
                    "model_request_count": 1,
                    "segments": [
                        {"kind": "speech", "speaker_id": "engineer", "text": "We can save them, but not for free."},
                        {
                            "kind": "action",
                            "actor_id": "engineer",
                            "grounding": "expressive",
                            "text": "She steadies herself.",
                        },
                    ],
                    "fact_ids": ["failure"],
                },
                {
                    "policy": "social",
                    "player_input": "What will this cost the crew?",
                    "accepted": True,
                    "model_request_count": 1,
                    "segments": [
                        {"kind": "speech", "speaker_id": "navigator", "text": "The route closes in four minutes."},
                        {
                            "kind": "action",
                            "actor_id": "navigator",
                            "grounding": "material",
                            "effect_refs": ["move_to_relay"],
                            "text": "They mark the escape route on the display.",
                        },
                    ],
                    "fact_ids": ["failure", "move_to_relay"],
                },
            ],
        }
    )


class _Critic:
    def __init__(self, response: object) -> None:
        self.response = response
        self.requests: list[tuple[ConversationTranscript, bool]] = []

    def review(self, transcript: ConversationTranscript, *, json_object: bool) -> object:
        self.requests.append((transcript, json_object))
        return self.response


def _assessment() -> dict[str, object]:
    evidence = [
        {"criterion": criterion, "turn_index": 0, "segment_index": 0}
        for criterion in (
            "directness",
            "voice_specificity",
            "emotional_legibility",
            "embodied_behavior",
            "continuity",
            "player_responsiveness",
        )
    ]
    return {
        "directness": 0.9,
        "voice_specificity": 0.9,
        "emotional_legibility": 0.8,
        "embodied_behavior": 0.9,
        "continuity": 0.9,
        "player_responsiveness": 0.9,
        "initiation_rate": 1.0,
        "continuation_rate": 0.5,
        "refusal_handling_rate": 1.0,
        "repeated_tactic_rate": 0.0,
        "repeated_phrase_rate": 0.0,
        "speaker_substitution_failures": 0,
        "ungrounded_material_action_rate": 0.0,
        "protected_leaks": 0,
        "conversational_dead_ends": 0,
        "distinguishable_profile_count": 2,
        "evidence": evidence,
        "rationale": "The two responses answer the shared question through distinct authored perspectives.",
    }


def test_critic_scores_full_transcript_and_authored_profiles_not_keyword_features() -> None:
    critic = _Critic(_assessment())

    assessment = evaluate_conversation_transcript(_transcript(), critic)

    assert assessment.passed
    assert assessment.distinguishable_profile_count == 2
    assert critic.requests == [(_transcript(), True)]


def test_critic_evidence_must_name_real_turns_and_segments() -> None:
    response = _assessment()
    response["evidence"] = [
        {
            "criterion": item["criterion"],
            "turn_index": 9 if item["criterion"] == "directness" else 0,
            "segment_index": 0,
        }
        for item in response["evidence"]
    ]

    with pytest.raises(ConversationCriticError, match="CONVERSATION_CRITIC_EVIDENCE_INVALID"):
        evaluate_conversation_transcript(_transcript(), _Critic(response))


@pytest.mark.parametrize(
    "evidence",
    (
        [{"criterion": "directness", "turn_index": 0, "segment_index": 0}] * 6,
        [
            {
                "criterion": item["criterion"],
                "turn_index": 0,
                "segment_index": 9 if item["criterion"] == "directness" else 0,
            }
            for item in _assessment()["evidence"]
        ],
    ),
)
def test_critic_rejects_missing_criteria_and_unknown_segments(evidence: list[dict[str, object]]) -> None:
    response = _assessment()
    response["evidence"] = evidence

    with pytest.raises(ConversationCriticError, match="CONVERSATION_CRITIC_EVIDENCE_INVALID"):
        evaluate_conversation_transcript(_transcript(), _Critic(response))


def test_critic_failure_is_typed_and_uses_one_shared_recovery() -> None:
    critic = _Critic("not JSON")

    with pytest.raises(ConversationCriticError, match="CONVERSATION_CRITIC_EXHAUSTED"):
        evaluate_conversation_transcript(_transcript(), critic)

    assert [json_object for _, json_object in critic.requests] == [True, False]


def test_transcript_turn_preserves_structured_runtime_evidence() -> None:
    turn = _transcript().turns[1]

    assert isinstance(turn, TranscriptTurn)
    assert turn.segments[1].effect_refs == ("move_to_relay",)


class _PolicyDriver:
    def __init__(self) -> None:
        self.policies: list[str] = []

    def propose(self, policy: str, transcript: ConversationTranscript, *, json_object: bool) -> object:
        self.policies.append(policy)
        return {"player_input": "What will this cost the crew?"}


class _TurnModel:
    def __init__(self) -> None:
        self.calls = 0

    def play_turn(self, context: object, *, json_object: bool) -> object:
        self.calls += 1
        return TurnResult(narration="The relay groans around the crew.", interaction=_group_proposal()).model_dump(
            mode="json"
        )


def test_policy_harness_drives_a_real_engine_without_constraining_live_turns(tmp_path) -> None:
    driver = _PolicyDriver()

    report = simulate_conversations(
        _group_state,
        _TurnModel(),
        driver,
        _Critic(_assessment()),
        genre="sci-fi",
        policies=("interruption_heavy",),
        max_turns=1,
    )

    assert driver.policies == ["interruption_heavy"]
    assert report.cases[0].transcript.turns[0].accepted
    assert report.cases[0].transcript.turns[0].model_request_count == 1
    output = tmp_path / "signal.conversation.json"
    write_conversation_simulation_report(output, report)
    with pytest.raises(ValueError, match="CONVERSATION_OUTPUT_EXISTS"):
        write_conversation_simulation_report(output, report)
    with pytest.raises(ValueError, match="CONVERSATION_OUTPUT_INVALID"):
        write_conversation_simulation_report(tmp_path / "signal.json", report)


def test_normal_interaction_uses_one_provider_request_without_an_evaluation_critic() -> None:
    model = _TurnModel()

    response = RuntimeEngine(_group_state(), model).turn("What will this cost the crew?")

    assert response.ok
    assert response.model_calls == 1
    assert model.calls == 1


class _InvalidPolicyDriver:
    def propose(self, policy: str, transcript: ConversationTranscript, *, json_object: bool) -> object:
        return "not JSON"


def test_policy_driver_has_a_bounded_typed_recovery() -> None:
    with pytest.raises(ConversationSimulationError, match="CONVERSATION_POLICY_EXHAUSTED"):
        simulate_conversations(
            _group_state,
            _TurnModel(),
            _InvalidPolicyDriver(),
            _Critic(_assessment()),
            genre="sci-fi",
            policies=("distrustful",),
            max_turns=1,
        )


def test_policy_simulation_rejects_an_unbounded_turn_budget() -> None:
    with pytest.raises(ValueError, match="max_turns must be positive"):
        simulate_conversations(
            _group_state,
            _TurnModel(),
            _PolicyDriver(),
            _Critic(_assessment()),
            genre="sci-fi",
            policies=("social",),
            max_turns=0,
        )

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import cast

import pytest

from storygame.authoring.causal_contracts import validate_causal_compiled_story
from storygame.authoring.compiler import _causal_story_as_compiled_story
from storygame.runtime.context import RuntimeContext, RuntimeContextBuilder
from storygame.runtime.contracts import (
    ActionSegment,
    InteractionEffect,
    InteractionProposal,
    RuntimeFailure,
    SpeechSegment,
    StateOperation,
    TurnResult,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.narrative import narrative_package_from_story
from storygame.runtime.state import RuntimeNarrativeProjection, RuntimeState, bootstrap_runtime_state
from storygame.runtime.validation import validate_and_commit
from tests.test_causal_spatial_projection_phase2 import _interaction_story


def _group_state():
    raw = deepcopy(_interaction_story())
    participants = cast(list[dict[str, object]], raw["participants"])
    profiles = cast(list[dict[str, object]], raw["npc_performance_profiles"])
    storylets = cast(list[dict[str, object]], raw["storylets"])
    frames = cast(list[dict[str, object]], raw["interaction_frames"])
    participants[1]["performance_profile_id"] = "navigator_manner"
    profiles.append(
        {
            "id": "navigator_manner",
            "participant_id": "navigator",
            "public_manner": "Measured, alert, and unwilling to guess.",
            "voice": {
                "register": "calm and precise",
                "cadence": "one observation followed by a measured question",
                "diction": "navigation terms grounded in the immediate scene",
                "avoidances": ["engineering jargon", "repeated catchphrases"],
            },
            "behavioral_cues": ["checks the departure timer before offering a route"],
        }
    )
    raw["party_knowledge"] = [
        {"participant_id": "engineer", "truth_ids": ["failure"]},
        {"participant_id": "navigator", "truth_ids": ["opening"]},
    ]
    availability = cast(dict[str, object], storylets[1]["availability"])
    availability["participant_ids"] = ["engineer", "navigator"]
    frames[0]["participant_ids"] = ["engineer", "navigator"]
    story = validate_causal_compiled_story(raw)
    state = bootstrap_runtime_state(
        RuntimeNarrativeProjection(_causal_story_as_compiled_story(story), narrative_package_from_story(story))
    )
    state.world.location = "relay"
    for participant_id in ("player", "engineer", "navigator"):
        state.facts.retract_fact(Fact(predicate="at", subject=participant_id, object="dock"))
        state.facts.assert_fact(Fact(predicate="at", subject=participant_id, object="relay"))
    for participant_id in ("engineer", "navigator"):
        state.facts.retract_fact(Fact(predicate="present", subject=participant_id, object="dock"))
        state.facts.assert_fact(Fact(predicate="present", subject=participant_id, object="relay"))
    state.facts.retract_fact(Fact(predicate="group_at", subject="dock_watch", object="dock"))
    state.facts.assert_fact(Fact(predicate="group_at", subject="dock_watch", object="relay"))
    state.facts.assert_fact(Fact(predicate="knows", subject="player", object="failure"))
    state.facts.retract_fact(Fact(predicate="scene_pressure", subject="scene", value="0"))
    state.facts.assert_fact(Fact(predicate="scene_pressure", subject="scene", value="20"))
    for beat_id in ("setup", "rise"):
        state.beat_runtime[beat_id].completed_tags.add(f"{beat_id}_completed")
    return state


def _group_proposal(**overrides: object) -> InteractionProposal:
    values: dict[str, object] = {
        "interaction_frame_id": "engineer_warning",
        "group_encounter_id": "dock_watch",
        "initiation": "npc_initiated",
        "participant_ids": ("engineer", "navigator", "player"),
        "segments": (
            SpeechSegment(
                speaker_id="engineer",
                addressee_ids=("player",),
                used_fact_ids=("failure",),
                text="The relay will fail unless we choose the repair now.",
            ),
            SpeechSegment(
                speaker_id="navigator",
                addressee_ids=("player",),
                used_fact_ids=("opening",),
                text="The departure timer gives us one clean chance to move.",
            ),
        ),
        "effects": (),
    }
    values.update(overrides)
    return InteractionProposal(**values)


def _inspection(**overrides: object) -> InteractionProposal:
    values: dict[str, object] = {
        "inspection_target_id": "dock_console",
        "initiation": "player_initiated",
        "participant_ids": ("player",),
        "segments": (
            ActionSegment(
                actor_id="player",
                grounding="expressive",
                text="You study the console display.",
            ),
        ),
    }
    values.update(overrides)
    return InteractionProposal(**values)


def _assert_failure(
    state: RuntimeState,
    proposal: InteractionProposal,
    code: str,
    *,
    player_input: str = "",
) -> None:
    with pytest.raises(RuntimeFailure) as exc_info:
        validate_and_commit(
            state,
            TurnResult(narration="The current scene advances.", interaction=proposal),
            player_input=player_input,
        )
    assert exc_info.value.code == code


def test_group_interaction_introduces_members_and_preserves_individual_voices() -> None:
    state = _group_state()

    updated = validate_and_commit(
        state,
        TurnResult(narration="The crew turns from the relay.", interaction=_group_proposal()),
    )

    assert updated.facts.has("group_introduced", "dock_watch", value="true")
    assert updated.facts.has("met", "player", "engineer")
    assert updated.facts.has("met", "player", "navigator")
    context = RuntimeContextBuilder().build(updated, "Navigator, which route is clear?")
    assert context.payload["speaker_private_context"]["navigator"]["performance_profile"]["id"] == "navigator_manner"

    follow_up = _group_proposal(
        initiation="continuation",
        addressed_participant_id="navigator",
        segments=(
            SpeechSegment(
                speaker_id="navigator",
                addressee_ids=("player",),
                used_fact_ids=("opening",),
                text="The service corridor remains our safest route.",
            ),
        ),
    )
    continued = validate_and_commit(
        updated,
        TurnResult(narration="The navigator points to the service corridor.", interaction=follow_up),
        player_input="Navigator, which route is clear?",
    )

    assert continued.facts.has("interaction_active", "engineer_warning", value="true")


@pytest.mark.parametrize(
    ("proposal", "make_absent", "code"),
    (
        (_group_proposal(participant_ids=("engineer", "outsider", "player")), False, "INTERACTION_PARTICIPANTS"),
        (_group_proposal(), True, "UNAVAILABLE_SPEAKER"),
    ),
)
def test_invalid_group_members_fail_closed(
    proposal: InteractionProposal,
    make_absent: bool,
    code: str,
) -> None:
    state = _group_state()
    if make_absent:
        state.facts.retract_fact(Fact(predicate="present", subject="navigator", object="relay"))

    with pytest.raises(RuntimeFailure) as exc_info:
        validate_and_commit(state, TurnResult(narration="The relay hums.", interaction=proposal))

    assert exc_info.value.code == code
    assert not state.facts.has("interaction_active", "engineer_warning", value="true")


def test_scene_subject_inspection_commits_only_declared_discoveries() -> None:
    state = bootstrap_runtime_state(
        RuntimeNarrativeProjection(
            _causal_story_as_compiled_story(validate_causal_compiled_story(_interaction_story())),
            narrative_package_from_story(validate_causal_compiled_story(_interaction_story())),
        )
    )
    inspection = InteractionProposal(
        inspection_target_id="dock_console",
        initiation="player_initiated",
        participant_ids=("player",),
        segments=(
            ActionSegment(
                actor_id="player",
                grounding="material",
                text="You run the console's diagnostic sequence.",
                effect_refs=("discover_console", "discover_scan"),
            ),
        ),
        effects=(
            InteractionEffect(
                id="discover_console",
                operation=StateOperation(
                    kind="add",
                    path="facts",
                    value={"predicate": "subject_discovered", "subject": "dock_console", "value": "true"},
                ),
            ),
            InteractionEffect(
                id="discover_scan",
                operation=StateOperation(
                    kind="add",
                    path="facts",
                    value={"predicate": "evidence_discovered", "subject": "scan_console", "value": "true"},
                ),
            ),
        ),
    )

    updated = validate_and_commit(state, TurnResult(narration="The diagnostic completes.", interaction=inspection))

    assert updated.facts.has("subject_discovered", "dock_console", value="true")
    assert updated.facts.has("evidence_discovered", "scan_console", value="true")


def test_inspection_rejects_absent_evidence_and_normalizes_visible_items() -> None:
    state = bootstrap_runtime_state(
        RuntimeNarrativeProjection(
            _causal_story_as_compiled_story(validate_causal_compiled_story(_interaction_story())),
            narrative_package_from_story(validate_causal_compiled_story(_interaction_story())),
        )
    )
    invalid = InteractionProposal(
        inspection_target_id="dock_console",
        initiation="player_initiated",
        participant_ids=("player",),
        segments=(
            ActionSegment(
                actor_id="player",
                grounding="material",
                text="You claim the relay log is here.",
                effect_refs=("invent_log",),
            ),
        ),
        effects=(
            InteractionEffect(
                id="invent_log",
                operation=StateOperation(
                    kind="add",
                    path="facts",
                    value={"predicate": "evidence_discovered", "subject": "relay_log", "value": "true"},
                ),
            ),
        ),
    )

    with pytest.raises(RuntimeFailure) as exc_info:
        validate_and_commit(state, TurnResult(narration="The console blinks.", interaction=invalid))

    assert exc_info.value.code == "INVALID_INSPECTION_DISCOVERY"

    state.world.items["signal_tablet"] = {"holder": "location:dock", "name": "signal tablet"}

    class Model:
        def play_turn(self, context: object, *, json_object: bool) -> object:
            assert cast(RuntimeContext, context).payload["normalized_affordance"]["target_id"] == "signal_tablet"
            return {
                "narration": "The tablet shows only its declared status.",
                "interaction": {
                    "inspection_target_id": "signal_tablet",
                    "initiation": "player_initiated",
                    "participant_ids": ["player"],
                    "segments": [
                        {
                            "kind": "action",
                            "actor_id": "player",
                            "grounding": "expressive",
                            "text": "You study the tablet display.",
                        }
                    ],
                },
            }

    response = RuntimeEngine(state, Model()).turn("inspect the signal tablet")

    assert response.ok


def test_group_and_inspection_cannot_reuse_opening_orientation() -> None:
    group_state = _group_state()
    assert group_state.compiled_story.opening is not None

    with pytest.raises(RuntimeFailure) as group_error:
        validate_and_commit(
            group_state,
            TurnResult(
                narration=group_state.compiled_story.opening.scene,
                interaction=_group_proposal(),
            ),
        )

    assert group_error.value.code == "OPENING_ORIENTATION_REUSED"

    story = validate_causal_compiled_story(_interaction_story())
    inspection_state = bootstrap_runtime_state(
        RuntimeNarrativeProjection(_causal_story_as_compiled_story(story), narrative_package_from_story(story))
    )
    assert inspection_state.compiled_story.opening is not None
    inspection = InteractionProposal(
        inspection_target_id="dock_console",
        initiation="player_initiated",
        participant_ids=("player",),
        segments=(
            ActionSegment(
                actor_id="player",
                grounding="expressive",
                text="You study the console display.",
            ),
        ),
    )

    with pytest.raises(RuntimeFailure) as inspection_error:
        validate_and_commit(
            inspection_state,
            TurnResult(
                narration=inspection_state.compiled_story.opening.scene,
                interaction=inspection,
            ),
        )

    assert inspection_error.value.code == "OPENING_ORIENTATION_REUSED"


def test_group_and_inspection_boundary_guards_fail_closed() -> None:
    _assert_failure(_group_state(), _group_proposal(group_encounter_id=None), "GROUP_ENCOUNTER_REQUIRED")
    _assert_failure(_group_state(), _group_proposal(group_encounter_id="missing"), "UNKNOWN_GROUP_ENCOUNTER")

    group_missing = _group_state()
    group_missing.facts.retract_fact(Fact(predicate="group_at", subject="dock_watch", object="relay"))
    _assert_failure(group_missing, _group_proposal(), "GROUP_NOT_PRESENT")

    protected_group = _group_state()
    assert protected_group.narrative_package is not None
    protected_group.narrative_package = replace(
        protected_group.narrative_package,
        protected_truth_ids=frozenset({"opening"}),
    )
    _assert_failure(protected_group, _group_proposal(), "PROTECTED_GROUP_INTRODUCTION")

    unprofiled = _group_state()
    assert unprofiled.narrative_package is not None
    unprofiled.narrative_package = replace(
        unprofiled.narrative_package,
        npc_performance_profiles=unprofiled.narrative_package.npc_performance_profiles[:1],
    )
    _assert_failure(unprofiled, _group_proposal(), "NPC_PROFILE_UNAVAILABLE")

    missing_target = _group_state()
    _assert_failure(
        missing_target,
        _group_proposal(initiation="continuation"),
        "GROUP_TARGET_REQUIRED",
    )
    inactive = _group_state()
    _assert_failure(
        inactive,
        _group_proposal(initiation="continuation", addressed_participant_id="navigator"),
        "INACTIVE_INTERACTION",
        player_input="Navigator, answer me.",
    )
    silent_target = _group_state()
    active = validate_and_commit(
        silent_target,
        TurnResult(narration="The crew turns.", interaction=_group_proposal()),
    )
    _assert_failure(
        active,
        _group_proposal(
            initiation="continuation",
            addressed_participant_id="navigator",
            segments=(
                SpeechSegment(
                    speaker_id="engineer",
                    addressee_ids=("player",),
                    used_fact_ids=("failure",),
                    text="The repair will not wait.",
                ),
            ),
        ),
        "ADDRESSED_PARTICIPANT_SILENT",
        player_input="Navigator, answer me.",
    )
    _assert_failure(
        _group_state(),
        _group_proposal(
            segments=(
                SpeechSegment(
                    speaker_id="navigator",
                    addressee_ids=("engineer",),
                    used_fact_ids=(),
                    text="The route is clear.",
                ),
            ),
        ),
        "INVALID_ADDRESSEE",
    )
    _assert_failure(
        _group_state(),
        _group_proposal(
            segments=(
                SpeechSegment(
                    speaker_id="navigator",
                    addressee_ids=("player",),
                    used_fact_ids=("failure",),
                    text="The route is clear.",
                ),
            ),
        ),
        "SPEAKER_LACKS_KNOWLEDGE",
    )
    _assert_failure(
        _group_state(),
        _group_proposal(
            segments=(ActionSegment(actor_id="player", grounding="expressive", text="You wave."),),
        ),
        "WRONG_ACTOR",
    )

    story = validate_causal_compiled_story(_interaction_story())
    inspection_state = bootstrap_runtime_state(
        RuntimeNarrativeProjection(_causal_story_as_compiled_story(story), narrative_package_from_story(story))
    )
    _assert_failure(inspection_state, _inspection(inspection_target_id="missing"), "UNKNOWN_INSPECTION_TARGET")
    _assert_failure(
        inspection_state,
        _inspection(participant_ids=("player", "engineer")),
        "INSPECTION_PARTICIPANTS",
    )
    _assert_failure(
        inspection_state,
        _inspection(segments=(ActionSegment(actor_id="engineer", grounding="expressive", text="They look."),)),
        "WRONG_INSPECTION_ACTOR",
    )
    _assert_failure(
        inspection_state,
        _inspection(
            segments=(
                SpeechSegment(
                    speaker_id="engineer",
                    addressee_ids=("dock_console",),
                    text="The console is steady.",
                ),
            ),
        ),
        "INVALID_INSPECTION_SPEECH",
    )
    _assert_failure(
        inspection_state,
        _inspection(
            segments=(
                SpeechSegment(
                    speaker_id="player",
                    addressee_ids=("dock_console",),
                    used_fact_ids=("tradeoff",),
                    text="I know the answer already.",
                ),
            ),
        ),
        "PLAYER_LACKS_KNOWLEDGE",
    )
    _assert_failure(
        inspection_state,
        _inspection(
            segments=(
                ActionSegment(actor_id="player", grounding="material", text="You scan.", effect_refs=("first",)),
            ),
            effects=(
                InteractionEffect(id="first", operation=StateOperation(kind="add", path="facts", value={})),
                InteractionEffect(id="extra", operation=StateOperation(kind="add", path="facts", value={})),
            ),
        ),
        "UNDECLARED_INSPECTION_EFFECT",
    )
    _assert_failure(
        inspection_state,
        _inspection(
            segments=(ActionSegment(actor_id="player", grounding="material", text="You scan.", effect_refs=("bad",)),),
            effects=(
                InteractionEffect(id="bad", operation=StateOperation(kind="set", path="world.flags", value="scan")),
            ),
        ),
        "UNDECLARED_INSPECTION_EFFECT",
    )
    _assert_failure(
        inspection_state,
        _inspection(
            segments=(ActionSegment(actor_id="player", grounding="material", text="You scan.", effect_refs=("bad",)),),
            effects=(InteractionEffect(id="bad", operation=StateOperation(kind="add", path="facts", value="bad")),),
        ),
        "INVALID_INSPECTION_DISCOVERY",
    )
    _assert_failure(
        inspection_state,
        _inspection(
            segments=(ActionSegment(actor_id="player", grounding="material", text="You scan.", effect_refs=("bad",)),),
            effects=(
                InteractionEffect(
                    id="bad",
                    operation=StateOperation(
                        kind="add",
                        path="facts",
                        value={"predicate": "subject_discovered", "subject": "dock_console", "value": "false"},
                    ),
                ),
            ),
        ),
        "INVALID_INSPECTION_DISCOVERY",
    )

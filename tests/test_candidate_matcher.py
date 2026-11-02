from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    _matches_all,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.knowledge import KnowledgeProjector, RevealCandidate
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

CARD_REFERENCES = ("recover", "retrieve", "memory card", "the card")

WARNING = ActionEvidenceCandidate(
    id="warning",
    required_groups=(
        CARD_REFERENCES,
        ("damaged recording", "interrupted message", "recording", "broken recording"),
        ("listen", "play"),
    ),
)
FILES = ActionEvidenceCandidate(
    id="files",
    required_groups=(CARD_REFERENCES, ("card files", "saved files"), ("read", "inspect")),
)

WARNING_HANDOFF = RevealCandidate(
    id="warning",
    statement="The recording warns against trusting emergency broadcasts.",
    action_evidence=WARNING.required_groups,
    must_convey=(),
    delivery_text="Michelle's damaged recording warns Kristin not to trust emergency broadcasts.",
)
FILES_HANDOFF = RevealCandidate(
    id="files",
    statement="The card contains saved files.",
    action_evidence=FILES.required_groups,
    must_convey=(),
    delivery_text="The memory card contains Michelle's saved files.",
)


SCENE_2C_CANDIDATES = tuple(
    RevealCandidate(
        id=item.id,
        statement=item.statement,
        earn_when=item.earn_when,
        must_convey=item.must_convey,
        action_evidence=item.action_evidence,
        delivery_text=item.delivery_text,
    )
    for item in PACKAGE.knowledge.knowledge
    if "2C" in item.available_in_scenes and item.action_evidence
)

SCENE_2A_CANDIDATES = tuple(
    RevealCandidate(
        id=item.id,
        statement=item.statement,
        earn_when=item.earn_when,
        must_convey=item.must_convey,
        action_evidence=item.action_evidence,
        delivery_text=item.delivery_text,
    )
    for item in PACKAGE.knowledge.knowledge
    if "2A" in item.available_in_scenes and item.action_evidence
)
SCENE_2A_OUTCOME_CANDIDATES = tuple(item for item in SCENE_2A_CANDIDATES if item.id != "k_sl_2a_b_r1")


@pytest.mark.parametrize(
    ("player_input",),
    [
        pytest.param(
            "Recover the damaged recording and listen to it.",
            id="unique_complete_evidence_matches_one_candidate",
        ),
        pytest.param("Retrieve the broken recording and play it.", id="declared_paraphrase_matches_without_inference"),
    ],
)
def test_complete_evidence_matches_one_candidate(player_input: str) -> None:
    result = uniquely_matched_candidate(player_input, (WARNING, FILES))

    assert result == WARNING


@pytest.mark.parametrize(
    ("player_input",),
    [
        pytest.param("Recover the damaged recording.", id="partial_evidence_does_not_match"),
        pytest.param("Search the kitchen for signs of a struggle.", id="unrelated_action_does_not_match"),
        pytest.param(
            "Do not recover the damaged recording or listen to it.",
            id="negated_action_does_not_match",
        ),
    ],
)
def test_nonmatching_evidence_does_not_match(player_input: str) -> None:
    result = uniquely_matched_candidate(player_input, (WARNING, FILES))

    assert result is None


def test_card_reference_aliases_match_only_the_intended_reveal() -> None:
    cases = (
        ("Read the saved files on Michelle's memory card.", "files"),
        ("Play the damaged recording from Michelle's memory card.", "warning"),
        ("Listen to the interrupted message on the card.", "warning"),
    )

    for player_input, expected_id in cases:
        result = uniquely_matched_candidate(player_input, (WARNING, FILES))

        assert result is not None
        assert result.id == expected_id


@pytest.mark.parametrize(
    ("player_input",),
    [
        pytest.param(
            "Ask Brandon about the memory card.",
            id="card_reference_without_the_reveal_action_does_not_match",
        ),
        pytest.param(
            "Do not listen to the damaged recording.",
            id="negated_recording_action_does_not_match_with_card_alias",
        ),
    ],
)
def test_missing_or_negated_reveal_action_does_not_match(player_input: str) -> None:
    assert uniquely_matched_candidate(player_input, (WARNING, FILES)) is None


def test_ambiguous_complete_evidence_does_not_break_ties() -> None:
    duplicate_warning = ActionEvidenceCandidate(id="other-warning", required_groups=WARNING.required_groups)

    result = uniquely_matched_candidate("Recover the damaged recording and listen to it.", (WARNING, duplicate_warning))

    assert result is None


def test_yielding_rule_for_action_candidates() -> None:
    non_repeatable = ActionEvidenceCandidate(
        id="non-repeatable", required_groups=(("recover",), ("recording",)), repeatable=False
    )
    repeatable = ActionEvidenceCandidate(
        id="repeatable", required_groups=(("recover",), ("recording",), ("listen",)), repeatable=True
    )

    assert uniquely_matched_candidate("Recover the recording and listen to it.", (repeatable, non_repeatable)) == (
        non_repeatable
    )

    another_non_repeatable = ActionEvidenceCandidate(
        id="another-non-repeatable", required_groups=(("recover",), ("recording",), ("listen",)), repeatable=False
    )
    assert (
        uniquely_matched_candidate("Recover the recording and listen to it.", (non_repeatable, another_non_repeatable))
        is None
    )

    another_repeatable = ActionEvidenceCandidate(
        id="another-repeatable", required_groups=(("recover",), ("recording",)), repeatable=True
    )
    assert (
        uniquely_matched_candidate("Recover the recording and listen to it.", (repeatable, another_repeatable)) is None
    )
    assert uniquely_matched_candidate("Recover the recording and listen to it.", (repeatable,)) == repeatable

    partial_non_repeatable = ActionEvidenceCandidate(
        id="partial-non-repeatable",
        required_groups=(("recover",), ("recording",), ("listen",)),
        repeatable=False,
    )
    repeatable_full = ActionEvidenceCandidate(
        id="repeatable-full", required_groups=(("recover",), ("recording",)), repeatable=True
    )
    assert (
        uniquely_matched_candidate("Recover the recording.", (repeatable_full, partial_non_repeatable))
        == repeatable_full
    )


def test_equal_complete_matches_still_tie() -> None:
    first = ActionEvidenceCandidate(id="first", required_groups=(("recover",), ("recording",)))
    second = ActionEvidenceCandidate(id="second", required_groups=(("recover",), ("recording",)))

    assert uniquely_matched_candidate("Recover the recording.", (first, second)) is None


def test_partial_match_never_beats_a_complete_match() -> None:
    partial = ActionEvidenceCandidate(id="partial", required_groups=(("recover",), ("recording",), ("listen",)))
    full = ActionEvidenceCandidate(id="full", required_groups=(("recover",), ("recording",)))

    result = uniquely_matched_candidate("Recover the recording.", (partial, full))

    assert result == full


def test_empty_evidence_never_matches() -> None:
    candidate = ActionEvidenceCandidate(id="empty", required_groups=())

    assert uniquely_matched_candidate("Recover the damaged recording and listen to it.", (candidate,)) is None


@pytest.mark.parametrize(
    ("authored_phrase", "synonym"),
    [
        ("inspect", "Examine"),
        ("read", "Review"),
        ("take", "Grab"),
        ("under", "Flip over"),
        ("open", "Pry open"),
        ("talk", "Speak with"),
    ],
)
def test_closed_synonym_classes_expand_an_authored_group(authored_phrase: str, synonym: str) -> None:
    candidate = ActionEvidenceCandidate(id="synonyms", required_groups=((authored_phrase,), ("drawer",)))

    assert uniquely_matched_candidate(f"{synonym} the drawer.", (candidate,)) == candidate


def test_single_word_evidence_tolerates_plural() -> None:
    candidate = ActionEvidenceCandidate(id="plural", required_groups=(("drawer",),))

    assert uniquely_matched_candidate("Inspect the drawers.", (candidate,)) == candidate


def test_three_letter_words_are_not_pluralised() -> None:
    candidate = ActionEvidenceCandidate(id="short", required_groups=(("map",),))

    assert uniquely_matched_candidate("Inspect the maps.", (candidate,)) is None


def test_negation_still_rejects_a_synonym_match() -> None:
    candidate = ActionEvidenceCandidate(id="negated", required_groups=(("inspect",), ("drawer",)))

    assert uniquely_matched_candidate("Do not examine the drawer.", (candidate,)) is None


def test_synonym_expansion_does_not_break_uniqueness() -> None:
    first = ActionEvidenceCandidate(id="first", required_groups=(("inspect",), ("drawer",)))
    second = ActionEvidenceCandidate(id="second", required_groups=(("look",), ("drawer",)))

    assert uniquely_matched_candidate("Examine the drawer.", (first, second)) is None


@pytest.mark.parametrize(
    "player_input",
    [
        "Examine the underside of my initials-marked drawer.",
        "Feel under the drawer.",
        "Flip over the KMS drawer.",
        "Inspect beneath the workstation drawer.",
    ],
)
def test_scene_1a_card_reveal_accepts_natural_synonyms(player_input: str) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-E")
    projection = KnowledgeProjector().project(state, "player", "")

    handoff = uniquely_matched_authored_handoff(player_input, projection.candidates)

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_1a_b_r0"


@pytest.mark.parametrize(
    ("player_input",),
    [
        ("Go to the uplink and start sending the copied JANUS evidence.",),
        ("Transmit the JANUS files from the broadcast uplink.",),
    ],
)
def test_scene_2c_transmit_matches_natural_player_actions(player_input: str) -> None:
    handoff = uniquely_matched_authored_handoff(player_input, SCENE_2C_CANDIDATES)

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_2c_d_r3"


@pytest.mark.parametrize(
    ("player_input",),
    [
        ("Reach the transfer carts and free a cart of captives.",),
        ("Go to the transfer carts and rescue the prisoners.",),
    ],
)
def test_scene_2c_rescue_matches_natural_player_actions(player_input: str) -> None:
    handoff = uniquely_matched_authored_handoff(player_input, SCENE_2C_CANDIDATES)

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_2c_d_r4"


def test_scene_2c_entry_text_hands_off_the_copied_files() -> None:
    scene = next(scene for scene in PACKAGE.scenes if scene.metadata.scene_id == "2C")

    assert "Kristin still carried the copied JANUS files." in scene.metadata.entry_text


def test_scene_2c_d_r3_matches_sending_the_copied_files() -> None:
    handoff = uniquely_matched_authored_handoff(
        "Head to the uplink and start sending the copied files.", SCENE_2C_CANDIDATES
    )

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_2c_d_r3"


@pytest.mark.parametrize(
    ("player_input",),
    [
        ("Open the purge-control console.",),
        ("Check Michelle's transfer order.",),
    ],
)
def test_scene_2c_unrelated_actions_match_neither_evidence_candidate(player_input: str) -> None:
    handoff = uniquely_matched_authored_handoff(player_input, SCENE_2C_CANDIDATES)

    assert handoff is None or handoff.candidate.id not in {
        "k_sl_2c_d_r3",
        "k_sl_2c_d_r4",
    }


def test_scene_2c_asking_brandon_to_retrieve_files_stays_tied() -> None:
    handoff = uniquely_matched_authored_handoff("Ask Brandon to retrieve the copied files.", SCENE_2C_CANDIDATES)

    assert handoff is None


@pytest.mark.parametrize(
    ("player_input",),
    [
        ("Diagnose the real cooling-water pressure fault for the supervisor.",),
        ("Read the pressure gauge and explain the precise pressure is falling on the return line.",),
    ],
)
def test_scene_2a_c_r5_matches_natural_player_actions(player_input: str) -> None:
    handoff = uniquely_matched_authored_handoff(player_input, SCENE_2A_OUTCOME_CANDIDATES)

    assert handoff is not None
    assert handoff.candidate.id == "k_sl_2a_c_r5"


@pytest.mark.parametrize(
    ("player_input",),
    [
        ("Present my inspection forms to the supervisor.",),
        ("Follow the supervisor through the nearby door.",),
    ],
)
def test_scene_2a_unrelated_actions_match_neither_evidence_candidate(player_input: str) -> None:
    handoff = uniquely_matched_authored_handoff(player_input, SCENE_2A_CANDIDATES)

    assert handoff is None or handoff.candidate.id not in {
        "k_sl_2a_c_r5",
        "k_sl_2a_c_r6",
    }


def test_scene_2a_c_r5_delivery_text_points_to_the_supervisor_action() -> None:
    item = next(item for item in PACKAGE.knowledge.knowledge if item.id == "k_sl_2a_c_r5")

    assert "shift supervisor grants access" in item.delivery_text


def test_authored_handoff_returns_the_projected_candidate_and_delivery() -> None:
    result = uniquely_matched_authored_handoff(
        "Recover the damaged recording and listen to it.", (WARNING_HANDOFF, FILES_HANDOFF)
    )

    assert result is not None
    assert result.candidate is WARNING_HANDOFF
    assert result.delivery_text == WARNING_HANDOFF.delivery_text


def test_authored_handoff_accepts_declared_aliases() -> None:
    result = uniquely_matched_authored_handoff("Retrieve the broken recording and play it.", (WARNING_HANDOFF,))

    assert result is not None
    assert result.candidate.id == "warning"


@pytest.mark.parametrize(
    ("player_input",),
    [
        pytest.param("Recover the damaged recording.", id="authored_handoff_rejects_partial_input"),
        pytest.param(
            "Do not recover the damaged recording or listen to it.",
            id="authored_handoff_rejects_negated_input",
        ),
        pytest.param(
            "Search the kitchen for signs of a struggle.",
            id="authored_handoff_rejects_no_offered_candidate",
        ),
    ],
)
def test_authored_handoff_rejects_nonmatching_input(player_input: str) -> None:
    assert uniquely_matched_authored_handoff(player_input, (WARNING_HANDOFF,)) is None


def test_authored_handoff_rejects_two_matching_candidates() -> None:
    duplicate = WARNING_HANDOFF.model_copy(update={"id": "other-warning"})

    assert (
        uniquely_matched_authored_handoff(
            "Recover the damaged recording and listen to it.", (WARNING_HANDOFF, duplicate)
        )
        is None
    )


def test_yielding_rule_for_authored_handoffs() -> None:
    non_repeatable = WARNING_HANDOFF.model_copy(
        update={
            "id": "non-repeatable",
            "action_evidence": (("recover",), ("recording",)),
            "repeatable": False,
        }
    )
    repeatable = WARNING_HANDOFF.model_copy(
        update={
            "id": "repeatable",
            "action_evidence": (("recover",), ("recording",), ("listen",)),
            "repeatable": True,
        }
    )

    result = uniquely_matched_authored_handoff("Recover the recording and listen to it.", (repeatable, non_repeatable))
    assert result is not None
    assert result.candidate is non_repeatable

    another_non_repeatable = WARNING_HANDOFF.model_copy(
        update={
            "id": "another-non-repeatable",
            "action_evidence": (("recover",), ("recording",), ("listen",)),
            "repeatable": False,
        }
    )
    assert (
        uniquely_matched_authored_handoff(
            "Recover the recording and listen to it.", (non_repeatable, another_non_repeatable)
        )
        is None
    )

    another_repeatable = WARNING_HANDOFF.model_copy(
        update={
            "id": "another-repeatable",
            "action_evidence": (("recover",), ("recording",)),
            "repeatable": True,
        }
    )
    assert (
        uniquely_matched_authored_handoff("Recover the recording and listen to it.", (repeatable, another_repeatable))
        is None
    )
    result = uniquely_matched_authored_handoff("Recover the recording and listen to it.", (repeatable,))
    assert result is not None
    assert result.candidate is repeatable

    partial_non_repeatable = WARNING_HANDOFF.model_copy(
        update={
            "id": "partial-non-repeatable",
            "action_evidence": (("recover",), ("recording",), ("listen",)),
            "repeatable": False,
        }
    )
    repeatable_full = WARNING_HANDOFF.model_copy(
        update={
            "id": "repeatable-full",
            "action_evidence": (("recover",), ("recording",)),
            "repeatable": True,
        }
    )
    result = uniquely_matched_authored_handoff("Recover the recording.", (repeatable_full, partial_non_repeatable))
    assert result is not None
    assert result.candidate is repeatable_full


def test_authored_handoff_equal_full_matches_still_tie() -> None:
    first = WARNING_HANDOFF.model_copy(update={"id": "first"})
    second = WARNING_HANDOFF.model_copy(update={"id": "second"})

    assert uniquely_matched_authored_handoff("Recover the damaged recording and listen to it.", (first, second)) is None


def test_authored_handoff_partial_match_never_beats_a_full_match() -> None:
    partial = WARNING_HANDOFF.model_copy(
        update={"id": "partial", "action_evidence": (("recover",), ("recording",), ("listen",))}
    )
    full = WARNING_HANDOFF.model_copy(update={"id": "full", "action_evidence": (("recover",), ("recording",))})

    result = uniquely_matched_authored_handoff("Recover the recording.", (partial, full))

    assert result is not None
    assert result.candidate is full


def test_authored_handoff_ignores_a_package_candidate_not_in_projection() -> None:
    package_candidates = (WARNING_HANDOFF, FILES_HANDOFF)
    projected_candidates = tuple(candidate for candidate in package_candidates if candidate.id == "warning")

    assert uniquely_matched_authored_handoff("Recover the card files and read them.", projected_candidates) is None


@pytest.mark.parametrize(
    "player_input",
    [
        "Examine under the drawer.",
        "Feel beneath the drawer.",
        "Search below the drawer.",
        "Check underneath the drawer.",
    ],
)
def test_under_synonym_class_matches_each_authored_group(player_input: str) -> None:
    groups = (("look", "search", "inspect", "check"), ("under", "beneath", "underside", "gap"), ("drawer",))

    assert _matches_all(groups, player_input)


def test_look_synonym_class_matches_outside_drawer_commands_only() -> None:
    groups = (("examine", "inspect", "search", "check", "look", "study"), ("drawer",))

    assert _matches_all(groups, "Inspect the drawer.")
    assert _matches_all(groups, "Look at the drawer.")
    assert not _matches_all(groups, "Open the drawer.")


def test_scene_1a_b_migrated_candidates_stay_disjoint() -> None:
    files_candidate = RevealCandidate(
        id="k_sl_1a_b_r1",
        statement="Kristin reads the saved files on Michelle's memory card.",
        must_convey=(),
        action_evidence=(
            CARD_REFERENCES,
            ("card files", "saved files", "files on the card"),
            ("read", "inspect"),
        ),
        delivery_text=(
            "Michelle's memory card contains a damaged recording and saved files. "
            "The card points to a dead drop at a bench in the park."
        ),
    )
    recording_candidate = RevealCandidate(
        id="k_sl_1a_b_r2",
        statement="Kristin listens to Michelle's damaged recording.",
        must_convey=(),
        action_evidence=(
            CARD_REFERENCES,
            ("damaged recording", "interrupted message", "recording"),
            ("listen", "play"),
        ),
        delivery_text=(
            "Michelle's memory card contains a damaged recording. It warns Kristin not to trust emergency broadcasts."
        ),
    )
    candidates = (files_candidate, recording_candidate)

    files_result = uniquely_matched_authored_handoff("Retrieve the saved files on the card and read them.", candidates)
    recording_result = uniquely_matched_authored_handoff("Recover the damaged recording and listen to it.", candidates)
    unrelated_result = uniquely_matched_authored_handoff("Search the kitchen for signs of a struggle.", candidates)

    assert files_result is not None
    assert files_result.candidate.id == "k_sl_1a_b_r1"
    assert recording_result is not None
    assert recording_result.candidate.id == "k_sl_1a_b_r2"
    assert unrelated_result is None

from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.knowledge import RevealCandidate

WARNING = ActionEvidenceCandidate(
    id="warning",
    required_groups=(("recover", "retrieve"), ("damaged recording", "broken recording"), ("listen", "play")),
)
FILES = ActionEvidenceCandidate(
    id="files",
    required_groups=(("recover", "retrieve"), ("card files", "saved files"), ("read", "inspect")),
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


def test_unique_complete_evidence_matches_one_candidate() -> None:
    result = uniquely_matched_candidate("Recover the damaged recording and listen to it.", (WARNING, FILES))

    assert result == WARNING


def test_declared_paraphrase_matches_without_inference() -> None:
    result = uniquely_matched_candidate("Retrieve the broken recording and play it.", (WARNING, FILES))

    assert result == WARNING


def test_partial_evidence_does_not_match() -> None:
    result = uniquely_matched_candidate("Recover the damaged recording.", (WARNING, FILES))

    assert result is None


def test_unrelated_action_does_not_match() -> None:
    result = uniquely_matched_candidate("Search the kitchen for signs of a struggle.", (WARNING, FILES))

    assert result is None


def test_negated_action_does_not_match() -> None:
    result = uniquely_matched_candidate("Do not recover the damaged recording or listen to it.", (WARNING, FILES))

    assert result is None


def test_ambiguous_complete_evidence_does_not_break_ties() -> None:
    duplicate_warning = ActionEvidenceCandidate(id="other-warning", required_groups=WARNING.required_groups)

    result = uniquely_matched_candidate("Recover the damaged recording and listen to it.", (WARNING, duplicate_warning))

    assert result is None


def test_empty_evidence_never_matches() -> None:
    candidate = ActionEvidenceCandidate(id="empty", required_groups=())

    assert uniquely_matched_candidate("Recover the damaged recording and listen to it.", (candidate,)) is None


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


def test_authored_handoff_rejects_partial_input() -> None:
    assert uniquely_matched_authored_handoff("Recover the damaged recording.", (WARNING_HANDOFF,)) is None


def test_authored_handoff_rejects_negated_input() -> None:
    assert (
        uniquely_matched_authored_handoff("Do not recover the damaged recording or listen to it.", (WARNING_HANDOFF,))
        is None
    )


def test_authored_handoff_rejects_no_offered_candidate() -> None:
    assert uniquely_matched_authored_handoff("Search the kitchen for signs of a struggle.", (WARNING_HANDOFF,)) is None


def test_authored_handoff_rejects_two_matching_candidates() -> None:
    duplicate = WARNING_HANDOFF.model_copy(update={"id": "other-warning"})

    assert (
        uniquely_matched_authored_handoff(
            "Recover the damaged recording and listen to it.", (WARNING_HANDOFF, duplicate)
        )
        is None
    )


def test_authored_handoff_ignores_a_package_candidate_not_in_projection() -> None:
    package_candidates = (WARNING_HANDOFF, FILES_HANDOFF)
    projected_candidates = tuple(candidate for candidate in package_candidates if candidate.id == "warning")

    assert uniquely_matched_authored_handoff("Recover the card files and read them.", projected_candidates) is None


def test_scene_1a_b_migrated_candidates_stay_disjoint() -> None:
    files_candidate = RevealCandidate(
        id="k_sl_1a_b_r1",
        statement="Kristin reads the saved files on Michelle's memory card.",
        must_convey=(),
        action_evidence=(
            ("recover", "retrieve"),
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
            ("recover", "retrieve"),
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

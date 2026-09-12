from storygame.runtime.candidate_matcher import ActionEvidenceCandidate, uniquely_matched_candidate

WARNING = ActionEvidenceCandidate(
    id="warning",
    required_groups=(("recover", "retrieve"), ("damaged recording", "broken recording"), ("listen", "play")),
)
FILES = ActionEvidenceCandidate(
    id="files",
    required_groups=(("recover", "retrieve"), ("card files", "saved files"), ("read", "inspect")),
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

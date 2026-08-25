"""Phase-4 review and promotion stays explicit, immutable, and genre-agnostic."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.authoring.candidate_review import CandidateReview, promote_candidate
from storygame.authoring.causal_profiles import CausalProfileRegistry
from storygame.authoring.compiler import CompilationError
from tests.test_causal_spatial_projection_phase3 import _phase3_story


def _candidate(path: Path, *, accepted: bool = True) -> None:
    path.write_text(
        json.dumps(
            {
                "story": _phase3_story(),
                "request_count": 1,
                "validation_results": ["local_contract_valid", "profile_valid", "source_verified"],
                "accepted": accepted,
                "diagnostics": [],
            }
        ),
        encoding="utf-8",
    )


def _review() -> CandidateReview:
    return CandidateReview(
        reviewer="editor@example.test",
        approved=True,
        checklist=(
            "terminal_roles",
            "knowledge_boundaries",
            "route_diversity",
            "failure_forward",
            "map_and_custody",
            "dramatic_questions",
            "participant_agency",
            "repeated_content_risk",
            "consequence_quality",
            "distinct_progression_paths",
            "character_voice_distinction",
            "catchphrase_and_stereotype_safety",
        ),
        notes="Verified against the source constraints and local review reports.",
    )


def _profiles() -> CausalProfileRegistry:
    return CausalProfileRegistry.from_directory(Path("data/genre_profiles"))


def test_promotion_writes_a_new_hash_bound_reviewed_artifact(tmp_path: Path) -> None:
    candidate = tmp_path / "signal.candidate.json"
    output = tmp_path / "signal.reviewed.json"
    _candidate(candidate)

    artifact = promote_candidate(candidate, output, _review(), _profiles())

    written = json.loads(output.read_text(encoding="utf-8"))
    assert artifact.candidate_sha256 == written["candidate_sha256"]
    assert written["schema_version"] == "reviewed-story-blueprint-v2"
    assert written["review"]["reviewer"] == "editor@example.test"
    assert written["story"]["id"] == "signal_crisis"
    assert not output.with_suffix(".tmp").exists()


@pytest.mark.parametrize(
    ("accepted", "review", "code"),
    [
        (False, _review(), "CANDIDATE_NOT_ACCEPTED"),
        (
            True,
            CandidateReview(reviewer="editor@example.test", approved=False, checklist=(), notes="Rejected."),
            "REVIEW_NOT_APPROVED",
        ),
    ],
)
def test_promotion_rejects_unaccepted_candidates_and_unapproved_reviews(
    tmp_path: Path, accepted: bool, review: CandidateReview, code: str
) -> None:
    candidate = tmp_path / "signal.candidate.json"
    _candidate(candidate, accepted=accepted)

    with pytest.raises(CompilationError, match=code):
        promote_candidate(
            candidate,
            tmp_path / "signal.reviewed.json",
            review,
            _profiles(),
        )


def test_promotion_revalidates_the_candidate_and_never_overwrites(tmp_path: Path) -> None:
    candidate = tmp_path / "signal.candidate.json"
    output = tmp_path / "signal.reviewed.json"
    _candidate(candidate)
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    payload["story"]["realization_routes"] = payload["story"]["realization_routes"][:1]
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CompilationError, match="CANDIDATE_REVIEW_INVALID"):
        promote_candidate(candidate, output, _review(), _profiles())

    _candidate(candidate)
    promote_candidate(candidate, output, _review(), _profiles())
    with pytest.raises(CompilationError, match="REVIEWED_OUTPUT_EXISTS"):
        promote_candidate(candidate, output, _review(), _profiles())


def test_promotion_rejects_a_debug_compilation_candidate(tmp_path: Path) -> None:
    candidate = tmp_path / "signal.candidate.json"
    _candidate(candidate)
    payload = json.loads(candidate.read_text(encoding="utf-8"))
    payload["story"]["provenance"]["generation_mode"] = "debug"
    candidate.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(CompilationError, match="DEBUG_CANDIDATE_NOT_PROMOTABLE"):
        promote_candidate(candidate, tmp_path / "signal.reviewed.json", _review(), _profiles())

from __future__ import annotations

import json
from pathlib import Path

import pytest

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
CORPUS = json.loads(Path("tests/fixtures/raw_language_corpus.json").read_text())


def _observed(entry: dict[str, object]) -> str | None:
    candidates = tuple(
        item
        for item in PACKAGE.knowledge.knowledge
        if entry["scene"] in item.available_in_scenes and item.action_evidence
    )
    result = uniquely_matched_authored_handoff(entry["input"], candidates)
    return result.candidate.id if result is not None else None


@pytest.mark.parametrize("entry", CORPUS, ids=lambda entry: entry["id"])
def test_recorded_observation_matches_matcher(entry: dict[str, object]) -> None:
    assert entry["observed"] == _observed(entry)


@pytest.mark.parametrize(
    "entry", [entry for entry in CORPUS if entry["kind"] == "canonical"], ids=lambda entry: entry["id"]
)
def test_canonical_commands_match_their_reveal(entry: dict[str, object]) -> None:
    assert entry["observed"] == entry["intended"] == entry["reveal_id"]


@pytest.mark.parametrize(
    "entry",
    [entry for entry in CORPUS if entry["kind"] in {"near_miss", "clarification_needed"}],
    ids=lambda entry: entry["id"],
)
def test_near_misses_and_clarifications_intend_no_reveal(entry: dict[str, object]) -> None:
    assert entry["intended"] is None


@pytest.mark.parametrize("entry", CORPUS, ids=lambda entry: entry["id"])
def test_known_gaps_are_marked(entry: dict[str, object]) -> None:
    if entry["intended"] != entry["observed"]:
        assert entry["note"].startswith("GAP:")


def test_corpus_has_required_shape() -> None:
    required_kinds = {
        "canonical",
        "polite",
        "pronoun",
        "correction",
        "scene_listening",
        "unrelated_restraint",
        "first_person",
        "clarification_needed",
        "near_miss",
    }
    assert len(CORPUS) >= 24
    assert required_kinds <= {entry["kind"] for entry in CORPUS}

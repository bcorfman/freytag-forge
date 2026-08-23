from __future__ import annotations

import json

import pytest

from storygame.authoring.compiler import load_compiled_story_fixture
from storygame.persistence.story_state import (
    ArtifactIntegrityError,
    artifact_bundle,
    artifact_manifest,
    replay_signature,
    verify_artifact_manifest,
    verify_replay_signature,
    write_artifacts,
)
from storygame.runtime.state import RuntimeEvent


@pytest.fixture
def sample_state():
    from storygame.runtime.state import bootstrap_runtime_state

    return bootstrap_runtime_state(load_compiled_story_fixture("mystery"))


def _event(turn_index: int = 1) -> RuntimeEvent:
    return RuntimeEvent(
        turn_index=turn_index,
        player_input="I inspect the door.",
        narration="The door is locked.",
        operations=({"kind": "set", "path": "world.flags", "value": "noticed_door"},),
        beat_updates=(),
        prompt_version="runtime-v2",
        prompt_token_estimate=42,
    )


def test_artifacts_are_deterministic_projections_of_facts_and_events(sample_state) -> None:
    state = sample_state
    state.recent_events.append(_event())
    state.turn_index = 1

    bundle = artifact_bundle(state)

    assert bundle["StoryState.json"]["turn_index"] == 1
    assert bundle["StoryState.json"]["facts"] == state.facts.as_json()
    assert bundle["trace.json"]["replay_signature"] == replay_signature(state)
    assert "I inspect the door." in bundle["STORY.md"]
    assert bundle["transcript.json"][0]["narration"] == "The door is locked."


def test_artifact_manifest_rejects_corruption(sample_state, tmp_path) -> None:
    state = sample_state
    state.recent_events.append(_event())
    write_artifacts(tmp_path, state)
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    (tmp_path / "STORY.md").write_text("tampered")

    with pytest.raises(ArtifactIntegrityError, match="STORY.md"):
        verify_artifact_manifest(tmp_path, manifest)


def test_artifacts_can_be_regenerated_after_a_clean_write(sample_state, tmp_path) -> None:
    state = sample_state
    state.recent_events.append(_event())
    expected = artifact_manifest(artifact_bundle(state))

    write_artifacts(tmp_path, state)

    actual = json.loads((tmp_path / "manifest.json").read_text())
    assert actual == expected


def test_replay_signature_is_checked_against_accepted_decisions(sample_state) -> None:
    state = sample_state
    verify_replay_signature(state, replay_signature(state))
    state.turn_index = 1
    with pytest.raises(ArtifactIntegrityError, match="replay signature"):
        verify_replay_signature(state, "tampered")


@pytest.mark.parametrize(
    "manifest",
    [
        {"schema_version": "old"},
        {"schema_version": "runtime-artifacts-v1"},
        {"schema_version": "runtime-artifacts-v1", "files": {}},
    ],
)
def test_artifact_manifest_rejects_invalid_or_incomplete_files(sample_state, tmp_path, manifest) -> None:
    write_artifacts(tmp_path, sample_state)
    if "files" not in manifest:
        with pytest.raises(ArtifactIntegrityError, match="unsupported artifact schema version|file hashes"):
            verify_artifact_manifest(tmp_path, manifest)
        return
    (tmp_path / "manifest.json").write_text("not json")
    with pytest.raises(ArtifactIntegrityError, match="manifest"):
        verify_artifact_manifest(tmp_path)

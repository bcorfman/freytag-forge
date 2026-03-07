from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from random import Random

import pytest

from storygame.engine.world import build_default_state
from storygame.persistence.savegame_sqlite import SqliteSaveStore
from storygame.persistence.story_state import (
    STORY_MARKDOWN_FILE,
    STORY_STATE_FILE,
    canonical_story_state_text,
    load_story_state_payload,
)


def test_story_state_includes_story_hash_and_trace(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=101)
    state.turn_index = 3

    with SqliteSaveStore(db_path) as store:
        store.save_run(
            "trace_slot",
            state,
            Random(7),
            raw_command="go north",
            action_kind="move",
            beat_type="progressive_complication",
            template_key="north_step",
            judge_decision={
                "decision_id": "judge-001",
                "status": "accepted",
                "judge": "director",
                "rationale": "state is coherent",
            },
        )

    artifact_dir = db_path.parent / "story_artifacts" / "trace_slot"
    state_payload = load_story_state_payload(artifact_dir / STORY_STATE_FILE)
    story_text = (artifact_dir / STORY_MARKDOWN_FILE).read_text(encoding="utf-8")

    assert state_payload["schema_version"] >= 2
    assert state_payload["trace"]["raw_command"] == "go north"
    assert state_payload["trace"]["judge_decision"]["status"] == "accepted"
    assert state_payload["story_markdown_sha256"] == hashlib.sha256(story_text.encode("utf-8")).hexdigest()


def test_save_run_rejects_tampered_story_markdown(tmp_path, caplog):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=88)
    state.turn_index = 1

    with SqliteSaveStore(db_path) as store:
        store.save_run("tamper_slot", state, Random(9), raw_command="look", action_kind="look")

        artifact_dir = db_path.parent / "story_artifacts" / "tamper_slot"
        story_path = artifact_dir / STORY_MARKDOWN_FILE
        story_path.write_text("tampered by external actor\n", encoding="utf-8")

        state.turn_index = 2
        with pytest.raises(ValueError, match="Artifact integrity check failed"):
            store.save_run("tamper_slot", state, Random(9), raw_command="look", action_kind="look")

    assert "artifact integrity check failed" in caplog.text.lower()


def test_story_state_round_trip_canonical_text_is_deterministic(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=111)
    state.turn_index = 5
    state.progress = 0.33
    state.player.flags["visited_archive"] = True

    with SqliteSaveStore(db_path) as store:
        store.save_run("deterministic_slot", state, Random(4), raw_command="look", action_kind="look")

    artifact_dir = db_path.parent / "story_artifacts" / "deterministic_slot"
    story_state_path = artifact_dir / STORY_STATE_FILE

    original_text = story_state_path.read_text(encoding="utf-8")
    payload = json.loads(original_text)
    first_render = canonical_story_state_text(payload)
    second_render = canonical_story_state_text(json.loads(first_render))

    assert first_render == second_render
    assert original_text == first_render


def test_story_state_canonical_text_is_stable_across_processes(tmp_path):
    db_path = tmp_path / "saves.sqlite"
    state = build_default_state(seed=515)
    state.turn_index = 7

    with SqliteSaveStore(db_path) as store:
        store.save_run("cross_process_slot", state, Random(22), raw_command="look", action_kind="look")

    artifact_dir = db_path.parent / "story_artifacts" / "cross_process_slot"
    story_state_path = artifact_dir / STORY_STATE_FILE
    local_text = story_state_path.read_text(encoding="utf-8")

    script = (
        "from pathlib import Path; "
        "from storygame.persistence.story_state import load_story_state_payload, canonical_story_state_text; "
        f"path = Path(r'{story_state_path}'); "
        "payload = load_story_state_payload(path); "
        "print(canonical_story_state_text(payload), end='')"
    )
    cross_process_text = subprocess.check_output(
        [sys.executable, "-c", script],
        text=True,
        encoding="utf-8",
    )

    assert local_text == cross_process_text

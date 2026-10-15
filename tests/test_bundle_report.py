import json
from pathlib import Path

import pytest

from bench.bundle_report import load_bundles, render_markdown, summarize
from storygame.runtime.attempt_bundle import (
    AttemptBundle,
    AttemptCommand,
    AttemptError,
    AttemptIdentity,
    AttemptPreState,
    CommittedDelta,
    CueStage,
    ModelStage,
    RevealSelection,
    SelectedReveal,
)


def bundle(**changes) -> AttemptBundle:
    value = AttemptBundle(
        identity=AttemptIdentity(),
        pre_state=AttemptPreState(scene_id="1A", turn_index=1, turns_since_scene_entry=0),
        command=AttemptCommand(raw="Search the desk.", normalized="Search the desk."),
        outcome="committed",
        reveal_selection=RevealSelection(outcome="no_eligible_action"),
    )
    return value.model_copy(update=changes)


def test_saved_bundle_report_covers_all_telemetry(tmp_path: Path) -> None:
    exact_selection = RevealSelection(outcome="exact_match", matched="k1", universe_size=3, shortlist_size=1)
    cases = [
        bundle(
            selected_reveal=SelectedReveal(knowledge_ids=("k1",)),
            cue_stage=CueStage(delivered=True),
            reveal_selection=exact_selection,
        ),
        bundle(cue_stage=CueStage(delivered=True, consumed=True)),
        bundle(committed_delta=CommittedDelta(scene_from="1A", scene_to="1B"), transition_cause="earned"),
        bundle(committed_delta=CommittedDelta(scene_from="1A", scene_to="1B"), transition_cause="forced"),
        bundle(committed_delta=CommittedDelta(scene_from="1A", scene_to="1B"), transition_cause="timer"),
        bundle(outcome="rejected", rejection=AttemptError(code="bad_json", message="no")),
        bundle(
            outcome="rejected",
            rejection=AttemptError(code="unsafe", message="no"),
            stages=(ModelStage(kind="narration"),),
        ),
        bundle(outcome="game_break"),
        bundle(outcome="operational_failure"),
        bundle(stages=(ModelStage(kind="narration"), ModelStage(kind="narration"), ModelStage(kind="capture"))),
    ]
    raw = []
    for turn, value in enumerate(cases, 1):
        payload = value.model_dump(mode="json")
        payload["profile"] = "test"
        raw.append({"turn": turn, "attempt_bundle": payload})
    raw.append({"turn": 99, "attempt_bundle": {"outcome": "committed"}})
    path = tmp_path / "e2e-blind-player-bundles-r1.json"
    path.write_text(
        json.dumps(
            {
                "story_id": "s",
                "scene": "1A",
                "replicates": [{"replicate": 1, "scenes": [{"scene": "1A", "bundles": raw}]}],
            }
        )
    )

    records = load_bundles([path])
    summary = summarize(records)
    assert len(records) == 10
    assert len(summary["invalid"]) == 1
    assert summary["reveal_vs_cue"]["checked"] == 6
    assert summary["reveal_vs_cue"]["per_scene"]["1A"]["cue_without_earned_reveal"] == 1
    assert summary["exits"]["per_scene"]["1A"] == {"earned": 1, "forced": 1, "timer": 1}
    assert summary["rare_selection"]["overall"]["exact_match"] == 1
    assert summary["refusal_telemetry"]["rejection_codes"] == {"bad_json": 1, "unsafe": 1}
    assert summary["refusal_telemetry"]["narration"] == {"provider_free": 1, "with_narration": 1}
    assert summary["refusal_telemetry"]["game_break"] == 1
    assert summary["refusal_telemetry"]["operational_failure"] == 1
    assert summary["recovery_stages"]["narration_stage_distribution"]["2"] == 1
    assert summary["recovery_stages"]["recovery_or_guard_retry"] == 1
    markdown = render_markdown(summary)
    assert "# Saved bundle report" in markdown
    assert "Checked: 10" in markdown
    assert "Invalid bundles: 1" in markdown


def test_repo_saved_bundles_are_valid_if_present() -> None:
    paths = sorted(Path("artifacts").glob("e2e-blind-player-bundles-r*.json"))
    if not paths:
        pytest.skip("no saved blind-player bundles")
    summary = summarize(load_bundles(paths))
    assert summary["invalid"] == []
    for key in ("reveal_vs_cue", "exits", "rare_selection", "refusal_telemetry", "recovery_stages"):
        assert isinstance(summary[key]["checked"], int)

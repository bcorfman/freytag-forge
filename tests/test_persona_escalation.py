"""End-to-end escalation checks for the deterministic persona harnesses."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

import storygame.personas
from storygame.personas import PERSONAS
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
SCENE_IDS = [scene.metadata.scene_id for scene in PACKAGE.scenes]
WINDOWS = {window.scene_id: window for window in PACKAGE.pacing.scenes}


@pytest.fixture(scope="module")
def summaries() -> dict[str, dict[str, object]]:
    return {name: storygame.personas.run_persona(name, PACKAGE) for name in PERSONAS}


def _rows(summary: dict[str, object]) -> dict[str, dict[str, object]]:
    return {row["scene_id"]: row for row in summary["scenes"]}


def test_personas_cover_the_escalation_ladder_without_stranding(
    summaries: dict[str, dict[str, object]],
) -> None:
    assert set(PERSONAS) == {"thorough", "staller", "wrong_lead"}

    for name, summary in summaries.items():
        assert summary["persona"] == name
        assert summary["resolution_complete"] is True
        assert summary["rejected_turns"] == []
        rows = _rows(summary)
        assert list(rows) == SCENE_IDS
        for scene_id, row in rows.items():
            window = WINDOWS[scene_id]
            if scene_id != SCENE_IDS[-1]:
                assert window.min_turns <= row["turns_to_exit"]
            assert row["turns_to_exit"] <= window.handoff_after_turns
            assert len(row["cue_fact_ids"]) == len(set(row["cue_fact_ids"]))

    for row in _rows(summaries["thorough"]).values():
        assert row["cue_count"] == 0
        assert row["deadline_staged"] is False
        assert row["layer_reached"] in {"none", "complication"}

    for scene_id, row in _rows(summaries["staller"]).items():
        if scene_id == SCENE_IDS[-1]:
            continue
        assert row["deadline_staged"] is True
        assert row["layer_reached"] == "deadline"
        events = [event for event in PACKAGE.pacing.events if event.scene_id == scene_id]
        if any(event.at_turn < WINDOWS[scene_id].handoff_after_turns and not event.when for event in events):
            assert row["complication_texts"]
    assert "memory_card_recovered" in _rows(summaries["staller"])[SCENE_IDS[0]]["costs_applied"]

    assert summaries["wrong_lead"]["resolution_complete"] is True


@pytest.mark.parametrize("name", ["thorough", "staller", "wrong_lead"])
def test_persona_summary_is_json_serializable(name: str, summaries: dict[str, dict[str, object]]) -> None:
    json.dumps(summaries[name])


def test_persona_cli_writes_json(
    summaries: dict[str, dict[str, object]], monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    output = tmp_path / "persona-summary.json"
    monkeypatch.setattr(storygame.personas, "run_persona", lambda name, package: summaries[name])
    monkeypatch.setattr(sys, "argv", ["storygame.personas", "--out", str(output)])
    storygame.personas.main()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert set(payload) == set(PERSONAS)
    assert all(summary["resolution_complete"] for summary in payload.values())

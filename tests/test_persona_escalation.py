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

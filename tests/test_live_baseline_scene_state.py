from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_scene_state", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def _run(module, output: Path, *extra: str, monkeypatch: pytest.MonkeyPatch | None = None):
    if monkeypatch is not None:
        from storygame.runtime.capture import WorldCapture
        from storygame.runtime.observation import ObservationContext, ObservationRequest
        from storygame.runtime.observation_verifier import Relation

        original_before_turn = WorldCapture.before_turn

        def force_observation(self, command):
            result = original_before_turn(self, command)
            self.provider.observation_request = ObservationRequest(command, "look", "storm_drain")
            return result

        monkeypatch.setattr(WorldCapture, "before_turn", force_observation)
        monkeypatch.setattr(
            WorldCapture,
            "_observation_context_for_verification",
            lambda _self, entered_scene: ObservationContext(
                observer="observer",
                action="look",
                completed_actions=(),
                visible_things=(),
                contingent_things=(),
                required=("storm drain",),
                omitted_optional=(),
                scope_complete=True,
                scene="1B",
            ),
        )
        monkeypatch.setattr(
            "storygame.runtime.capture.relations_from_context",
            lambda _context: (Relation(thing="storm_drain", place="park_path", scene_level=True),),
        )
    arguments = [
        "--dry-run",
        "--route",
        "observe_storm_drain_1b",
        "--replicates",
        "1",
        "--enforce",
        *extra,
        "--out",
        str(output),
    ]
    assert module.main(arguments) == 0
    return json.loads((output / "rows.json").read_text()), json.loads((output / "summary.json").read_text())


def test_storm_drain_route_has_one_command_and_1b_entry() -> None:
    module = _module()

    assert module.ROUTES["observe_storm_drain_1b"] == ("inspect the storm drain",)
    assert "observe_storm_drain_1b" in module.NEW_ROUTES
    assert module.ROUTE_START_SCENES["observe_storm_drain_1b"] == "1B"


def test_scene_state_requires_enforcement(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    module = _module()

    with pytest.raises(SystemExit) as raised:
        module.main(
            [
                "--dry-run",
                "--route",
                "observe_storm_drain_1b",
                "--scene-state",
                "--out",
                str(tmp_path / "invalid"),
            ]
        )

    assert raised.value.code == 2
    assert "--scene-state requires --enforce" in capsys.readouterr().err


def test_scene_state_is_recorded_and_off_rows_stay_unchanged(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _module()

    off_rows, off_summary = _run(module, tmp_path / "off", monkeypatch=monkeypatch)
    off_again_rows, off_again_summary = _run(module, tmp_path / "off-again", monkeypatch=monkeypatch)
    on_rows, on_summary = _run(module, tmp_path / "on", "--scene-state", monkeypatch=monkeypatch)

    def stable(value):
        if isinstance(value, dict):
            return {key: stable(item) for key, item in value.items() if key not in {"elapsed_s", "turn_elapsed_s"}}
        if isinstance(value, list):
            return [stable(item) for item in value]
        return value

    assert stable(off_rows) == stable(off_again_rows)
    assert off_summary == off_again_summary
    assert off_summary["scene_state"] is False
    assert on_summary["scene_state"] is True
    off_attempts = off_rows[0]["turns"][0]["enforce_attempts"]
    on_attempts = on_rows[0]["turns"][0]["enforce_attempts"]
    assert off_attempts
    assert on_attempts
    assert all(attempt.get("scene_state", False) is False for attempt in off_attempts)
    assert all(attempt["scene_state"] is True for attempt in on_attempts)


def test_scene_keyword_reaches_real_verifier(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _module()
    from storygame.runtime.capture import WorldCapture
    from storygame.runtime.observation import ObservationContext, ObservationRequest
    from storygame.runtime.observation_verifier import ObservationVerifier, Relation

    scenes: list[str | None] = []
    original_verify = ObservationVerifier.verify

    def recording_verify(self, narration, relations, *, scene=None):
        scenes.append(scene)
        return original_verify(self, narration, relations, scene=scene)

    monkeypatch.setattr(ObservationVerifier, "verify", recording_verify)
    original_before_turn = WorldCapture.before_turn

    def force_observation(self, command):
        result = original_before_turn(self, command)
        self.provider.observation_request = ObservationRequest(command, "look", "storm_drain")
        return result

    monkeypatch.setattr(WorldCapture, "before_turn", force_observation)
    monkeypatch.setattr(
        WorldCapture,
        "_observation_context_for_verification",
        lambda _self, entered_scene: ObservationContext(
            observer="observer",
            action="look",
            completed_actions=(),
            visible_things=(),
            contingent_things=(),
            required=("storm drain",),
            omitted_optional=(),
            scope_complete=True,
            scene="1B",
        ),
    )
    monkeypatch.setattr(
        "storygame.runtime.capture.relations_from_context",
        lambda _context: (Relation(thing="storm_drain", place="park_path", scene_level=True),),
    )
    _run(module, tmp_path / "scene", "--scene-state")

    assert scenes
    assert all(scene == "1B" for scene in scenes)

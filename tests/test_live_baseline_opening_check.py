from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from storygame.runtime.observation_verifier import ObservationVerifier
from storygame.runtime.world_model import world_for
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ringer/transcript_1a/live_baseline.py"
PACKAGE_ROOT = ROOT / "data/stories/continuity-initiative"


def _module():
    module_spec = importlib.util.spec_from_file_location("live_baseline_opening_check", SCRIPT)
    module = importlib.util.module_from_spec(module_spec)
    assert module_spec.loader is not None
    module_spec.loader.exec_module(module)
    return module


def _run(module, output: Path, *flags: str, monkeypatch: pytest.MonkeyPatch | None = None):
    if monkeypatch is not None:
        _force_observation(monkeypatch)
    assert (
        module.main(
            [
                "--dry-run",
                "--route",
                "observe_storm_drain_1b",
                "--replicates",
                "1",
                "--turns",
                "1",
                *flags,
                "--out",
                str(output),
            ]
        )
        == 0
    )
    return (
        json.loads((output / "rows.json").read_text()),
        json.loads((output / "summary.json").read_text()),
    )


def _force_observation(monkeypatch: pytest.MonkeyPatch) -> None:
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


def test_opening_check_requires_enforcement(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    module = _module()

    with pytest.raises(SystemExit) as raised:
        module.main(
            [
                "--dry-run",
                "--route",
                "observe_back_door_1a",
                "--opening-check",
                "--out",
                str(tmp_path / "invalid"),
            ]
        )

    assert raised.value.code == 2
    assert "--opening-check requires --enforce" in capsys.readouterr().err


def test_opening_check_configures_verifier_and_records_opening_data(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    module = _module()
    opening_checks: list[bool] = []
    verify_calls: list[dict[str, object]] = []
    original_init = ObservationVerifier.__init__
    original_verify = ObservationVerifier.verify

    def recording_init(self, ask, **kwargs):
        opening_checks.append(kwargs.get("opening_check", False))
        original_init(self, ask, **kwargs)

    def recording_verify(self, narration, relations, **kwargs):
        verify_calls.append(kwargs)
        return original_verify(self, narration, relations, **kwargs)

    monkeypatch.setattr(ObservationVerifier, "__init__", recording_init)
    monkeypatch.setattr(ObservationVerifier, "verify", recording_verify)
    monkeypatch.setattr(
        "storygame.runtime.item_facts.ItemFactsProvider.opening_subjects",
        lambda _self: ("storm drain",),
    )

    rows, summary = _run(module, tmp_path / "opening", "--enforce", "--opening-check")

    assert opening_checks == [True]
    assert summary["scene_state"] is False
    assert summary["opening_check"] is True
    assert rows[0]["opening_check"] is True
    attempts = rows[0]["turns"][0]["enforce_attempts"]
    assert attempts
    assert all("opening_verdicts" in attempt for attempt in attempts)
    assert all("opening_requests" in attempt for attempt in attempts)
    assert all(isinstance(attempt["opening_verdicts"], list) for attempt in attempts)
    assert all(isinstance(attempt["opening_requests"], int) for attempt in attempts)
    assert verify_calls
    assert all(call["opening_subjects"] == ("storm drain",) for call in verify_calls)
    assert all(call["command"] == "inspect the storm drain" for call in verify_calls)


def test_opening_check_off_keeps_attempt_shape(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    module = _module()
    rows, summary = _run(module, tmp_path / "off", "--enforce", monkeypatch=monkeypatch)

    assert summary["opening_check"] is False
    assert rows[0]["opening_check"] is False
    assert all(
        set(attempt)
        == {
            "narration",
            "relations",
            "outcome",
            "accepted",
            "verdicts",
            "requests",
            "failure",
            "elapsed_s",
            "scene_state",
        }
        for turn in rows[0]["turns"]
        for attempt in turn["enforce_attempts"]
    )


@pytest.mark.parametrize(
    ("route", "scene_id", "thing_id"),
    [
        ("observe_storm_drain_1b", "1B", "storm_drain"),
        ("observe_service_gate_1b", "1B", "service_gate"),
        ("observe_back_door_1a", "1A", "back_door"),
    ],
)
def test_opening_routes_start_in_scene_with_visible_thing(route: str, scene_id: str, thing_id: str) -> None:
    module = _module()
    package = load_story_package(PACKAGE_ROOT)

    assert module.ROUTES[route] == (f"inspect the {thing_id.replace('_', ' ')}",)
    assert route in module.NEW_ROUTES
    state, checkpoint_index = module._start_state(package, route)
    world = world_for(package, state.facts)

    assert checkpoint_index is not None
    assert state.current_scene_id == scene_id
    assert world.sees("kristin", thing_id)

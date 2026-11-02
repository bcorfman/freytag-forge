from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.phase1 import act2_guard_probe as probe
from storygame.runtime.validation import ProposalValidationError
from storygame.story_package.loader import load_story_package

EXPECTED = {
    "control": (False, True, True),
    "legacy": (True, True, True),
    "leakterms": (False, False, True),
}


@pytest.mark.parametrize("arm", probe.ARMS)
def test_arm_packages_load(tmp_path: Path, arm: str) -> None:
    package_path = probe.build_arm_package(arm, tmp_path / "package")
    load_story_package(package_path)


@pytest.mark.parametrize("arm", probe.ARMS)
def test_dry_run_has_expected_guard_signals(tmp_path: Path, arm: str) -> None:
    out = tmp_path / arm
    assert probe.run(out, arm, 1, True, False) == 0
    assert probe.check(out, 1, "dry") == []
    result = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert (
        tuple(
            result[key]
            for key in (
                "prompt_has_cooling_fault",
                "leak_map_has_cooling_fault",
                "leak_map_has_restricted_infrastructure_corridors",
            )
        )
        == EXPECTED[arm]
    )


def test_build_arm_requires_each_replacement(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source = tmp_path / "source"
    import shutil

    shutil.copytree(probe.PACKAGE_SOURCE, source)
    knowledge = source / "knowledge.yaml"
    target = "  pressure: Prove the cooling system is failing to get inside"
    knowledge.write_text(
        knowledge.read_text(encoding="utf-8").replace(target, "  pressure: Prove the cooling issue is real"),
        encoding="utf-8",
    )
    monkeypatch.setattr(probe, "PACKAGE_SOURCE", source)
    with pytest.raises(ValueError, match="legacy"):
        probe.build_arm_package("legacy", tmp_path / "package")


def test_live_requires_confirmation(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="live mode requires --confirm"):
        probe.run(tmp_path / "out", "control", 1, False, False)


def test_live_classifies_results_and_does_not_spend_player_budget(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    class FakeProvider:
        def __init__(self, _state: object, outcome: object) -> None:
            self.outcome = outcome
            self.request_count = 1
            self.recovery_count = 0
            self._request = lambda _payload: {}

        def __call__(self, _command: str) -> object:
            if isinstance(self.outcome, BaseException):
                raise self.outcome
            return self.outcome

    payload = {"segments": [{"kind": "narration", "text": "The gate waits."}]}
    outcomes = iter(
        [
            payload,
            ProposalValidationError("cooling fault", code="narration_known_term_leak", term="cooling fault"),
            RuntimeError("fetch failed"),
        ]
    )
    monkeypatch.setattr(probe, "provider_for", lambda state, variation: FakeProvider(state, next(outcomes)))
    out = tmp_path / "out"
    assert probe.run(out, "control", 3, False, True) == 0
    results = json.loads((out / "results.json").read_text(encoding="utf-8"))
    assert [row["result"] for row in results["samples"]] == ["ok", "rejected", "transport_error"]
    assert all(event["kind"] != "raw_player" for event in results["budget_events"])
    assert probe.check(out, 3, "live") == []

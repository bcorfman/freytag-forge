from __future__ import annotations

import json
from pathlib import Path

import check_three_c_probe as checker
import three_c_probe as probe
from door_transport import SpendBudget


class _CaptureProvider:
    def __init__(self, values: dict[str, object] | None = None) -> None:
        self.values = values or {}

    def __call__(self, _command: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The turn is uneventful."}]}

    def last_item_facts_match(self):
        return self.values.get("match", {"match_call": True})

    def last_item_facts_unplaced(self):
        return self.values.get("unplaced", [{"name": "Kristin", "place": "nowhere"}])

    def last_item_facts_refused(self):
        return self.values.get("refused", [{"name": "Kristin", "id": "kristin"}])


class _ProviderWithoutCaptureAccessors:
    def __call__(self, _command: str) -> dict[str, object]:
        return {"segments": [{"kind": "narration", "text": "The turn is uneventful."}]}


def _run_with_provider(provider, tmp_path: Path) -> dict[str, object]:
    return probe.run_row(
        "control",
        probe.variation_paths(("control",))["control"],
        SpendBudget(20, cloudflare_limit=20, player_limit=20),
        ask=lambda _screen, _budget: "Wait quietly.",
        provider_factory=lambda _state, _variation: provider,
        start="postc",
        first_command="Wait quietly.",
        capture_item_facts=True,
    )


def test_capture_records_provider_accessors_on_each_turn(tmp_path: Path) -> None:
    values = {
        "match": {"resolutions": {"Kristin": "broadcast chamber"}},
        "unplaced": ["unplaced"],
        "refused": ["refused"],
    }
    row = _run_with_provider(_CaptureProvider(values), tmp_path)
    capture = row["turns"][0]["item_facts_capture"]
    assert capture["match"] == values["match"]
    assert capture["unplaced"] == values["unplaced"]
    assert capture["refused"] == values["refused"]
    assert capture["raw"] is None


def test_capture_records_null_for_provider_without_accessors(tmp_path: Path) -> None:
    row = _run_with_provider(_ProviderWithoutCaptureAccessors(), tmp_path)
    capture = row["turns"][0]["item_facts_capture"]
    assert capture["match"] is None
    assert capture["unplaced"] is None
    assert capture["refused"] is None


def test_capture_enabled_dry_run_passes_checker(tmp_path: Path) -> None:
    probe.dry_run(tmp_path, 1, "postc", "off", ("control", "pre667"), None, capture_item_facts=True)
    assert json.loads((tmp_path / "source.json").read_text())["capture_item_facts"] is True
    assert json.loads((tmp_path / "plan.json").read_text())["capture_item_facts"] is True
    assert checker.check(tmp_path, 1, "dry") == []

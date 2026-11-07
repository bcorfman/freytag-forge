from __future__ import annotations

import json
from pathlib import Path

from bench.core import load_variation
from bench.exit_audit import audit, main
from bench.frozen_prompts import _script_inputs

ROOT = Path(__file__).resolve().parents[1]
VARIATION = ROOT / "bench" / "variations" / "richer-3a-d1-control.json"


def test_audit_records_each_command_and_authoritative_world_shape() -> None:
    variation = load_variation(VARIATION)
    report = audit(VARIATION)

    assert report["variation"] == variation["name"]
    assert report["package_hash"] == variation["_package_hash"]
    assert len(report["commands"]) == len(_script_inputs(variation)) == 9
    assert len(report["radio_custody_by_command"]) == 9
    assert report["exit"]["scene_id"] != "3A"

    required_ids = {"kristin", "michelle", "brandon", "captives", "stolen_radio"}
    for record in report["commands"]:
        assert set(record) >= {"command", "scene_id", "left_scene", "true_fact_ids", "placements"}
        assert record["true_fact_ids"] == sorted(record["true_fact_ids"])
        assert required_ids <= set(record["placements"])
        for placement in record["placements"].values():
            assert set(placement) >= {"place", "holder"}
            if placement["holder"] is not None:
                assert placement["holder"] in record["placements"]
                assert record["placements"][placement["holder"]]["holder"] is None

    exit_placements = report["exit"]["placements"]
    assert required_ids <= set(exit_placements)
    assert report["commands"][-1]["left_scene"] is True
    assert report["radio_custody_by_command"][-1]["command"] == report["commands"][-1]["command"]


def test_audit_is_deterministic() -> None:
    assert audit(VARIATION) == audit(VARIATION)


def test_cli_writes_report_json(tmp_path: Path) -> None:
    output = tmp_path / "REPORT.json"

    assert main(["--variation", str(VARIATION), "--out", str(output)]) == 0

    written = json.loads(output.read_text(encoding="utf-8"))
    assert written == audit(VARIATION)

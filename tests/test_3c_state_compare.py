from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.stage7 import three_c_state_compare as compare


@pytest.mark.nightly
def test_state_compare_runs_offline_end_to_end(tmp_path: Path) -> None:
    out = tmp_path / "comparison"
    assert compare.main(["--out", str(out)]) == 0
    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert {
        "entry",
        "before_turn6",
        "d_eligibility",
        "prompt_diff",
        "kristin_counterfactual",
        "per_turn",
        "limits",
    } <= report.keys()
    assert (out / "report.md").stat().st_size > 0
    scripted = report["before_turn6"]["SCRIPTED"]
    assert {"scene_1a_entry_known", "relay_open"} <= set(scripted["fact_predicates"])
    for label in ("Kristin", "Michelle", "captives group"):
        assert scripted["parents"][label]["parent"] is not None
    places = report["prompt_diff"]["things_places_called_out"]["SCRIPTED"]
    assert places["Michelle"]["present"]
    assert places["captives"]["present"]


def test_grouped_set_difference_on_fixtures() -> None:
    result = compare.grouped_set_difference(
        {"wk_parent", "relay_open", "scene_3c_entry_known", "left_only"},
        {"wk_parent", "captives_reaching_surface", "scene_3c_entry_known", "right_only"},
    )
    assert "world (wk_*)" not in result
    assert result["relay"]["present_live_absent_scripted"] == ["relay_open"]
    assert result["captives"]["present_scripted_absent_live"] == ["captives_reaching_surface"]
    assert result["right"]["present_scripted_absent_live"] == ["right_only"]


def test_recorded_bundle_loader_fails_loudly_on_missing_shape(tmp_path: Path) -> None:
    path = tmp_path / "bad-bundle.json"
    path.write_text(json.dumps({"replicates": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="recorded bundle shape"):
        compare.load_recorded_bundle(path)

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ringer.stage7 import three_c_state_compare as compare


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

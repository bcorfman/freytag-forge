from __future__ import annotations

import json
from pathlib import Path

import check_three_c_probe as checker
import pytest
import three_c_probe as probe

from bench.core import load_variation, package_and_state
from storygame.runtime.world_model import world_for

ROOT = Path(__file__).resolve().parents[1]
PLACES = ("maintenance_network", "facility_escape")


def _package_and_state():
    variation = load_variation(probe.variation_paths(("control",))["control"])
    return package_and_state(variation, "3C")


def test_default_chamber_dry_output_matches_checked_in_proof(tmp_path: Path) -> None:
    expected = ROOT / "bench/results/stage7-3c-carried-dry"
    probe.dry_run(tmp_path, 1, "carried", "on", ("pump", "families"), None)
    for name in ("source.json", "plan.json"):
        expected_bytes = (expected / name).read_bytes().replace(b"/home/bcorfman/dev/freytag-forge", str(ROOT).encode())
        assert (tmp_path / name).read_bytes() == expected_bytes


@pytest.mark.parametrize("place", PLACES)
def test_postc_prefix_moves_kristin_and_preserves_reveals(place: str) -> None:
    package, state = _package_and_state()
    probe.assert_3c_entry_facts(state)
    prefix = probe.apply_postc_prefix(package, state, place)
    world = world_for(package, state.facts)
    assert world.parent("kristin") == place
    assert prefix["committed_reveal_ids"] == [item[0] for item in probe.POSTC_REVEALS]
    assert "resolution_escape" in state.fired_event_ids


@pytest.mark.parametrize("place", PLACES)
def test_postc_prefix_c_r2_response_has_shipped_escape_delivery_once(place: str) -> None:
    package, state = _package_and_state()
    probe.assert_3c_entry_facts(state)
    prefix = probe.apply_postc_prefix(package, state, place)
    shipped = next(
        event.delivery_text for event in package.storylet_routes.resolution_events if event.id == "resolution_escape"
    )
    c_r2_response = next(turn["response"] for turn in prefix["turns"] if turn["knowledge_id"] == "k_sl_3c_c_r2")
    assert c_r2_response.count(shipped) == 1


def test_non_postc_kristin_place_is_rejected_before_execution(tmp_path: Path) -> None:
    with pytest.raises(SystemExit, match="only valid with --start postc"):
        probe.main(
            [
                "--n",
                "1",
                "--out",
                str(tmp_path),
                "--start",
                "entry",
                "--kristin-place",
                "facility_escape",
                "--dry-run",
            ]
        )
    assert not (tmp_path / "source.json").exists()


@pytest.mark.parametrize("place", PLACES)
def test_non_default_dry_artifacts_pass_checker(tmp_path: Path, place: str) -> None:
    probe.dry_run(tmp_path, 1, "postc", "off", ("control", "pre667"), None, place)
    assert checker.check(tmp_path, 1, "dry") == []
    source = json.loads((tmp_path / "source.json").read_text())
    plan = json.loads((tmp_path / "plan.json").read_text())
    assert source["kristin_place"] == plan["kristin_place"] == place

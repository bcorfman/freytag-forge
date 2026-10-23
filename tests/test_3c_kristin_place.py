from __future__ import annotations

from pathlib import Path

import pytest
import three_c_probe as probe

from bench.core import load_variation, package_and_state

ROOT = Path(__file__).resolve().parents[1]
PLACES = ("maintenance_network", "facility_escape")


def _package_and_state():
    variation = load_variation(probe.variation_paths(("control",))["control"])
    return package_and_state(variation, "3C")


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

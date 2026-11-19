"""Each cap is the count measured before that scene's richer data change."""

from pathlib import Path

import pytest

from storygame.audit import audit_package

ROOT = Path("data/stories/continuity-initiative")


@pytest.fixture(scope="module")
def findings():
    return audit_package(ROOT)["findings"]


@pytest.mark.parametrize(
    ("scene_id", "cap"),
    [("1C", 0), ("2A", 2), ("2B", 5), ("2C", 4), ("3A", 1)],
    ids=["1C", "2A", "2B", "2C", "3A"],
)
def test_the_richer_scene_adds_no_beat_overprojection(scene_id, cap, findings):
    overprojection = [
        finding
        for finding in findings
        if finding["check"] == "beat_overprojection" and finding.get("scene_id") == scene_id
    ]
    # The 1A findings are known and older; use them to prove this filter is non-vacuous.
    assert any(finding.get("scene_id") == "1A" for finding in findings if finding["check"] == "beat_overprojection")
    assert len(overprojection) <= cap

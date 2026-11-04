from __future__ import annotations

import re
from pathlib import Path

from storygame.runtime.validation import unconveyed_terms
from storygame.story_package.loader import load_story_package

LIVE_PACKAGE = Path("data/stories/continuity-initiative")
FROZEN_PACKAGE = Path("bench/frozen/continuity-pre-richer-2b")


def _collapse_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _entries(package_path: Path) -> dict[str, object]:
    package = load_story_package(package_path)
    return {entry.id: entry for entry in package.knowledge.knowledge}


def test_the_door_delivery_is_only_the_quote() -> None:
    entry = _entries(LIVE_PACKAGE)["k_sl_1c_f_r1"]

    assert _collapse_whitespace(entry.delivery_text) == 'Brandon says only, "Somebody has to watch the door."'
    assert [list(group) for group in entry.must_convey] == [["Brandon"], ["door"]]


def test_the_door_stance_lives_in_the_scene_details() -> None:
    package = load_story_package(LIVE_PACKAGE)
    scene = next(scene for scene in package.scenes if scene.metadata.scene_id == "1C")
    expected_details = [
        "observation shaft",
        "sedated prisoners",
        "processing line",
        "identification numbers",
        "woman resembling Michelle",
        "service entrance",
        "Brandon at the top of the stairs with his back to the processing line, watching the door",
    ]
    details = [list(beat.details) for beat in scene.beats.values()]

    assert expected_details in details
    assert "Brandon watching the door" not in {detail for beat in details for detail in beat}


def test_the_badge_delivery_has_no_closing_beat() -> None:
    entry = _entries(LIVE_PACKAGE)["k_sl_2b_e_r1"]

    assert _collapse_whitespace(entry.delivery_text) == (
        "In the build record, the access section lists what the badge readers check. "
        "There are three checks, the same three Brandon said he knew at the gate."
    )


def test_gating_and_conveyance_are_unchanged() -> None:
    live_entries = _entries(LIVE_PACKAGE)
    frozen_entries = _entries(FROZEN_PACKAGE)

    live = live_entries["k_sl_1c_f_r1"].model_dump(mode="json")
    frozen = frozen_entries["k_sl_1c_f_r1"].model_dump(mode="json")
    live.pop("delivery_text")
    frozen.pop("delivery_text")
    assert live == frozen

    for entry_id in ("k_sl_1c_f_r1", "k_sl_2b_e_r1"):
        entry = live_entries[entry_id]
        assert unconveyed_terms(entry.must_convey, entry.delivery_text) == ()

    assert [list(group) for group in live_entries["k_sl_2b_e_r1"].must_convey] == [
        ["badge readers"],
        ["three"],
        ["Brandon"],
    ]

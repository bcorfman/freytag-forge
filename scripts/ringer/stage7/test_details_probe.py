from __future__ import annotations

import hashlib
from pathlib import Path

from check_door_probe import check
from door_probe import EXPERIMENTS, TRANSITION_CAPS, build_source, dry_run
from door_prompt import patch_prompt, select_prompt
from payload_2b import capture

from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[3]
PACKAGE_FILES = (
    "handoffs.yaml",
    "knowledge.yaml",
    "pacing.yaml",
    "plot.md",
    "storylet-routes.yaml",
    "storylets.md",
    "world.yaml",
)
FROZEN_SHA256 = {
    "handoffs.yaml": "7a2e4d1eaa9e0f298f151c7462fb86185fc07f25b8e5a5408b2eb1cde3cbe00a",
    "knowledge.yaml": "f74523535c25f71ce7f05a4c81707fb4d4693aeaa68bd41c64439869493605f8",
    "pacing.yaml": "a5ece909890e08e3a2747447ab6f36652a654d9d06e00cff2356e6558de89783",
    "plot.md": "1beafff1ef00d1a110868b4809f6541035cfb95353f806fb123229541c2b1f97",
    "storylet-routes.yaml": "71003a4a9fd4ecf8721f3fcccd326e8ef8b91500c26a63a3c3c62841a4940f4b",
    "storylets.md": "94f53a26fa80aa0dfcdbaa6294a80600117557b82207119d028bdf953deafb42",
    "world.yaml": "d69165b0b171b668869cb863298084fca7de0e189d9d4d0b9932896b0eda44f7",
}


def test_frozen_package_is_head_and_both_packages_load() -> None:
    frozen = ROOT / "bench/frozen/continuity-pre-details"
    current = ROOT / "data/stories/continuity-initiative"
    assert load_story_package(frozen).story_id == load_story_package(current).story_id
    assert {name: hashlib.sha256((frozen / name).read_bytes()).hexdigest() for name in PACKAGE_FILES} == FROZEN_SHA256
    assert [name for name in PACKAGE_FILES if (frozen / name).read_bytes() != (current / name).read_bytes()] == [
        "knowledge.yaml",
        "plot.md",
    ]


def test_details_payload_changes_only_authored_details_bullets() -> None:
    command = "Examine the hidden panel closely, then try to open it."
    baseline = capture(ROOT / "bench/variations/stage7-details-control.json", command)
    details = capture(ROOT / "bench/variations/stage7-door-grounded.json", command)
    assert baseline["system"] == details["system"]
    assert "- unfamiliar system files\n" in baseline["user"]
    assert "- government data\n" in baseline["user"]
    assert "- financial data\n" in baseline["user"]
    assert "- the Initiative’s selection files\n" in details["user"]
    assert baseline["user"].index("- Michelle’s research") < baseline["user"].index("- The archive crisis")
    assert details["user"].index("- Michelle’s research") < details["user"].index("- the Initiative’s selection files")


def test_details_still_rejects_current_merged_package(tmp_path: Path) -> None:
    import pytest

    with pytest.raises(AssertionError, match="details continuation packages differ outside plot.md"):
        build_source(tmp_path, "details")


def test_merged_dry_run_and_prompt_hashes(tmp_path: Path) -> None:
    dry_run(tmp_path, 1, "merged")
    assert check(tmp_path, 1, "dry", "merged") == []
    source = __import__("json").loads((tmp_path / "source-before.json").read_text(encoding="utf-8"))
    assert source["merged_assertions"]["prompt_hashes_identical"] is True
    assert "plot.md" in source["merged_assertions"]["package_delta"]
    assert "knowledge.yaml" in source["merged_assertions"]["package_delta"]
    assert source["prompts"]["baseline"]["hashes"] == source["prompts"]["details"]["hashes"]


def test_checker_rejects_merged_without_merged_assertions(tmp_path: Path) -> None:
    dry_run(tmp_path, 1, "merged")
    source_path = tmp_path / "source-before.json"
    source = __import__("json").loads(source_path.read_text(encoding="utf-8"))
    del source["merged_assertions"]
    source_path.write_text(__import__("json").dumps(source), encoding="utf-8")
    assert any("merged_assertions is missing" in error for error in check(tmp_path, 1, "dry", "merged"))


def test_details_caps_and_existing_experiments_remain_registered() -> None:
    assert EXPERIMENTS["details"]["caps"] == TRANSITION_CAPS
    assert EXPERIMENTS["details"]["arms"] == ("baseline", "details")
    assert EXPERIMENTS["merged"]["caps"] == TRANSITION_CAPS
    assert EXPERIMENTS["merged"]["arms"] == ("baseline", "details")
    assert EXPERIMENTS["transition"]["arms"] == ("control", "grounded")
    assert EXPERIMENTS["grounded"]["caps"][1] == {"raw": 2, "cloudflare": 10, "player": 4}
    assert EXPERIMENTS["source"]["arms"] == ("control", "location", "limits")
    assert (
        patch_prompt(select_prompt(), "baseline", "details")["hashes"]
        == patch_prompt(select_prompt(), "details", "details")["hashes"]
    )

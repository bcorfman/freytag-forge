from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package import situation_trace
from storygame.story_package.gap_rules import CustodyCheck, custody_checks
from storygame.story_package.loader import load_story_package
from storygame.story_package.situation_trace import render_situation_trace

ROOT = Path("data/stories/continuity-initiative")


@pytest.mark.parametrize("anchor", ("officer_presses_1a", "i_2a_real_leak", "t_1b_1c"))
def test_trace_has_three_non_empty_sections(anchor: str) -> None:
    text = render_situation_trace(ROOT, anchor)

    for heading in (
        "## 1. The situation",
        "## 2. Where the situation leads",
        "## 3. What the next scene needs",
    ):
        assert heading in text
    assert all(section.strip() for section in text.split("## 1. The situation", 1)[1].split("## 2.", 1))


def test_pacing_event_contains_independent_source_facts() -> None:
    text = render_situation_trace(ROOT, "officer_presses_1a")

    assert "fires at turn 7" in text
    assert "`card_challenged`" in text
    assert "claim k_sl_1a_b_r0w from SL-1A-E-R2" in text
    assert "Transition `t_1a_1b` needs all of:" in text


@pytest.mark.parametrize("anchor", ("officer_presses_1a", "t_1b_1c"))
def test_trace_includes_authored_source_scene_frame(anchor: str) -> None:
    package = load_story_package(ROOT)
    event = next((event for event in package.pacing.events if event.id == anchor), None)
    source_scene_id = (
        event.scene_id
        if event
        else next(transition.source_scene_id for transition in package.pacing.transitions if transition.id == anchor)
    )
    frame = next(frame for frame in package.knowledge.scene_frames if frame.scene_id == source_scene_id)

    text = render_situation_trace(ROOT, anchor)

    if frame.situation:
        assert f"Situation in scene {source_scene_id}: {frame.situation}" in text
    assert f"Pressure in scene {source_scene_id}: {frame.pressure}" in text


def test_trace_reports_computed_holder_check() -> None:
    package = load_story_package(ROOT)
    checks = custody_checks(package, "officer_presses_1a")
    check = next(check for check in checks if check.item_id == "memory_card")

    text = render_situation_trace(ROOT, "officer_presses_1a")

    assert not check.holder_checked
    assert (
        f"Claim `{check.claim_id}`: the engine does not check whether "
        f"`{check.character_id}` holds `{check.item_id}` (tested by moving it)."
    ) in text


def test_transition_trace_reports_untested_holder_check() -> None:
    package = load_story_package(ROOT)
    check = next(check for check in custody_checks(package, "t_1a_1b") if check.status == "untested")

    text = render_situation_trace(ROOT, "t_1a_1b")

    assert "No held item is named by these claims." not in text
    assert (
        f"Claim `{check.claim_id}` names `{check.item_id}`; whether the engine checks who holds it "
        "was not tested here, because no other character is with the protagonist in this anchor's starting state."
    ) in text


def test_trace_can_render_holder_checked_for_seeded_clean_copy(tmp_path: Path, monkeypatch) -> None:
    package_root = tmp_path / "package"
    shutil.copytree(ROOT, package_root)
    package = load_story_package(package_root)
    check = next(check for check in custody_checks(package, "officer_presses_1a") if check.item_id == "memory_card")
    patched_check = CustodyCheck(check.claim_id, check.item_id, check.character_id, status="checked")
    monkeypatch.setattr(situation_trace, "custody_checks", lambda _package, _anchor: [patched_check])

    text = render_situation_trace(package_root, "officer_presses_1a")

    assert (
        f"Claim `{check.claim_id}`: the engine checks whether "
        f"`{check.character_id}` holds `{check.item_id}` (tested by moving it)."
    ) in text


def test_trace_reports_no_held_item_when_claim_does_not_name_one(tmp_path: Path) -> None:
    package_root = tmp_path / "package"
    shutil.copytree(ROOT, package_root)
    package = load_story_package(package_root)
    check = next(check for check in custody_checks(package, "t_1a_1b") if check.status == "untested")

    knowledge_path = package_root / "knowledge.yaml"
    knowledge = yaml.safe_load(knowledge_path.read_text(encoding="utf-8"))
    for check in custody_checks(package, "t_1a_1b"):
        claim = next(item for item in knowledge["knowledge"] if item["id"] == check.claim_id)
        claim["entity_ids"].remove(check.item_id)
        claim["relevance"]["entity_ids"].remove(check.item_id)
    knowledge_path.write_text(yaml.safe_dump(knowledge, sort_keys=False), encoding="utf-8")

    text = render_situation_trace(package_root, "t_1a_1b")

    assert "No held item is named by these claims." in text


def test_unknown_anchor_raises() -> None:
    with pytest.raises(ValueError, match=r"unknown anchor 'missing_anchor'"):
        render_situation_trace(ROOT, "missing_anchor")


def test_event_and_transition_duplicate_anchor_is_ambiguous(tmp_path: Path) -> None:
    package_root = tmp_path / "package"
    shutil.copytree(ROOT, package_root)
    pacing_path = package_root / "pacing.yaml"
    pacing = yaml.safe_load(pacing_path.read_text(encoding="utf-8"))
    event = next(item for item in pacing["events"] if item["id"] == "officer_presses_1a")
    event["id"] = "t_1b_1c"
    pacing_path.write_text(yaml.safe_dump(pacing, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match=r"ambiguous anchor 't_1b_1c'.*pacing event.*transition"):
        render_situation_trace(package_root, "t_1b_1c")


def test_render_is_deterministic() -> None:
    first = render_situation_trace(ROOT, "officer_presses_1a")
    second = render_situation_trace(ROOT, "officer_presses_1a")

    assert first == second


def test_render_does_not_change_package_files() -> None:
    before = {path.relative_to(ROOT): path.read_bytes() for path in ROOT.rglob("*") if path.is_file()}

    render_situation_trace(ROOT, "officer_presses_1a")

    after = {path.relative_to(ROOT): path.read_bytes() for path in ROOT.rglob("*") if path.is_file()}
    assert before == after


@pytest.mark.parametrize("anchor", ("officer_presses_1a", "i_2a_real_leak", "t_1b_1c"))
def test_trace_leaves_discovery_to_the_reviewer(anchor: str) -> None:
    text = render_situation_trace(ROOT, anchor)

    assert "## 4." not in text
    assert "## 5." not in text
    assert "| Response |" not in text
    assert "# Gaps" not in text

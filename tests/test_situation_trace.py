from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

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

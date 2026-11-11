from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml

from storygame.story_package.branch_report import render_branch_report
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1] / "data" / "stories" / "continuity-initiative"


def _copy_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(ROOT, destination)
    return destination


def _edit_yaml(root: Path, filename: str, edit) -> None:
    path = root / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _incident(data: dict, scene_id: str = "2C") -> dict:
    return next(item for item in data["incidents"] if item["scene_id"] == scene_id)


def _outcome(data: dict, outcome_id: str) -> dict:
    return next(item for item in _incident(data)["outcomes"] if item["id"] == outcome_id)


def _claim(data: dict, claim_id: str) -> dict:
    return next(item for item in data["knowledge"] if item["id"] == claim_id)


def _scene_block(root: Path, scene_id: str) -> tuple[str, str, str]:
    path = root / "plot.md"
    text = path.read_text(encoding="utf-8")
    start = text.index(f"## Scene {scene_id} ")
    end = text.find("\n## Scene ", start)
    end = len(text) if end == -1 else end
    return str(path), text[:start], text[start:end]


def _replace_scene_block(root: Path, scene_id: str, replacement) -> None:
    path_string, before, block = _scene_block(root, scene_id)
    path = Path(path_string)
    path.write_text(
        before + replacement(block) + path.read_text(encoding="utf-8")[len(before) + len(block) :], encoding="utf-8"
    )


def _remove_rescue_variant(root: Path) -> None:
    def edit(block: str) -> str:
        marker = "entry_variants:\n- requires: [committed_to_rescue]\n"
        start = block.index(marker)
        end = block.index("transition_ids:", start)
        return block[:start] + "entry_variants: []\n" + block[end:]

    _replace_scene_block(root, "3A", edit)


def _move_target_item(root: Path, parent: str) -> None:
    def edit(block: str) -> str:
        for old_parent in ("kristin", "detention_level"):
            old = f"  copied_janus_files: {{parent: {old_parent}}}\n"
            if old in block:
                return block.replace(old, f"  copied_janus_files: {{parent: {parent}}}\n", 1)
        raise AssertionError("target item placement is missing")

    _replace_scene_block(root, "3A", edit)


def test_declared_costs_distinguish_unset_and_unread(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def seed(data: dict) -> None:
        _outcome(data, "committed_to_transmit")["costs"] = [
            "evidence_ready_to_transmit",
            "detention_sectors_sealed",
        ]

    _edit_yaml(package_root, "incidents.yaml", seed)
    _edit_yaml(
        package_root,
        "knowledge.yaml",
        lambda data: _claim(data, "k_sl_2c_d_r3").update(
            establishes=[
                effect
                for effect in _claim(data, "k_sl_2c_d_r3")["establishes"]
                if effect["fact_id"] != "evidence_ready_to_transmit"
            ]
        ),
    )
    report = render_branch_report(
        package_root, _incident(yaml.safe_load((package_root / "incidents.yaml").read_text()))["id"]
    )
    assert "declares cost `evidence_ready_to_transmit`" in report
    assert "but the realization does not set it" in report
    assert "declares cost `detention_sectors_sealed`" in report
    assert "but nothing later reads it, so the cost has no effect" in report

    def clean(data: dict) -> None:
        _outcome(data, "committed_to_transmit")["costs"] = ["detention_sectors_sealed"]

    _edit_yaml(package_root, "incidents.yaml", clean)
    clean_report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    assert "declares cost `evidence_ready_to_transmit`" not in clean_report


def test_entry_variant_applies_only_to_branch_that_sets_advantage(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    rescue = report.split("## Branch `committed_to_rescue`", 1)[1].split("## Branch", 1)[0]
    transmit = report.split("## Branch `committed_to_transmit`", 1)[1].split("## Branch", 1)[0]
    rescue_applicable = rescue.split("Entry variants that apply", 1)[1].split("Entry variants that do not", 1)[0]
    transmit_applicable = transmit.split("Entry variants that apply", 1)[1].split("Entry variants that do not", 1)[0]
    assert "requires ('committed_to_rescue',)" in rescue_applicable
    assert "requires ('committed_to_rescue',)" not in transmit_applicable

    _remove_rescue_variant(package_root)
    clean_report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    assert "requires ('committed_to_rescue',)" not in clean_report


def test_target_placement_reports_loss_of_custody_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    _move_target_item(package_root, "detention_level")
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    assert "Result: Item `copied_janus_files` loses custody" in report
    assert "purge_chamber" in report and "detention_level" in report

    _move_target_item(package_root, "kristin")
    clean_report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    assert "Item `copied_janus_files` loses custody" not in clean_report


def test_handoff_bridge_text_is_once_per_branch_and_uses_plain_read_wording() -> None:
    package = load_story_package(ROOT)
    incident = next(item for item in package.incidents if item.scene_id == "2C")
    bridge_text = next(
        scene.metadata.bridge_text["t_2c_3a"] for scene in package.scenes if scene.metadata.scene_id == "2C"
    )
    report = render_branch_report(ROOT, incident.id)
    assert "through nothing" not in report
    for branch_section in report.split("## Branch `")[1:]:
        handoff = branch_section.split("### Handoff analysis", 1)[1].split("### Evidence for judgment", 1)[0]
        assert handoff.count(bridge_text) == 1


def test_handoff_separates_scene_setup_from_carried_state(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    _move_target_item(package_root, "detention_level")
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    handoff = report.split("### Handoff analysis", 1)[1].split("### Evidence for judgment", 1)[0]
    assert "\n\n- Handoff from `2C` to `3A`:" in handoff
    assert "\n- Carried over from the branch:\n  - " in handoff
    assert "\n- Appears with the next scene:\n  - " in handoff
    carried = handoff.split("Carried over from the branch:", 1)[1].split("Appears with the next scene:", 1)[0]
    appearing = handoff.split("Appears with the next scene:", 1)[1]
    assert "Item `emergency_surface_gates`" in appearing
    assert "Item `emergency_surface_gates`" not in carried
    assert "Result: Item `copied_janus_files` loses custody" in carried


def test_exit_transition_consumes_branch_fact() -> None:
    report = render_branch_report(ROOT, "i_2c_rebecca_corridor")
    assert "read by: transition t_2c_3a requires it (scene 2C)" in report


def test_real_incident_no_trace_line_names_only_later_scene_branches() -> None:
    report = render_branch_report(ROOT, "i_2c_rebecca_corridor")
    line = next(line for line in report.splitlines() if line.startswith("Branches that leave no trace"))
    assert line == (
        "Branches that leave no trace in any later scene: `committed_to_transmit`, `SL-2C-E`, `purge_window_2c`."
    )
    assert "`committed_to_rescue`" not in line


def test_exit_transition_only_reader_does_not_leave_later_trace(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def seed(data: dict) -> None:
        transition = next(item for item in data["transitions"] if item["id"] == "t_2c_3a")
        transition["triggers"] = [{"fact_id": "committed_to_transmit", "equals": True}]

    _edit_yaml(package_root, "pacing.yaml", seed)
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    line = next(line for line in report.splitlines() if line.startswith("Branches that leave no trace"))
    assert "`committed_to_transmit`" in line


def test_next_scene_reader_removes_branch_from_no_trace_line(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def seed(block: str) -> str:
        variant = (
            "entry_variants:\n"
            "- requires: [committed_to_transmit]\n"
            "  text: The transmit branch carries into the next scene.\n"
        )
        return block.replace(
            "entry_variants:\n",
            variant,
            1,
        )

    _replace_scene_block(package_root, "3A", seed)
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    line = next(line for line in report.splitlines() if line.startswith("Branches that leave no trace"))
    assert "`committed_to_transmit`" not in line


def test_branch_without_trigger_is_reported_as_dead_end_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def seed(data: dict) -> None:
        transition = next(item for item in data["transitions"] if item["id"] == "t_2c_3a")
        transition["triggers"] = [{"fact_id": "committed_to_transmit", "equals": True}]

    _edit_yaml(package_root, "pacing.yaml", seed)
    _edit_yaml(
        package_root,
        "handoffs.yaml",
        lambda data: data.update(
            deliveries=[item for item in data["deliveries"] if item["fact_id"] != "committed_to_transmit"]
        ),
    )
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    rescue = report.split("## Branch `committed_to_rescue`", 1)[1].split("## Branch", 1)[0]
    assert "Result: dead end" in rescue
    assert "unmet trigger facts: `committed_to_transmit`" in rescue

    def clean(data: dict) -> None:
        transition = next(item for item in data["transitions"] if item["id"] == "t_2c_3a")
        transition["triggers"] = [{"fact_id": "combined_broadcast_rescue_plan_known", "equals": True}]

    _edit_yaml(package_root, "pacing.yaml", clean)
    clean_report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    assert "Result: dead end" not in clean_report


def test_real_incident_renders_expected_costs_and_variant() -> None:
    package = load_story_package(ROOT)
    incident = next(item for item in package.incidents if item.scene_id == "2C")
    report = render_branch_report(ROOT, incident.id)
    assert "declares cost `detention_sectors_sealed`" in report
    assert "declares cost `evidence_not_transmitted`" in report
    assert "requires ('committed_to_rescue',)" in report


def test_pacing_event_and_unknown_id_raise_value_error() -> None:
    package = load_story_package(ROOT)
    event_id = package.pacing.events[0].id
    with pytest.raises(ValueError, match="not an incident"):
        render_branch_report(ROOT, event_id)
    with pytest.raises(ValueError, match="unknown incident"):
        render_branch_report(ROOT, "missing_incident")

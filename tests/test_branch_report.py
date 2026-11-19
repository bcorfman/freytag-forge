from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from storygame.story_package.branch_report import render_branch_report
from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy

ROOT = Path(__file__).resolve().parents[1] / "data" / "stories" / "continuity-initiative"


def _copy_package(tmp_path: Path) -> Path:
    return compiled_story_copy(tmp_path)


def _edit_source(root: Path, filename: str, edit) -> None:
    path = root / "source" / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _remove_delivery(root: Path, delivery_id: str) -> None:
    _edit_source(root, "scenes/2C.yaml", lambda data: data["facts"][delivery_id].pop("delivery"))

    def remove_match_delivery(data: dict) -> None:
        data["deliveries"].pop(delivery_id)

    _edit_source(root, "scenes/2C.match.yaml", remove_match_delivery)
    _edit_source(
        root,
        "scenes/2C.yaml",
        lambda data: _prune_order_id(data, "deliveries", delivery_id),
    )


def _prune_order_id(data: dict, kind: str, record_id: str) -> None:
    order = data.get("order")
    if isinstance(order, dict) and isinstance(order.get(kind), list):
        order[kind] = [item_id for item_id in order[kind] if item_id != record_id]
        if not order[kind]:
            order.pop(kind)
        if not order:
            data.pop("order")


def _incident(data: dict) -> dict:
    return next(item for item in data.incidents if item.scene_id == "2C")


def _outcome(data: dict, outcome_id: str) -> dict:
    reveal = next(item for item in data["reveals"] if item["id"] == "sl_2c_d")
    return next(variant for variant in reveal["variants"].values() if variant["outcome"]["id"] == outcome_id)["outcome"]


def _remove_entry_variants(root: Path) -> None:
    _edit_source(root, "scenes/3A.yaml", lambda data: data.update(entry_additions=[]))


def _move_target_item(root: Path, parent: str) -> None:
    def edit(data: dict) -> None:
        data["placements"]["copied_janus_files"]["parent"] = parent

    _edit_source(root, "scenes/3A.yaml", edit)


def test_declared_costs_distinguish_unset_and_unread(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def seed(data: dict) -> None:
        _outcome(data, "committed_to_transmit")["costs"] = [
            "evidence_ready_to_transmit",
            "rebecca_offer_active",
        ]

    _edit_source(package_root, "scenes/2C.yaml", seed)
    _edit_source(
        package_root,
        "scenes/2C.yaml",
        lambda data: data["reveals"][1]["variants"]["r3"].update(
            commits_subset={
                fact_id: value
                for fact_id, value in data["reveals"][1]["variants"]["r3"]["commits"].items()
                if fact_id != "evidence_ready_to_transmit"
            }
        ),
    )
    package = load_compiled_copy(package_root)
    report = render_branch_report(package_root, _incident(package).id)
    assert "declares cost `evidence_ready_to_transmit`" in report
    assert "but the realization does not set it" in report
    assert "declares cost `rebecca_offer_active`" in report
    assert "but nothing later reads it, so the cost has no effect" in report

    def clean(data: dict) -> None:
        _outcome(data, "committed_to_transmit")["costs"] = ["rebecca_offer_active"]

    _edit_source(package_root, "scenes/2C.yaml", clean)
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

    _remove_entry_variants(package_root)
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
    assert line == "Branches that leave no trace in any later scene: `SL-2C-E`, `purge_window_2c`."
    assert "`committed_to_rescue`" not in line
    assert "`committed_to_transmit`" not in line


def test_exit_transition_only_reader_does_not_leave_later_trace(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    _edit_source(package_root, "scenes/2C.yaml", lambda data: data["exit"].update(when_all=["committed_to_transmit"]))
    _remove_entry_variants(package_root)
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    line = next(line for line in report.splitlines() if line.startswith("Branches that leave no trace"))
    assert "`committed_to_transmit`" in line


def test_next_scene_reader_removes_branch_from_no_trace_line(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def seed(data: dict) -> None:
        data["entry_additions"] = [
            {"when": ["committed_to_transmit"], "text": "The transmit branch carries into the next scene."}
        ]

    _edit_source(package_root, "scenes/3A.yaml", seed)
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    line = next(line for line in report.splitlines() if line.startswith("Branches that leave no trace"))
    assert "`committed_to_transmit`" not in line


def test_branch_without_trigger_is_reported_as_dead_end_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    _edit_source(package_root, "scenes/2C.yaml", lambda data: data["exit"].update(when_all=["committed_to_transmit"]))

    _remove_delivery(package_root, "committed_to_transmit")
    report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    rescue = report.split("## Branch `committed_to_rescue`", 1)[1].split("## Branch", 1)[0]
    assert "Result: dead end" in rescue
    assert "unmet trigger facts: `committed_to_transmit`" in rescue

    _edit_source(
        package_root,
        "scenes/2C.yaml",
        lambda data: data["exit"].update(when_all=["combined_broadcast_rescue_plan_known"]),
    )
    clean_report = render_branch_report(package_root, "i_2c_rebecca_corridor")
    assert "Result: dead end" not in clean_report


def test_real_incident_renders_expected_costs_and_variant() -> None:
    package = load_story_package(ROOT)
    incident = next(item for item in package.incidents if item.scene_id == "2C")
    report = render_branch_report(ROOT, incident.id)
    assert "nothing later reads it, so the cost has no effect" not in report
    assert "`detention_sectors_sealed` ('" in report
    assert "read by scene 3A picks entry wording by it (scene 3A)" in report
    assert "`evidence_not_transmitted` ('" in report
    assert "read by scene 3B picks entry wording by it (scene 3B)" in report
    assert "requires ('committed_to_rescue',)" in report
    assert "requires ('detention_sectors_sealed',)" in report


def test_pacing_event_and_unknown_id_raise_value_error() -> None:
    package = load_story_package(ROOT)
    event_id = package.pacing.events[0].id
    with pytest.raises(ValueError, match="not an incident"):
        render_branch_report(ROOT, event_id)
    with pytest.raises(ValueError, match="unknown incident"):
        render_branch_report(ROOT, "missing_incident")

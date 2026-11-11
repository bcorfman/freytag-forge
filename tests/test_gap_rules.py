from __future__ import annotations

import re
import shutil
from pathlib import Path

import pytest
import yaml

from scripts.gap_rules import main
from storygame.story_package.gap_rules import custody_checks, exit_transitions, render_flags, run_gap_rules
from storygame.story_package.loader import load_story_package

ROOT = Path("data/stories/continuity-initiative")
MODULE = Path("storygame/story_package/gap_rules.py")


def _copy_package(tmp_path: Path) -> Path:
    destination = tmp_path / "package"
    shutil.copytree(ROOT, destination)
    return destination


def _edit_yaml(root: Path, filename: str, edit) -> None:
    path = root / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _claim(data: dict, claim_id: str) -> dict:
    return next(item for item in data["knowledge"] if item["id"] == claim_id)


def _add_world_fact(data: dict, fact_id: str) -> None:
    data["facts"].append(fact_id)


def _add_knowledge_fact(data: dict, fact_id: str) -> None:
    data["facts"].append({"id": fact_id, "purpose": "A synthetic gap-rule test fact."})


def _add_route_fact(data: dict, fact_id: str) -> None:
    data["new_fact_ids"].append(
        {
            "id": fact_id,
            "definition": "A synthetic gap-rule test fact.",
            "used_by_storylets": [],
            "used_by_transitions": [],
        }
    )


def _remove_asserted_fact(data: object, fact_id: str) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"effects", "establishes", "operations", "costs"} and isinstance(value, list):
                data[key] = [
                    item
                    for item in value
                    if not (
                        isinstance(item, dict)
                        and item.get("fact_id") == fact_id
                        and (item.get("op") == "assert" or item.get("equals") is True)
                    )
                ]
            _remove_asserted_fact(value, fact_id)
    elif isinstance(data, list):
        for item in data:
            _remove_asserted_fact(item, fact_id)


def test_real_data_reports_the_known_flags() -> None:
    flags = run_gap_rules(ROOT, "officer_presses_1a")

    assert any(
        flag.rule == "custody" and flag.subject == "k_sl_1a_b_r1" and "memory_card" in flag.summary for flag in flags
    )
    assert any(
        flag.rule == "co_location" and flag.subject == "k_sl_1a_b_r1" and "kristin_laptop" in flag.summary
        for flag in flags
    )
    assert any(
        flag.rule == "no_strand" and flag.subject == "k_sl_1a_b_r1" and "memory_card" in flag.summary for flag in flags
    )


def test_custody_checks_include_every_flagged_pair() -> None:
    package = load_story_package(ROOT)
    flags = run_gap_rules(ROOT, "officer_presses_1a", ["custody"])
    checks = custody_checks(package, "officer_presses_1a")

    for flag in flags:
        matching = [
            check for check in checks if check.claim_id == flag.subject and f"names {check.item_id} " in flag.summary
        ]
        assert matching
        assert all(not check.holder_checked for check in matching)


def test_custody_checks_report_untested_transition_pairs() -> None:
    package = load_story_package(ROOT)
    checks = custody_checks(package, "t_1a_1b")

    assert checks
    assert all(check.status == "untested" for check in checks)
    assert all(check.character_id is None for check in checks)


def test_custody_checks_report_checked_moves_as_unchecked_rows() -> None:
    package = load_story_package(ROOT)
    checks = custody_checks(package, "officer_presses_1a")

    assert checks
    assert all(check.status == "unchecked" for check in checks)
    assert all(check.character_id is not None for check in checks)


def test_untested_custody_rows_do_not_produce_flags() -> None:
    assert not run_gap_rules(ROOT, "t_1a_1b", ["custody"])


def test_real_data_citations_point_to_record_definitions() -> None:
    rendered = render_flags(run_gap_rules(ROOT, "officer_presses_1a"), "officer_presses_1a")
    citation = re.compile(r"(?P<path>\S+\.(?:yaml|md)):(?P<line>\d+)$")
    id_definition = re.compile(r"\bid:\s*[A-Za-z0-9_.-]+(?=\s*(?:$|[,}#]))")
    bare_key = re.compile(r"\s*[A-Za-z0-9_.-]+:\s*(?:#.*)?$")

    for evidence in rendered.splitlines():
        match = citation.search(evidence)
        if match is None:
            continue
        source = ROOT / match.group("path")
        source_line = source.read_text(encoding="utf-8").splitlines()[int(match.group("line")) - 1]
        assert id_definition.search(source_line) or bare_key.fullmatch(source_line), source_line


def test_baseline_holder_simulation_has_no_citation() -> None:
    flags = run_gap_rules(ROOT, "officer_presses_1a", ["custody"])
    simulation_lines = [
        evidence for flag in flags for evidence in flag.evidence if evidence.startswith("holder at baseline:")
    ]
    assert simulation_lines
    assert all(re.search(r"\S+\.(?:yaml|md):\d+$", line) is None for line in simulation_lines)


def test_no_strand_reports_already_true_effect() -> None:
    flags = run_gap_rules(ROOT, "officer_presses_1a", ["no_strand"])
    assert any(
        "already true, so it cannot fire again" in evidence
        for flag in flags
        if flag.subject == "k_sl_1a_b_r1"
        for evidence in flag.evidence
    )


def test_custody_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    _edit_yaml(
        package_root,
        "knowledge.yaml",
        lambda data: _claim(data, "k_sl_1a_b_r1").update(
            entity_ids=list(dict.fromkeys(_claim(data, "k_sl_1a_b_r1")["entity_ids"]))
        ),
    )
    flags = run_gap_rules(package_root, "officer_presses_1a", ["custody"])
    assert any(flag.subject == "k_sl_1a_b_r1" and "memory_card" in flag.summary for flag in flags)

    def clean(data: dict) -> None:
        claim = _claim(data, "k_sl_1a_b_r1")
        claim["entity_ids"].remove("memory_card")
        claim["relevance"]["entity_ids"].remove("memory_card")

    _edit_yaml(package_root, "knowledge.yaml", clean)
    flags = run_gap_rules(package_root, "officer_presses_1a", ["custody"])
    assert not any(flag.subject == "k_sl_1a_b_r1" for flag in flags)


def test_co_location_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    _edit_yaml(package_root, "knowledge.yaml", lambda data: _claim(data, "k_sl_1a_b_r1").update(reach_entity_ids=[]))
    flags = run_gap_rules(package_root, "officer_presses_1a", ["co_location"])
    assert any(flag.subject == "k_sl_1a_b_r1" and "kristin_laptop" in flag.summary for flag in flags)

    _edit_yaml(
        package_root,
        "knowledge.yaml",
        lambda data: _claim(data, "k_sl_1a_b_r1").update(reach_entity_ids=["kristin_laptop"]),
    )
    flags = run_gap_rules(package_root, "officer_presses_1a", ["co_location"])
    assert not any(flag.subject == "k_sl_1a_b_r1" for flag in flags)


def test_no_strand_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    assert any(
        flag.subject == "k_sl_1a_b_r1" for flag in run_gap_rules(package_root, "officer_presses_1a", ["no_strand"])
    )

    def add_non_item_gated_producer(data: dict) -> None:
        event = next(item for item in data["events"] if item["id"] == "officer_presses_1a")
        event["effects"].append({"fact_id": "michelle_lead_actionable", "equals": True})

    _edit_yaml(package_root, "pacing.yaml", add_non_item_gated_producer)
    flags = run_gap_rules(package_root, "officer_presses_1a", ["no_strand"])
    assert not any(flag.subject == "k_sl_1a_b_r1" for flag in flags)


def test_no_producer_seeded_defect_loads_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    assert not run_gap_rules(Path(ROOT), "pursuit_1b", ["no_producer"])

    for filename in ("pacing.yaml", "knowledge.yaml", "storylet-routes.yaml", "handoffs.yaml"):
        _edit_yaml(package_root, filename, lambda data: _remove_asserted_fact(data, "kristin_marked_by_patrol"))

    assert load_story_package(package_root)
    flags = run_gap_rules(package_root, "pursuit_1b", ["no_producer"])
    assert any(flag.subject == "kristin_marked_by_patrol" for flag in flags)


def test_unread_effect_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    fact_id = "gap_rule_unread_fact"

    _edit_yaml(package_root, "world.yaml", lambda data: _add_world_fact(data, fact_id))
    _edit_yaml(package_root, "knowledge.yaml", lambda data: _add_knowledge_fact(data, fact_id))
    _edit_yaml(package_root, "storylet-routes.yaml", lambda data: _add_route_fact(data, fact_id))

    def add_effect(data: dict) -> None:
        event = next(item for item in data["events"] if item["id"] == "pursuit_1b")
        event["effects"].append({"fact_id": fact_id, "equals": True})

    def remove_effect(data: dict) -> None:
        event = next(item for item in data["events"] if item["id"] == "pursuit_1b")
        event["effects"] = [item for item in event["effects"] if item["fact_id"] != fact_id]

    _edit_yaml(package_root, "pacing.yaml", add_effect)
    assert load_story_package(package_root)
    flags = run_gap_rules(package_root, "pursuit_1b", ["unread_effect"])
    assert any(flag.subject == fact_id for flag in flags)

    _edit_yaml(package_root, "pacing.yaml", remove_effect)
    flags = run_gap_rules(package_root, "pursuit_1b", ["unread_effect"])
    assert not any(flag.subject == fact_id for flag in flags)


def test_real_dependency_results_match_the_audit_inventory() -> None:
    package = load_story_package(ROOT)
    anchors = [event.id for event in package.pacing.events]
    anchors += [incident.id for incident in package.incidents]
    anchors += [transition.id for transition in package.pacing.transitions]

    expected_by_anchor = {
        "audit_nudge_2b": ("janus_known", "kristin_was_bait", "michelle_selected_for_resistance_influence"),
        "audit_recovery_2b": ("janus_known", "kristin_was_bait", "michelle_selected_for_resistance_influence"),
        "audit_window_2b": ("janus_known", "kristin_was_bait", "michelle_selected_for_resistance_influence"),
        "collapse_3c": ("facility_collapse_escalating",),
        "destruction_3b": ("facility_destruction_threat",),
        "detention_lockdown_3a": ("detention_lockdown_spreading",),
        "home_search_narrows_1a": ("home_search_window_narrowing", "house_marked_for_return"),
        "i_1c_freight_transfer": ("terminal_sweep_closing", "trust_brandon"),
        "i_2a_real_leak": ("supervisor_convinced",),
        "i_2b_audit": ("janus_known", "kristin_was_bait", "michelle_selected_for_resistance_influence"),
        "i_2c_rebecca_corridor": (
            "antagonist_split_known",
            "detention_sectors_sealed",
            "evidence_not_transmitted",
            "rebecca_offer_active",
        ),
        "inspection_nudge_2a": ("supervisor_convinced",),
        "inspection_recovery_2a": ("supervisor_convinced",),
        "inspection_window_2a": ("supervisor_convinced",),
        "kristin_steadies_1a": ("house_marked_for_return",),
        "officer_presses_1a": ("house_marked_for_return",),
        "park_lockdown_1b": ("park_lockdown_spreading",),
        "patrol_arrives_1a": ("house_marked_for_return",),
        "patrol_enters_1a": ("house_marked_for_return",),
        "patrol_leaves_1a": ("house_marked_for_return",),
        "patrol_returns_1a": ("house_marked_for_return",),
        "purge_nudge_2c": (
            "antagonist_split_known",
            "detention_sectors_sealed",
            "evidence_not_transmitted",
            "rebecca_offer_active",
        ),
        "purge_recovery_2c": (
            "antagonist_split_known",
            "detention_sectors_sealed",
            "evidence_not_transmitted",
            "rebecca_offer_active",
        ),
        "purge_window_2c": (
            "antagonist_split_known",
            "detention_sectors_sealed",
            "evidence_not_transmitted",
            "rebecca_offer_active",
        ),
        "pursuit_1b": ("pursuit_closing_in",),
        "relay_power_3b": ("relay_power_failing",),
        "reyes_rams_drawer_1a": ("house_marked_for_return",),
        "routes_collapse_3c": ("escape_routes_collapsing",),
        "t_1a_1b": ("house_marked_for_return",),
        "t_1c_2a": ("terminal_sweep_closing", "trust_brandon"),
        "t_2a_2b": ("supervisor_convinced",),
        "t_2b_2c": ("janus_known", "kristin_was_bait", "michelle_selected_for_resistance_influence"),
        "t_2c_3a": (
            "antagonist_split_known",
            "detention_sectors_sealed",
            "evidence_not_transmitted",
            "rebecca_offer_active",
        ),
        "transfer_nudge_1c": ("brandon_urges_retreat", "terminal_sweep_closing", "trust_brandon"),
        "transfer_window_1c": ("terminal_sweep_closing", "trust_brandon"),
        "transfer_withdrawal_1c": ("terminal_sweep_closing", "trust_brandon"),
    }
    expected = {
        ("unread_effect", anchor, fact_id) for anchor, fact_ids in expected_by_anchor.items() for fact_id in fact_ids
    }

    actual = {
        (flag.rule, flag.anchor, flag.subject)
        for anchor in anchors
        for flag in run_gap_rules(ROOT, anchor, ["no_producer", "unread_effect"])
    }
    assert actual == expected


def test_single_reveal_strand_has_no_flags_for_every_transition() -> None:
    package = load_story_package(ROOT)

    for transition in package.pacing.transitions:
        assert not run_gap_rules(ROOT, transition.id, ["single_reveal_strand"])


def test_single_reveal_strand_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def remove_exit_fact(data: dict) -> None:
        route = next(item for item in data["storylets"] if item["id"] == "SL-1A-E")
        realization = next(item for item in route["realization_options"] if item["id"] == "SL-1A-E-R1")
        operation = next(item for item in realization["operations"] if item["fact_id"] == "memory_card_recovered")
        operation["fact_id"] = "drawer_opened"

    def restore_exit_fact(data: dict) -> None:
        route = next(item for item in data["storylets"] if item["id"] == "SL-1A-E")
        realization = next(item for item in route["realization_options"] if item["id"] == "SL-1A-E-R1")
        operation = next(item for item in realization["operations"] if item["fact_id"] == "drawer_opened")
        operation["fact_id"] = "memory_card_recovered"

    def edit_knowledge(data: dict, fact_id: str) -> None:
        claim = _claim(data, "k_sl_1a_b_r0")
        effect = next(
            item for item in claim["establishes"] if item["fact_id"] in {"memory_card_recovered", "drawer_opened"}
        )
        effect["fact_id"] = fact_id

    _edit_yaml(package_root, "storylet-routes.yaml", remove_exit_fact)
    _edit_yaml(package_root, "knowledge.yaml", lambda data: edit_knowledge(data, "drawer_opened"))
    flags = run_gap_rules(package_root, "t_1a_1b", ["single_reveal_strand"])
    assert any(flag.subject == "SL-1A-E/SL-1A-E-R1" and "memory_card_recovered" in flag.summary for flag in flags)

    _edit_yaml(package_root, "storylet-routes.yaml", restore_exit_fact)
    _edit_yaml(package_root, "knowledge.yaml", lambda data: edit_knowledge(data, "memory_card_recovered"))
    flags = run_gap_rules(package_root, "t_1a_1b", ["single_reveal_strand"])
    assert not any(flag.subject == "SL-1A-E/SL-1A-E-R1" for flag in flags)


def test_unknown_anchor_and_rule_raise() -> None:
    with pytest.raises(ValueError, match=r"unknown anchor 'missing_anchor'"):
        run_gap_rules(ROOT, "missing_anchor")
    with pytest.raises(ValueError, match=r"unknown rule 'missing_rule'"):
        run_gap_rules(ROOT, "officer_presses_1a", ["missing_rule"])


def test_anchor_resolution_and_control_anchor() -> None:
    package = load_story_package(ROOT)
    assert [item.id for item in exit_transitions(package, "officer_presses_1a")] == ["t_1a_1b"]
    run_gap_rules(ROOT, "i_2a_real_leak")


def test_ambiguous_anchor_uses_situation_trace_wording(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def duplicate(data: dict) -> None:
        next(item for item in data["events"] if item["id"] == "officer_presses_1a")["id"] = "t_1b_1c"

    _edit_yaml(package_root, "pacing.yaml", duplicate)
    with pytest.raises(ValueError, match=r"ambiguous anchor 't_1b_1c'.*pacing event.*transition"):
        run_gap_rules(package_root, "t_1b_1c")


def test_output_and_inputs_are_deterministic_and_read_only() -> None:
    before = {path.relative_to(ROOT): path.read_bytes() for path in ROOT.rglob("*") if path.is_file()}
    first = run_gap_rules(ROOT, "officer_presses_1a")
    second = run_gap_rules(ROOT, "officer_presses_1a")
    assert first == second
    assert render_flags(first, "officer_presses_1a") == render_flags(second, "officer_presses_1a")
    after = {path.relative_to(ROOT): path.read_bytes() for path in ROOT.rglob("*") if path.is_file()}
    assert before == after


def test_module_has_no_story_specific_words() -> None:
    source = MODULE.read_text(encoding="utf-8")
    for word in ("memory_card", "kristin", "patrol", "laptop", "k_sl_", "t_1a", "continuity"):
        assert word not in source


def test_script_main_returns_zero_with_flags_and_two_for_unknown_anchor(capsys) -> None:
    assert main(["officer_presses_1a", "--rule", "custody"]) == 0
    assert "# Gap flags: officer_presses_1a" in capsys.readouterr().out
    assert main(["missing_anchor"]) == 2
    assert "unknown anchor 'missing_anchor'" in capsys.readouterr().err

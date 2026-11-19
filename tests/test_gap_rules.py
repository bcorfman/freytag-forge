from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from scripts.gap_rules import main
from storygame.story_package.gap_rules import custody_checks, exit_transitions, render_rule_results, run_gap_rules
from storygame.story_package.loader import load_story_package
from tests.story_source.helpers import compiled_story_copy, load_compiled_copy

ROOT = Path("data/stories/continuity-initiative")
MODULE = Path("storygame/story_package/gap_rules.py")


def _copy_package(tmp_path: Path) -> Path:
    return compiled_story_copy(tmp_path)


def _edit_source(root: Path, filename: str, edit) -> None:
    path = root / "source" / filename
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    edit(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")


def _claim(data: dict, claim_id: str) -> dict:
    return next(
        variant
        for reveal in data["reveals"]
        for variant in reveal["variants"].values()
        if variant.get("claim_id") == claim_id
    )


def _remove_asserted_fact(data: object, fact_id: str) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            if key in {"sets", "commits", "establishes", "operations", "costs"}:
                if isinstance(value, dict) and value.get(fact_id) is True:
                    del value[fact_id]
                elif isinstance(value, list):
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


def test_real_data_reports_the_known_results() -> None:
    results = run_gap_rules(ROOT, "officer_presses_1a")

    assert any(
        result.rule == "custody" and result.subject == "k_sl_1a_d_r1" and "memory_card" in result.summary
        for result in results
    )
    # 1A laptop reach: the fixed b_r1 claim no longer produces a co-location gap.
    assert not any(result.rule == "co_location" and result.subject == "k_sl_1a_b_r1" for result in results)
    assert any(
        result.rule == "no_strand" and result.subject == "k_sl_1a_d_r1" and "memory_card" in result.summary
        for result in results
    )

    transition_results = run_gap_rules(ROOT, "t_1a_1b")
    # 1A laptop reach: the transition has no co-location result after b_r1 is laptop-gated.
    assert not any(result.rule == "co_location" for result in transition_results)

    custody_results = run_gap_rules(ROOT, "t_2c_3a", ["custody"])
    assert {result.subject for result in custody_results} == {"k_sl_2c_d_r3", "k_sl_2c_d_r4"}


def test_custody_checks_include_every_pair_with_a_result() -> None:
    package = load_story_package(ROOT)
    results = run_gap_rules(ROOT, "officer_presses_1a", ["custody"])
    checks = custody_checks(package, "officer_presses_1a")

    for result in results:
        matching = [
            check
            for check in checks
            if check.claim_id == result.subject and f"names {check.item_id} " in result.summary
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


def test_untested_custody_rows_do_not_produce_results() -> None:
    assert not run_gap_rules(ROOT, "t_1a_1b", ["custody"])


def test_real_data_citations_point_to_record_definitions() -> None:
    rendered = render_rule_results(run_gap_rules(ROOT, "officer_presses_1a"), "officer_presses_1a")
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
    results = run_gap_rules(ROOT, "officer_presses_1a", ["custody"])
    simulation_lines = [
        evidence for result in results for evidence in result.evidence if evidence.startswith("holder at baseline:")
    ]
    assert simulation_lines
    assert all(re.search(r"\S+\.(?:yaml|md):\d+$", line) is None for line in simulation_lines)


def test_no_strand_reports_already_true_effect() -> None:
    results = run_gap_rules(ROOT, "officer_presses_1a", ["no_strand"])
    assert any(
        "already true, so it cannot fire again" in evidence
        for result in results
        if result.subject == "k_sl_1a_d_r1"
        for evidence in result.evidence
    )


def test_custody_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    _edit_source(
        package_root,
        "scenes/1A.yaml",
        lambda data: _claim(data, "k_sl_1a_d_r1")["entities"].append("memory_card"),
    )
    results = run_gap_rules(package_root, "officer_presses_1a", ["custody"])
    assert any(result.subject == "k_sl_1a_d_r1" and "memory_card" in result.summary for result in results)

    def clean(data: dict) -> None:
        claim = _claim(data, "k_sl_1a_d_r1")
        claim["entities"] = [entity for entity in claim["entities"] if entity != "memory_card"]
        claim["relevance"]["entity_ids"] = [
            entity for entity in claim["relevance"]["entity_ids"] if entity != "memory_card"
        ]

    _edit_source(package_root, "scenes/1A.yaml", clean)
    results = run_gap_rules(package_root, "officer_presses_1a", ["custody"])
    assert not any(result.subject == "k_sl_1a_d_r1" for result in results)


def test_co_location_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    _edit_source(package_root, "scenes/1A.yaml", lambda data: _claim(data, "k_sl_1a_b_r1").update(reach=[]))
    results = run_gap_rules(package_root, "officer_presses_1a", ["co_location"])
    assert any(result.subject == "k_sl_1a_b_r1" and "kristin_laptop" in result.summary for result in results)

    _edit_source(
        package_root,
        "scenes/1A.yaml",
        lambda data: _claim(data, "k_sl_1a_b_r1").update(reach=["kristin_laptop"]),
    )
    results = run_gap_rules(package_root, "officer_presses_1a", ["co_location"])
    assert not any(result.subject == "k_sl_1a_b_r1" for result in results)


def test_no_strand_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    assert any(
        result.subject == "k_sl_1a_d_r1" for result in run_gap_rules(package_root, "officer_presses_1a", ["no_strand"])
    )

    def add_non_item_gated_producer(data: dict) -> None:
        event = next(item for item in data["beats"] if item["id"] == "officer_presses_1a")
        event["sets"]["michelle_lead_actionable"] = True

    _edit_source(package_root, "scenes/1A.yaml", add_non_item_gated_producer)
    results = run_gap_rules(package_root, "officer_presses_1a", ["no_strand"])
    assert not any(result.subject == "k_sl_1a_d_r1" for result in results)


def test_no_producer_seeded_defect_loads_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)
    assert not run_gap_rules(Path(ROOT), "pursuit_1b", ["no_producer"])

    for filename in ("1A.yaml", "1B.yaml", "1C.yaml", "2A.yaml", "2B.yaml", "2C.yaml", "3A.yaml", "3B.yaml", "3C.yaml"):
        _edit_source(
            package_root,
            f"scenes/{filename}",
            lambda data: _remove_asserted_fact(data, "kristin_marked_by_patrol"),
        )

    assert load_compiled_copy(package_root)
    results = run_gap_rules(package_root, "pursuit_1b", ["no_producer"])
    assert any(result.subject == "kristin_marked_by_patrol" for result in results)


def test_real_package_has_no_producer_results_for_every_anchor() -> None:
    package = load_story_package(ROOT)
    anchors = [event.id for event in package.pacing.events]
    anchors += [incident.id for incident in package.incidents]
    anchors += [transition.id for transition in package.pacing.transitions]

    for anchor in anchors:
        results = run_gap_rules(ROOT, anchor, ["no_producer"])
        assert not results, f"{anchor}: no_producer results for {', '.join(result.subject for result in results)}"


def test_unread_effect_is_an_unknown_rule() -> None:
    with pytest.raises(ValueError, match="unknown rule"):
        run_gap_rules(ROOT, "pursuit_1b", ["unread_effect"])


def test_single_reveal_strand_has_no_results_for_every_transition() -> None:
    package = load_story_package(ROOT)

    for transition in package.pacing.transitions:
        assert not run_gap_rules(ROOT, transition.id, ["single_reveal_strand"])


def test_single_reveal_strand_seeded_defect_and_clean_variant(tmp_path: Path) -> None:
    package_root = _copy_package(tmp_path)

    def remove_exit_fact(data: dict) -> None:
        realization = next(
            variant
            for reveal in data["reveals"]
            for variant in reveal["variants"].values()
            if variant.get("realization_id") == "SL-1A-E-R1"
        )
        realization["commits"]["drawer_opened"] = realization["commits"].pop("memory_card_recovered")

    def restore_exit_fact(data: dict) -> None:
        realization = next(
            variant
            for reveal in data["reveals"]
            for variant in reveal["variants"].values()
            if variant.get("realization_id") == "SL-1A-E-R1"
        )
        realization["commits"]["memory_card_recovered"] = realization["commits"].pop("drawer_opened")

    def edit_knowledge(data: dict, fact_id: str) -> None:
        claim = _claim(data, "k_sl_1a_b_r0")
        old_fact = "memory_card_recovered" if fact_id == "drawer_opened" else "drawer_opened"
        claim["commits_subset"] = {fact_id: claim["commits"].get(old_fact, True)}

    def remove_exit_and_edit_claim(data: dict) -> None:
        remove_exit_fact(data)
        edit_knowledge(data, "drawer_opened")

    _edit_source(package_root, "scenes/1A.yaml", remove_exit_and_edit_claim)
    results = run_gap_rules(package_root, "t_1a_1b", ["single_reveal_strand"])
    assert any(
        result.subject == "SL-1A-E/SL-1A-E-R1" and "memory_card_recovered" in result.summary for result in results
    )

    _edit_source(package_root, "scenes/1A.yaml", restore_exit_fact)
    _edit_source(package_root, "scenes/1A.yaml", lambda data: edit_knowledge(data, "memory_card_recovered"))
    results = run_gap_rules(package_root, "t_1a_1b", ["single_reveal_strand"])
    assert not any(result.subject == "SL-1A-E/SL-1A-E-R1" for result in results)


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
        next(item for item in data["beats"] if item["id"] == "officer_presses_1a")["id"] = "t_1b_1c"

    _edit_source(package_root, "scenes/1A.yaml", duplicate)
    with pytest.raises(ValueError, match=r"ambiguous anchor 't_1b_1c'.*pacing event.*transition"):
        run_gap_rules(package_root, "t_1b_1c")


def test_output_and_inputs_are_deterministic_and_read_only() -> None:
    source_root = ROOT / "source"
    before = {path.relative_to(source_root): path.read_bytes() for path in source_root.rglob("*") if path.is_file()}
    first = run_gap_rules(ROOT, "officer_presses_1a")
    second = run_gap_rules(ROOT, "officer_presses_1a")
    assert first == second
    assert render_rule_results(first, "officer_presses_1a") == render_rule_results(second, "officer_presses_1a")
    after = {path.relative_to(source_root): path.read_bytes() for path in source_root.rglob("*") if path.is_file()}
    assert before == after


def test_module_has_no_story_specific_words() -> None:
    source = MODULE.read_text(encoding="utf-8")
    for word in ("memory_card", "kristin", "patrol", "laptop", "k_sl_", "t_1a", "continuity"):
        assert word not in source


def test_script_main_returns_zero_with_results_and_two_for_unknown_anchor(capsys) -> None:
    assert main(["officer_presses_1a", "--rule", "custody"]) == 0
    assert "# Gap rule results: officer_presses_1a" in capsys.readouterr().out
    assert main(["missing_anchor"]) == 2
    assert "unknown anchor 'missing_anchor'" in capsys.readouterr().err

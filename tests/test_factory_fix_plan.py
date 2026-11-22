from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.stations import fix_plan
from storygame.story_package.loader import load_story_package
from storygame.story_source.lookup import story_text

PACKAGE = load_story_package(DEFAULT_ROOT)
TICKET = {
    "parent": "ticket-parent",
    "scene": "1A",
    "class": "story_data",
    "failing_turns": [
        {
            "key": "1A-r1-t6",
            "scene": "1A",
            "player_input": "I search the desk.",
            "narration": "The search stalls.",
            "candidates_offered": ["k_sl_1a_b_r1", "k_sl_1a_b_r2"],
            "matched_candidate": None,
            "outcome": {"committed": False},
        },
        {
            "key": "1A-r1-t7",
            "scene": "1A",
            "player_input": "I look for the next lead.",
            "narration": "Nothing points to the next move.",
            "candidates_offered": ["k_sl_1a_b_r2"],
            "matched_candidate": None,
            "outcome": {"committed": False},
        },
    ],
    "rules": {},
}


def beat_plan() -> dict:
    return {
        "version": 1,
        "ticket_id": "ticket-parent-1a-story-data",
        "scene": "1A",
        "kind": "add_pacing_beat",
        "reason": "The failing turns need a concrete next move before the handoff.",
        "evidence_keys": ["1A-r1-t6", "1A-r1-t7"],
        "beat": {
            "id": "truck_laptop_1a",
            "at_turn": 10,
            "text": "Check the truck and laptop before the patrol returns to the house.",
            "verbatim": True,
            "trailing": True,
            "when": {"memory_card_recovered": True, "michelle_lead_actionable": False},
            "sets": {},
        },
    }


def text_plan() -> dict:
    return {
        "version": 1,
        "ticket_id": "ticket-parent-1a-story-data",
        "scene": "1A",
        "kind": "set_text",
        "reason": "The reveal handoff should make the next move explicit to the player.",
        "evidence_keys": ["1A-r1-t6"],
        "set_text": {
            "address": "claim:k_sl_1a_b_r1.text",
            "text": "The handoff points clearly toward the waiting vehicle and the nearby computer.",
        },
    }


def test_valid_plans_pass() -> None:
    assert fix_plan.lint_plan(beat_plan(), TICKET, PACKAGE) == []
    assert fix_plan.lint_plan(text_plan(), TICKET, PACKAGE) == []


@pytest.mark.parametrize(
    ("mutation", "rule"),
    [
        (lambda plan: plan.update({"extra": True}), "plan.shape"),
        (lambda plan: plan.update({"kind": "unsupported"}), "plan.kind"),
        (lambda plan: plan.update({"scene": "2A"}), "plan.scene"),
        (lambda plan: plan.update({"evidence_keys": ["missing"]}), "plan.evidence"),
        (lambda plan: plan.update({"reason": "  "}), "plan.reason"),
        (lambda plan: plan["beat"].update({"id": "Not a safe id"}), "plan.beat_id"),
        (lambda plan: plan["beat"].update({"id": "reyes_rams_drawer_1a"}), "plan.beat_id"),
        (lambda plan: plan["beat"].update({"at_turn": 0}), "plan.beat_turn"),
        (lambda plan: plan["beat"].update({"at_turn": 15}), "plan.beat_turn"),
        (lambda plan: plan["beat"]["when"].update({"unknown_fact": True}), "plan.facts"),
        (lambda plan: plan["beat"].update({"sets": {"memory_card_recovered": True}}), "plan.exit_trigger"),
    ],
)
def test_beat_rule_mutations(mutation, rule: str) -> None:
    plan = beat_plan()
    mutation(plan)
    assert any(problem.startswith(rule) for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE))


@pytest.mark.parametrize(
    "text",
    [
        "",
        "too short",
        "x" * 601,
        "This text contains {a brace} and should fail.",
        "TODO: this handoff still needs authoring.",
        "The memory_card_recovered clue is not allowed in authored prose.",
        "The k_sl_1a_b_r1 claim id is not allowed in authored prose.",
        "The SL-1A-B storylet id is not allowed in authored prose.",
    ],
)
def test_beat_text_rules(text: str) -> None:
    plan = beat_plan()
    plan["beat"]["text"] = text
    assert any(problem.startswith("plan.text") for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE))


def test_set_text_rules() -> None:
    invalid_address = text_plan()
    invalid_address["set_text"]["address"] = "claim:k_sl_1a_b_r1.says"
    assert any(problem.startswith("plan.address") for problem in fix_plan.lint_plan(invalid_address, TICKET, PACKAGE))

    unchanged = text_plan()
    unchanged["set_text"]["text"] = story_text(unchanged["set_text"]["address"], package=PACKAGE)
    assert any(problem.startswith("plan.unchanged") for problem in fix_plan.lint_plan(unchanged, TICKET, PACKAGE))


def test_evidence_is_deterministic_bounded_and_skips_unknown() -> None:
    ticket = copy.deepcopy(TICKET)
    ticket["failing_turns"][0]["candidates_offered"].append("unknown_candidate")
    first = fix_plan.build_evidence(ticket, PACKAGE)
    second = fix_plan.build_evidence(ticket, PACKAGE)
    assert first == second
    json.dumps(first)
    assert len(json.dumps(first)) < 12_000
    assert "unknown_candidate" not in first["candidates"]
    candidate = first["candidates"]["k_sl_1a_b_r1"]
    assert candidate["earn_when"]
    assert isinstance(candidate["requires"], list)
    assert {item["key"] for item in first["failing_turns"]} == {"1A-r1-t6", "1A-r1-t7"}


def test_cli_exit_codes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    ticket_path = tmp_path / "ticket.json"
    plan_path = tmp_path / "plan.json"
    ticket_path.write_text(json.dumps(TICKET), encoding="utf-8")
    plan_path.write_text(json.dumps(beat_plan()), encoding="utf-8")

    assert fix_plan.main(["lint", str(plan_path), "--ticket", str(ticket_path)]) == 0
    plan_path.write_text(json.dumps({"kind": "bad"}), encoding="utf-8")
    assert fix_plan.main(["lint", str(plan_path), "--ticket", str(ticket_path)]) == 1
    assert "plan.shape" in capsys.readouterr().out
    assert fix_plan.main(["evidence", str(ticket_path)]) == 0
    assert json.loads(capsys.readouterr().out)
    ticket_path.write_text("not json", encoding="utf-8")
    assert fix_plan.main(["evidence", str(ticket_path)]) == 2


def test_module_has_no_story_specific_literals() -> None:
    source = inspect.getsource(fix_plan).lower()
    for literal in ("michelle", "kristin", "memory_card", "1a"):
        assert literal not in source

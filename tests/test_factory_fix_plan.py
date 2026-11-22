from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path

import pytest

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.stations import fix_plan
from storygame.story_package.dependencies import producers
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
        "reason": "Precedent: fact-gated pacing beat; the failing turns need a concrete next move before the handoff.",
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
        "reason": (
            "Precedent: concise handoff wording; the reveal handoff should make the next move explicit to the player."
        ),
        "evidence_keys": ["1A-r1-t6"],
        "set_text": {
            "address": "claim:k_sl_1a_b_r1.text",
            "text": "The handoff points clearly toward the waiting vehicle and the nearby computer.",
        },
    }


def _drawer_gap_plan() -> dict:
    plan = beat_plan()
    plan["beat"].update(
        {
            "id": "drawer_gap_recalled_1a",
            "at_turn": 12,
            "when": {"memory_card_recovered": False, "patrol_in_house": False},
            "sets": {"drawer_gap_pointed_out": True},
            "text": (
                "The street is quiet again. Kristin's eyes go back to the workstation drawer, riding high in its "
                "frame, "
                "with that thin gap under its lower edge. The officer was too interested in it. Michelle may have left "
                "something there."
            ),
        }
    )
    return plan


def test_valid_plans_pass() -> None:
    assert fix_plan.lint_plan(beat_plan(), TICKET, PACKAGE) == []
    assert fix_plan.lint_plan(text_plan(), TICKET, PACKAGE) == []


def test_rejects_pacing_beat_with_redundant_effect() -> None:
    problems = fix_plan.lint_plan(_drawer_gap_plan(), TICKET, PACKAGE)

    assert problems == [
        "plan.redundant_effect beat sets drawer_gap_pointed_out, which pacing event reyes_rams_drawer_1a (turn 8) "
        "already sets; guard when with drawer_gap_pointed_out: False or set a fact nothing else sets",
        "plan.shared_effect beat sets drawer_gap_pointed_out, which pacing event reyes_rams_drawer_1a (turn 8) "
        "also sets; set a fact no other pacing event sets",
    ]


def test_redundant_effect_is_allowed_with_opposite_guard() -> None:
    plan = _drawer_gap_plan()
    plan["beat"]["when"]["drawer_gap_pointed_out"] = False

    assert not any(problem.startswith("plan.redundant_effect") for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE))


def test_rejects_beat_that_sets_a_fact_any_pacing_event_sets() -> None:
    plans = []
    plan = _drawer_gap_plan()
    plan["beat"].update(
        {
            "id": "drawer_gap_noticed_1a",
            "at_turn": 5,
            "when": {"drawer_gap_pointed_out": False, "memory_card_recovered": False},
        }
    )
    plans.append(plan)

    plan = _drawer_gap_plan()
    plan["beat"].update(
        {
            "id": "drawer_sits_crooked_1a",
            "at_turn": 11,
            "when": {
                "drawer_gap_pointed_out": False,
                "memory_card_recovered": False,
                "patrol_in_house": False,
            },
        }
    )
    plans.append(plan)

    for plan in plans:
        problems = fix_plan.lint_plan(plan, TICKET, PACKAGE)

        assert any(
            problem.startswith("plan.shared_effect") and "reyes_rams_drawer_1a" in problem and "(turn 8)" in problem
            for problem in problems
        )


def test_shared_effect_is_refused_at_and_after_the_producer_turn_too() -> None:
    plan = _drawer_gap_plan()
    plan["beat"].update(
        {
            "id": "drawer_gap_noticed_1a",
            "when": {"drawer_gap_pointed_out": False, "memory_card_recovered": False},
        }
    )
    for at_turn in (8, 9):
        plan["beat"]["at_turn"] = at_turn

        assert any(
            problem.startswith("plan.shared_effect") and "reyes_rams_drawer_1a" in problem and "(turn 8)" in problem
            for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE)
        )


def test_shared_effect_rule_ignores_a_fact_no_pacing_event_sets() -> None:
    pacing_fact_ids = {
        fix_plan._value(effect, "fact_id")
        for event in fix_plan._value(getattr(PACKAGE, "pacing", None), "events", ()) or ()
        for effect in fix_plan._value(event, "effects", ()) or ()
    }
    fact_id = next(fact for fact in sorted(fix_plan._declared_facts(PACKAGE)) if fact not in pacing_fact_ids)
    plan = beat_plan()
    plan["beat"]["sets"] = {fact_id: True}

    for at_turn in (5, 11):
        plan["beat"]["at_turn"] = at_turn

        assert not any(
            problem.startswith("plan.shared_effect") for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE)
        )


def test_declared_fact_without_matching_producer_is_allowed() -> None:
    fact_id = next(
        fact
        for fact in sorted(fix_plan._declared_facts(PACKAGE))
        if not producers(PACKAGE, fact, True) and not producers(PACKAGE, fact, False)
    )
    plan = beat_plan()
    plan["beat"]["sets"] = {fact_id: True}

    assert not any(problem.startswith("plan.redundant_effect") for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE))


def test_opposite_value_of_existing_producer_is_allowed() -> None:
    fact_id = next(
        fact
        for fact in sorted(fix_plan._declared_facts(PACKAGE))
        if producers(PACKAGE, fact, True) and not producers(PACKAGE, fact, False)
    )
    plan = beat_plan()
    plan["beat"]["sets"] = {fact_id: False}

    assert not any(problem.startswith("plan.redundant_effect") for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE))


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
    bounded_without_curated_text = {
        key: value for key, value in first.items() if key not in {"precedents", "fun_lessons"}
    }
    assert len(json.dumps(bounded_without_curated_text)) < 12_000
    assert "unknown_candidate" not in first["candidates"]
    candidate = first["candidates"]["k_sl_1a_b_r1"]
    assert candidate["earn_when"]
    assert isinstance(candidate["requires"], list)
    assert {item["key"] for item in first["failing_turns"]} == {"1A-r1-t6", "1A-r1-t7"}


def test_evidence_ignores_lesson_rendering_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_render_lessons(*args: object, **kwargs: object) -> str:
        raise RuntimeError("bad lesson store")

    monkeypatch.setattr(fix_plan, "render_lessons", broken_render_lessons)

    assert fix_plan.build_evidence(copy.deepcopy(TICKET), PACKAGE)["fun_lessons"] is None


def test_evidence_carries_the_diagnosis() -> None:
    ticket = copy.deepcopy(TICKET)
    ticket["diagnosis"] = {
        "counts": {"claim_not_offered": 2},
        "rows": [
            {"key": "1A-r1-t6", "cause": "claim_not_offered", "why": "x" * 200, "signals": ["claim"]},
            {"key": "1A-r1-t7", "cause": "claim_not_offered", "why": "short"},
        ],
    }

    diagnosis = fix_plan.build_evidence(ticket, PACKAGE)["diagnosis"]

    assert diagnosis["counts"] == {"claim_not_offered": 2}
    assert diagnosis["rows"] == [
        {"key": "1A-r1-t6", "cause": "claim_not_offered", "why": "x" * 160},
        {"key": "1A-r1-t7", "cause": "claim_not_offered", "why": "short"},
    ]

    ticket["diagnosis"]["rows"] = [
        {"key": f"turn-{index}", "cause": "claim_not_offered", "why": "y" * 160} for index in range(200)
    ]
    bounded = fix_plan.build_evidence(ticket, PACKAGE)["diagnosis"]
    assert len(json.dumps(bounded, ensure_ascii=False, separators=(",", ":"))) <= 6000
    assert bounded["counts"] == {"claim_not_offered": 2}
    assert bounded["rows"]
    assert len(bounded["rows"]) < 200
    assert all(row["why"] == "" for row in bounded["rows"])


def test_evidence_diagnosis_is_null_without_it() -> None:
    assert fix_plan.build_evidence(TICKET, PACKAGE)["diagnosis"] is None
    for malformed in (
        {"counts": [], "rows": []},
        {"counts": {}, "rows": [{"key": "turn-1", "cause": "unclear"}]},
    ):
        ticket = copy.deepcopy(TICKET)
        ticket["diagnosis"] = malformed
        assert fix_plan.build_evidence(ticket, PACKAGE)["diagnosis"] is None


def test_evidence_carries_the_precedents_text(tmp_path: Path) -> None:
    default_path = DEFAULT_ROOT.parents[2] / "factory" / "precedents" / "stuck_turns.md"
    default_text = default_path.read_text(encoding="utf-8")
    evidence = fix_plan.build_evidence(TICKET, PACKAGE)
    assert evidence["precedents"] == default_text[:20_000]

    custom_text = "precedent marker\n" + ("x" * 20_100)
    custom_path = tmp_path / "precedents.md"
    custom_path.write_text(custom_text, encoding="utf-8")
    ticket = copy.deepcopy(TICKET)
    ticket["precedents_path"] = str(custom_path)

    assert fix_plan.build_evidence(ticket, PACKAGE)["precedents"] == custom_text[:20_000]


def test_evidence_precedents_is_null_when_the_file_is_missing(tmp_path: Path) -> None:
    ticket = copy.deepcopy(TICKET)
    ticket["precedents_path"] = str(tmp_path / "missing.md")

    assert fix_plan.build_evidence(ticket, PACKAGE)["precedents"] is None


def test_lint_requires_a_precedent_prefix_in_the_reason() -> None:
    plan = beat_plan()
    plan["reason"] = "A fix without its precedent."
    message = (
        "plan.precedent reason must begin with Precedent: and name the proven technique followed, "
        "or Precedent: none with what was checked"
    )

    assert fix_plan.lint_plan(plan, TICKET, PACKAGE) == [message]

    plan["reason"] = "Precedent: none, nothing covers a fixed exit"
    assert fix_plan.lint_plan(plan, TICKET, PACKAGE) == []


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

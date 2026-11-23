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
    fact_id = next(
        fact
        for fact in sorted(fix_plan._declared_facts(PACKAGE))
        if not producers(PACKAGE, fact, True) and not producers(PACKAGE, fact, False)
    )
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
            "test": "fixed_replay",
            "when": {"memory_card_recovered": True, "michelle_lead_actionable": False},
            "sets": {fact_id: True},
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


def test_rejects_pacing_beat_with_empty_effects() -> None:
    plan = beat_plan()
    plan["beat"]["sets"] = {}

    problems = fix_plan.lint_plan(plan, TICKET, PACKAGE)

    assert len(problems) == 1
    assert problems[0].startswith("plan.empty_effect")


def test_accepts_pacing_beat_with_one_unshared_effect() -> None:
    problems = fix_plan.lint_plan(beat_plan(), TICKET, PACKAGE)

    assert not any(problem.startswith("plan.empty_effect") for problem in problems)
    assert not any(problem.startswith(("plan.redundant_effect", "plan.shared_effect")) for problem in problems)


def test_reports_empty_effect_with_other_beat_problem() -> None:
    plan = beat_plan()
    plan["beat"].update({"id": "Not a safe id", "sets": {}})

    problems = fix_plan.lint_plan(plan, TICKET, PACKAGE)

    assert any(problem.startswith("plan.empty_effect") for problem in problems)
    assert any(problem.startswith("plan.beat_id") for problem in problems)


def test_rejects_pacing_beat_with_redundant_effect() -> None:
    problems = fix_plan.lint_plan(_drawer_gap_plan(), TICKET, PACKAGE)

    assert problems == [
        "plan.redundant_effect beat sets drawer_gap_pointed_out, which pacing event reyes_rams_drawer_1a (turn 8) "
        "already sets; guard when with drawer_gap_pointed_out: False or set a fact nothing else sets",
        "plan.shared_effect beat sets drawer_gap_pointed_out, which pacing event reyes_rams_drawer_1a (turn 8) "
        "also sets; set a fact no other pacing event sets",
        "plan.skipped_preconditions beat sets drawer_gap_pointed_out, but claim k_sl_1a_f_r3 from SL-1A-F-R3 "
        "requires drawer_opened=True; pin those predicates in when before setting the fact",
        "plan.skipped_preconditions beat sets drawer_gap_pointed_out, but pacing event reyes_rams_drawer_1a (turn 8) "
        "requires patrol_in_house=True, drawer_gap_pointed_out=False; pin those predicates in when before setting "
        "the fact",
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


def test_unsupported_plan_requires_reroute_shape_and_prefix() -> None:
    plan = {
        "version": 1,
        "ticket_id": "ticket-parent-1a-story-data",
        "scene": "1A",
        "kind": "unsupported",
        "reason": "Reroute: the replay needs an adaptive player to test the next choice.",
        "evidence_keys": ["1A-r1-t6"],
        "reroute": "adaptive_probe",
    }

    assert fix_plan.lint_plan(plan, TICKET, PACKAGE) == []

    wrong_reroute = copy.deepcopy(plan)
    wrong_reroute["reroute"] = "wiring"
    assert any(problem.startswith("plan.shape") for problem in fix_plan.lint_plan(wrong_reroute, TICKET, PACKAGE))

    bad_prefix = copy.deepcopy(plan)
    bad_prefix["reason"] = "Precedent: this cannot be represented by the menu."
    assert any(problem.startswith("plan.reroute_reason") for problem in fix_plan.lint_plan(bad_prefix, TICKET, PACKAGE))


def test_skipped_preconditions_reject_a_meaning_fact_but_accept_matching_guard() -> None:
    plan = beat_plan()
    plan["beat"].update(
        {
            "id": "card_challenged_hint_1a",
            "sets": {"card_challenged": True},
            "when": {},
        }
    )
    problems = fix_plan.lint_plan(plan, TICKET, PACKAGE)
    assert any(
        problem.startswith("plan.skipped_preconditions") and "k_sl_1a_b_r0w" in problem and "patrol_in_house" in problem
        for problem in problems
    )

    plan["beat"]["when"] = {"patrol_in_house": True, "memory_card_recovered": False}
    assert not any(
        problem.startswith("plan.skipped_preconditions") for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE)
    )


def test_skipped_preconditions_ignore_a_fact_with_no_writers() -> None:
    fact_id = next(
        fact
        for fact in sorted(fix_plan._declared_facts(PACKAGE))
        if not producers(PACKAGE, fact, True) and not producers(PACKAGE, fact, False)
    )
    plan = beat_plan()
    plan["beat"]["sets"] = {fact_id: True}
    assert not any(
        problem.startswith("plan.skipped_preconditions") for problem in fix_plan.lint_plan(plan, TICKET, PACKAGE)
    )


def test_contradicted_cause_uses_only_cited_diagnosis_rows() -> None:
    ticket = copy.deepcopy(TICKET)
    ticket["diagnosis"] = {
        "counts": {"claim_not_offered": 1},
        "rows": [{"key": "1A-r1-t6", "cause": "claim_not_offered", "why": "not offered"}],
    }
    plan = beat_plan()
    plan["evidence_keys"] = ["1A-r1-t6"]
    plan["reason"] = "Precedent: no_authored_outcome is the cause and the cue keeps the scene moving."
    assert any(problem.startswith("plan.contradicted_cause") for problem in fix_plan.lint_plan(plan, ticket, PACKAGE))

    plan["reason"] = "Precedent: claim_not_offered is the cause and the cue keeps the scene moving."
    assert not any(
        problem.startswith("plan.contradicted_cause") for problem in fix_plan.lint_plan(plan, ticket, PACKAGE)
    )

    ticket.pop("diagnosis")
    plan["reason"] = "Precedent: no_authored_outcome is the cause and the cue keeps the scene moving."
    assert not any(
        problem.startswith("plan.contradicted_cause") for problem in fix_plan.lint_plan(plan, ticket, PACKAGE)
    )


def test_add_pacing_beat_test_field_is_linted_but_legacy_shape_is_readable() -> None:
    missing = beat_plan()
    del missing["beat"]["test"]
    assert any(problem.startswith("plan.test") for problem in fix_plan.lint_plan(missing, TICKET, PACKAGE))

    invalid = beat_plan()
    invalid["beat"]["test"] = "live_model"
    assert any(problem.startswith("plan.test") for problem in fix_plan.lint_plan(invalid, TICKET, PACKAGE))

    legacy = copy.deepcopy(TICKET)
    legacy["plan"] = missing
    assert not any(problem.startswith("plan.test") for problem in fix_plan.lint_plan(missing, legacy, PACKAGE))


@pytest.mark.parametrize(
    ("mutation", "rule"),
    [
        (lambda plan: plan.update({"extra": True}), "plan.shape"),
        (lambda plan: plan.update({"kind": "unsupported"}), "plan.shape"),
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
    assert len(json.dumps(bounded_without_curated_text)) <= fix_plan.EVIDENCE_LIMIT_CHARS
    assert "unknown_candidate" not in first["candidates"]
    candidate = first["candidates"]["k_sl_1a_b_r1"]
    assert candidate["earn_when"]
    assert isinstance(candidate["requires"], list)
    assert {item["key"] for item in first["failing_turns"]} == {"1A-r1-t6", "1A-r1-t7"}


def test_bound_evidence_keeps_a_turn_and_reports_all_cuts() -> None:
    packet = {
        "failing_turns": [
            {
                "key": f"turn-{index}",
                "player_input": "I search for the next lead.",
                "narration": "n" * 900,
                "previous_narration": "p" * 900,
                "rejected_code": "c" * 600,
                "rejected_message": "m" * 600,
            }
            for index in range(25)
        ],
        "candidates": {f"candidate-{index:02d}": {"text": "c" * 500} for index in range(12)},
        "fact_readers": {},
        "beats": [],
        "exits": [],
    }

    bounded = fix_plan._bound_evidence(packet)

    assert bounded["failing_turns"]
    assert len(json.dumps(bounded, ensure_ascii=False, separators=(",", ":"))) <= fix_plan.EVIDENCE_LIMIT_CHARS
    assert bounded["truncated"]["candidates"] == {"kept": 0, "of": 12}
    assert bounded["truncated"]["text_shortened_to"] == 150
    if "failing_turns" in bounded["truncated"]:
        assert bounded["truncated"]["failing_turns"] == {"kept": len(bounded["failing_turns"]), "of": 25}


def test_bound_evidence_keeps_diagnosis_turns_longest() -> None:
    packet = {
        "failing_turns": [
            {"key": key, "narration": "n" * 600, "previous_narration": "p" * 600}
            for key in ("keep", "drop-1", "drop-2")
        ],
        "candidates": {},
        "fact_readers": {},
        "beats": [],
        "exits": [],
    }

    bounded = fix_plan._bound_evidence(packet, limit=500, protected_turn_keys={"keep"})

    assert "keep" in {turn["key"] for turn in bounded["failing_turns"]}
    assert len(bounded["failing_turns"]) == 1


def test_bound_evidence_cuts_candidates_before_failing_turns() -> None:
    packet = {
        "failing_turns": [{"key": "keep", "narration": "n" * 80}, {"key": "also-keep", "narration": "n" * 80}],
        "candidates": {f"candidate-{index:02d}": {"text": "c" * 500} for index in range(8)},
        "fact_readers": {},
        "beats": [],
        "exits": [],
    }

    bounded = fix_plan._bound_evidence(packet, limit=500)

    assert [turn["key"] for turn in bounded["failing_turns"]] == ["keep", "also-keep"]
    assert bounded["truncated"]["candidates"] == {"kept": 0, "of": 8}
    assert "failing_turns" not in bounded["truncated"]


def test_bound_evidence_protects_offered_last_sorted_candidate() -> None:
    candidate_ids = [
        "k_sl_1a_a_r1",
        "k_sl_1a_b_r1",
        "k_sl_1a_c_r1",
        "k_sl_1a_k_r1",
    ]
    ticket = {
        "scene": "1A",
        "diagnosis": None,
        "failing_turns": [{"key": "turn-1", "candidates_offered": ["k_sl_1a_k_r1"]}],
    }
    packet = {
        "failing_turns": ticket["failing_turns"],
        "candidates": {candidate_id: {"text": "candidate"} for candidate_id in candidate_ids},
        "fact_readers": {},
        "beats": [],
        "exits": [],
    }

    bounded = fix_plan._bound_evidence(packet, limit=100, protected_candidates={"k_sl_1a_k_r1"})

    assert "k_sl_1a_k_r1" in bounded["candidates"]
    assert bounded["truncated"]["candidates"]["kept"] < len(candidate_ids)


def test_bound_evidence_leaves_small_packet_unchanged() -> None:
    packet = {"failing_turns": [], "candidates": {}, "fact_readers": {}, "beats": [], "exits": []}
    original = copy.deepcopy(packet)

    assert fix_plan._bound_evidence(packet) == original
    assert "truncated" not in packet


def test_bound_evidence_handles_zero_failing_turns_when_over_limit() -> None:
    packet = {
        "failing_turns": [],
        "candidates": {f"candidate-{index}": {"text": "c" * 500} for index in range(8)},
        "fact_readers": {},
        "beats": [],
        "exits": [],
    }

    bounded = fix_plan._bound_evidence(packet, limit=100)

    assert bounded["failing_turns"] == []
    assert bounded["truncated"]["candidates"] == {"kept": 0, "of": 8}


def test_bound_evidence_keeps_structured_pacing_evidence_at_default_limit() -> None:
    packet = {
        "failing_turns": [
            {
                "key": f"turn-{index}",
                "narration": "n" * 600,
                "previous_narration": "p" * 600,
            }
            for index in range(25)
        ],
        "candidates": {f"candidate-{index:02d}": {"text": "c" * 500} for index in range(10)},
        "diagnosis": "d" * 6_000,
        "fact_readers": {"facts": "r" * 2_300},
        "beats": [{"id": f"beat-{index}", "at_turn": index} for index in range(8)],
        "exits": [{"id": "exit-1", "to": "next"}],
    }

    bounded = fix_plan._bound_evidence(packet)

    assert len(json.dumps(bounded, ensure_ascii=False, separators=(",", ":"))) <= fix_plan.EVIDENCE_LIMIT_CHARS
    assert bounded["truncated"]
    assert len(bounded["failing_turns"]) >= 10
    assert len(bounded["beats"]) == 8
    assert len(bounded["exits"]) == 1


def test_bound_evidence_cuts_pacing_evidence_after_150_character_text() -> None:
    packet = {
        "failing_turns": [
            {
                "key": "turn-1",
                "narration": "n" * 600,
                "previous_narration": "p" * 600,
            }
        ],
        "candidates": {},
        "fact_readers": {},
        "beats": [{"id": f"beat-{index}", "detail": "b" * 200} for index in range(3)],
        "exits": [{"id": f"exit-{index}", "detail": "e" * 200} for index in range(2)],
    }

    after_150 = copy.deepcopy(packet)
    after_150["failing_turns"][0]["narration"] = "n" * 150
    after_150["failing_turns"][0]["previous_narration"] = "p" * 150
    after_150["beats"] = []
    after_150["exits"] = []
    after_150["truncated"] = {
        "text_shortened_to": 150,
        "beats": {"kept": 0, "of": 3},
        "exits": {"kept": 0, "of": 2},
    }
    limit = len(json.dumps(after_150, ensure_ascii=False, separators=(",", ":")))

    bounded = fix_plan._bound_evidence(packet, limit=limit)

    assert bounded["truncated"]["text_shortened_to"] == 150
    assert bounded["truncated"]["beats"] == {"kept": 0, "of": 3}
    assert bounded["truncated"]["exits"] == {"kept": 0, "of": 2}
    assert len(json.dumps(bounded, ensure_ascii=False, separators=(",", ":"))) <= limit
    assert len(bounded["failing_turns"]) == 1
    assert all(
        len(turn[field]) == 150 for turn in bounded["failing_turns"] for field in ("narration", "previous_narration")
    )


def test_build_evidence_protects_diagnosis_row_turns() -> None:
    ticket = copy.deepcopy(TICKET)
    ticket["failing_turns"] = [
        {
            "key": key,
            "player_input": "p" * 4_000,
            "narration": "n" * 600,
            "candidates_offered": [],
            "matched_candidate": None,
            "outcome": {"committed": False},
        }
        for key in ("diagnosed", "other-1", "other-2", "other-3")
    ]
    ticket["diagnosis"] = {
        "counts": {"claim_not_offered": 1},
        "rows": [{"key": "diagnosed", "cause": "claim_not_offered", "why": "The turn is described."}],
    }

    evidence = fix_plan.build_evidence(ticket, PACKAGE)

    assert "diagnosed" in {turn["key"] for turn in evidence["failing_turns"]}
    assert len(evidence["failing_turns"]) == 4


def test_evidence_ignores_lesson_rendering_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    def broken_render_lessons(*args: object, **kwargs: object) -> str:
        raise RuntimeError("bad lesson store")

    monkeypatch.setattr(fix_plan, "render_lessons", broken_render_lessons)

    assert fix_plan.build_evidence(copy.deepcopy(TICKET), PACKAGE)["fun_lessons"] is None


def test_evidence_carries_the_diagnosis() -> None:
    ticket = copy.deepcopy(TICKET)
    ticket["failing_turns"][0]["previous_narration"] = "Earlier narration" * 100
    ticket["failing_turns"][0]["rejected_code"] = "narration_known_term_leak"
    ticket["failing_turns"][0]["rejected_message"] = "The protected phrase was repeated."
    ticket["failing_turns"][1]["rejected_code"] = None
    ticket["diagnosis"] = {
        "counts": {"claim_not_offered": 2},
        "rows": [
            {
                "key": "1A-r1-t6",
                "cause": "claim_not_offered",
                "why": "x" * 200,
                "signals": {"claim_ids": ["k_sl_1a_b_r0"], "fact_ids": ["memory_card_recovered"]},
            },
            {"key": "1A-r1-t7", "cause": "claim_not_offered", "why": "short"},
        ],
    }

    diagnosis = fix_plan.build_evidence(ticket, PACKAGE)["diagnosis"]

    assert diagnosis["counts"] == {"claim_not_offered": 2}
    assert diagnosis["rows"] == [
        {
            "key": "1A-r1-t6",
            "cause": "claim_not_offered",
            "why": "x" * 160,
            "signals": {"claim_ids": ["k_sl_1a_b_r0"], "fact_ids": ["memory_card_recovered"]},
        },
        {"key": "1A-r1-t7", "cause": "claim_not_offered", "why": "short"},
    ]
    assert "k_sl_1a_b_r0" in fix_plan.build_evidence(ticket, PACKAGE)["candidates"]
    first_turn, second_turn = fix_plan.build_evidence(ticket, PACKAGE)["failing_turns"]
    assert first_turn["previous_narration"] == ("Earlier narration" * 100)[:600]
    assert first_turn["rejected_code"] == "narration_known_term_leak"
    assert first_turn["rejected_message"] == "The protected phrase was repeated."
    assert "rejected_code" not in second_turn
    assert len(json.dumps(fix_plan.build_evidence(ticket, PACKAGE)["fact_readers"])) <= 2500

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

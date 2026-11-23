from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from factory.checks.gap_delta import DEFAULT_ROOT
from factory.stations import fix_plan
from factory.stations.planner import PLANNER_BRIEF
from factory.stations.wiring import claim_evidence_change_error, wiring_spec
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = load_story_package(DEFAULT_ROOT)
PACKETS = json.loads((ROOT / "tests/fixtures/factory/stuck_packets_1a.json").read_text(encoding="utf-8"))
TARGET = "k_sl_1a_k_r1"


def ticket(*, packets: list[dict] | None = None) -> dict:
    return {"scene": "1A", "failing_turns": copy.deepcopy(packets if packets is not None else PACKETS)}


def plan(*, claim_id: str = TARGET, group: int = 0, phrase: str = "my truck") -> dict:
    return {
        "version": 1,
        "ticket_id": "claim-edit-test",
        "scene": "1A",
        "kind": "edit_claim_evidence",
        "reason": "Precedent: exact matcher wording; the offered claim already covers the typed action.",
        "evidence_keys": ["smoke18c-1A-r2-t11"],
        "claim_edit": {"claim_id": claim_id, "group": group, "phrase": phrase},
    }


def test_valid_claim_edit_passes_and_shape_is_strict() -> None:
    assert fix_plan.lint_plan(plan(), ticket(), PACKAGE) == []

    malformed = plan()
    malformed["claim_edit"]["extra"] = "no"
    assert fix_plan._shape_problems(malformed) == ["plan.shape claim_edit fields are invalid"]

    malformed = plan()
    malformed["claim_edit"]["group"] = True
    assert fix_plan._shape_problems(malformed) == ["plan.shape claim_edit group must be an integer"]


def test_planner_brief_describes_the_narrow_claim_edit() -> None:
    assert '"edit_claim_evidence"' in PLANNER_BRIEF
    assert "typed words clearly mean what an existing offered claim" in PLANNER_BRIEF
    assert "already covers" in PLANNER_BRIEF
    assert "never add a bare common word" in PLANNER_BRIEF


@pytest.mark.parametrize(
    ("mutation", "rule"),
    [
        (lambda value: value["claim_edit"].update(claim_id="not_a_claim"), "plan.claim"),
        (lambda value: value["claim_edit"].update(group=9), "plan.group"),
        (lambda value: value["claim_edit"].update(phrase="My truck"), "plan.phrase"),
        (lambda value: value["claim_edit"].update(phrase="the and"), "plan.phrase"),
        (lambda value: value["claim_edit"].update(phrase="drive"), "plan.phrase"),
        (lambda value: value.update(evidence_keys=["smoke18c-1A-r1-t6"]), "plan.phrase_evidence"),
    ],
)
def test_claim_edit_lint_rules_reject_bad_plans(mutation, rule: str) -> None:
    proposed = plan()
    mutation(proposed)
    problems = fix_plan.lint_plan(proposed, ticket(), PACKAGE)
    assert any(problem.startswith(rule) for problem in problems), problems


def test_claim_edit_rejects_shared_matcher(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        fix_plan,
        "_match_source",
        lambda _package, _claim_id: (
            {"use": "common_matchers"},
            {"shared": {"common_matchers": {"action_evidence": [["drive"]]}}},
        ),
    )
    problems = fix_plan.lint_plan(plan(), ticket(), PACKAGE)
    assert any(problem.startswith("plan.claim_shared") for problem in problems)


def test_claim_edit_rejects_phrase_owned_by_another_claim_and_by_a_leak_term() -> None:
    action_owned = plan(phrase="search")
    action_problems = fix_plan.lint_plan(action_owned, ticket(), PACKAGE)
    assert any(problem.startswith("plan.phrase_owned") for problem in action_problems)

    leak_packet = {
        "key": "synthetic-memory-card",
        "scene": "1A",
        "player_input": "Inspect the memory card.",
        "candidates_offered": [TARGET],
    }
    leak_plan = plan(phrase="memory card")
    leak_plan["evidence_keys"] = [leak_packet["key"]]
    leak_problems = fix_plan.lint_plan(leak_plan, ticket(packets=[*PACKETS, leak_packet]), PACKAGE)
    assert any(problem.startswith("plan.phrase_owned") for problem in leak_problems)


def test_claim_edit_claim_offered_is_weak_but_out_of_scene_is_rejected() -> None:
    assert fix_plan.lint_plan(plan(), ticket(), PACKAGE) == []
    other_scene = next(
        claim_id
        for scene, claim_ids in PACKAGE.knowledge_indexes.scene_to_candidates.items()
        if scene != "1A"
        for claim_id in claim_ids
    )
    problems = fix_plan.lint_plan(plan(claim_id=other_scene), ticket(), PACKAGE)
    assert any(problem.startswith("plan.claim") for problem in problems)
    assert any(problem.startswith("plan.claim_offered") for problem in problems)


def test_evidence_menu_and_candidate_matcher_context_are_bounded() -> None:
    evidence = fix_plan.build_evidence(ticket(), PACKAGE)
    assert {entry["kind"] for entry in evidence["fix_menu"]} == {
        "add_pacing_beat",
        "set_text",
        "edit_claim_evidence",
        "unsupported",
    }
    candidate = evidence["candidates"][TARGET]
    assert candidate["action_evidence"] == [
        list(group) for group in PACKAGE.knowledge_indexes.by_id[TARGET].action_evidence
    ]
    assert candidate["uses_shared"] is False
    assert len(candidate["action_evidence"]) <= 8
    assert all(len(group) <= 12 for group in candidate["action_evidence"])


def test_wiring_spec_describes_only_the_claim_evidence_append() -> None:
    text = wiring_spec(plan(), "data/stories/continuity-initiative")
    assert "claim:<id>.action_evidence[<group>] --add" in text
    assert "claim_edit.claim_id, claim_edit.group, and claim_edit.phrase" in text
    assert "smallest hand edit in the owned match file" in text


def test_claim_evidence_content_proof_accepts_one_append_and_rejects_other_changes(tmp_path: Path) -> None:
    source = DEFAULT_ROOT / "source/scenes/1A.match.yaml"
    copied = tmp_path / source.name
    copied.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
    before = yaml.safe_load(copied.read_text(encoding="utf-8"))
    after = copy.deepcopy(before)
    after["claims"][TARGET]["action_evidence"][0].append("my truck")
    copied.write_text(yaml.safe_dump(after, sort_keys=False), encoding="utf-8")
    actual = yaml.safe_load(copied.read_text(encoding="utf-8"))
    assert claim_evidence_change_error(before, actual, TARGET, 0, "my truck") is None

    second_change = copy.deepcopy(actual)
    second_change["claims"][TARGET]["aliases"].append("unplanned alias")
    assert claim_evidence_change_error(before, second_change, TARGET, 0, "my truck")

    wrong_group = copy.deepcopy(before)
    wrong_group["claims"][TARGET]["action_evidence"][1].append("my truck")
    assert claim_evidence_change_error(before, wrong_group, TARGET, 0, "my truck")

    duplicate = copy.deepcopy(before)
    duplicate["claims"][TARGET]["action_evidence"][0].extend(["my truck", "my truck"])
    assert claim_evidence_change_error(before, duplicate, TARGET, 0, "my truck")

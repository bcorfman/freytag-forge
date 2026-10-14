from __future__ import annotations

from pathlib import Path

from bench.pipeline_eval.model import STATE_PREDICATES, STATE_VOCABULARY, load_cases
from storygame.story_package.loader import load_story_package

ROOT = Path(__file__).parents[1]
CASES = ROOT / "bench/pipeline_eval/cases.json"
PACKAGE = load_story_package(ROOT / "data/stories/continuity-initiative")
REQUIRED_CATEGORIES = {
    "short_reference_after_cue",
    "same_phrase_two_referents",
    "pocket_vs_withdraw",
    "enter_vs_drive",
    "ordered_compound",
    "correction",
    "harmless_vs_plot_bypassing_object",
    "unresolved_existing_npc",
    "refused_move_prose",
    "concealment_then_npc",
    "save_load_between_cue_and_followup",
    "reveal_before_after_prerequisites",
    "player_caused_dependency_damage",
    "clarification_invariance",
}


def test_pipeline_fixture_contract_is_grounded_and_split() -> None:
    cases = load_cases(CASES)
    assert {case.category for case in cases} == REQUIRED_CATEGORIES
    assert all(
        {case.split for case in cases if case.category == category} == {"diagnostic", "held_out"}
        for category in REQUIRED_CATEGORIES
    )
    assert all(
        len([case for case in cases if case.category == category and case.split == split]) >= 3
        for category in REQUIRED_CATEGORIES
        for split in ("diagnostic", "held_out")
    )
    assert all(
        key in STATE_VOCABULARY and value in STATE_VOCABULARY[key]
        for case in cases
        if case.expect.state
        for key, value in case.expect.state.items()
    )
    assert all(
        not any(word in phrase.lower() for word in ("cannot", "can't", "unable", "refuse"))
        for case in cases
        for phrase in case.expect.prose_includes
    )

    commands_by_split = {
        split: {command for case in cases if case.split == split for command in case.commands}
        for split in ("diagnostic", "held_out")
    }
    assert not commands_by_split["diagnostic"] & commands_by_split["held_out"]

    fact_ids = set(PACKAGE.world.facts)
    scene_ids = {scene.metadata.scene_id for scene in PACKAGE.scenes}
    knowledge_ids = {item.id for item in PACKAGE.knowledge.knowledge}
    assert all(fact in fact_ids for case in cases for fact in case.setup_facts)
    assert all(case.scene in scene_ids for case in cases)
    assert all(
        not command.startswith(("I ", "I'll"))
        and all(token not in command for token in (" do not ", " without ", " avoid "))
        and command != "Wait."
        for case in cases
        for command in case.commands
    )
    assert all(
        reveal in knowledge_ids
        for case in cases
        for reveal in (*case.expect.required_reveals, *case.expect.allowed_reveals)
    )
    assert all(case.save_load_after is None or case.save_load_after < len(case.commands) for case in cases)
    clarification_cases = [case for case in cases if case.category == "clarification_invariance"]
    assert all(
        case.expect.clarification is True and case.expect.clarification_leaves_clock_unchanged is True
        for case in clarification_cases
    )


def test_state_vocabulary_has_explicit_runtime_grounding() -> None:
    assert set(STATE_PREDICATES) == set(STATE_VOCABULARY)
    assert all(set(predicates) == set(STATE_VOCABULARY[key]) for key, predicates in STATE_PREDICATES.items())


def test_pipeline_fixture_state_claims_use_declared_vocabulary() -> None:
    cases = load_cases(CASES)
    assert all(
        key in STATE_VOCABULARY and value in STATE_VOCABULARY[key]
        for case in cases
        if case.expect.state
        for key, value in case.expect.state.items()
    )

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from scripts.ringer.affordance.cue_eligibility_compare import _scene_states, _true_fact_ids
from scripts.ringer.affordance.sibling_reachability import (
    _activate_unfired_storylets,
    _apply_reveal,
    _seed_reveal_state,
    _state,
    _storylets,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.validation import predicate_matches
from storygame.story_package.loader import load_story_package
from tests.test_cue_eligibility_compare import _delivery, _synthetic_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def old_cue_reveal_available(state: object, fact_id: str) -> bool:
    """Reference copy of the old RuntimeEngine cue predicate."""

    delivery = next(
        (delivery for delivery in state.package.deliveries if delivery.fact_id == fact_id),
        None,
    )
    reveal_fact_ids = {fact_id}
    if delivery is not None:
        reveal_fact_ids.update(cost.fact_id for cost in delivery.costs if cost.op == "assert")
    reveals = tuple(
        knowledge
        for knowledge in state.package.knowledge.knowledge
        if state.current_scene_id in knowledge.available_in_scenes
        and any(effect.op == "assert" and effect.fact_id in reveal_fact_ids for effect in knowledge.establishes)
    )
    return not reveals or any(
        all(predicate_matches(predicate, state.facts) for predicate in knowledge.requires) for knowledge in reveals
    )


def _cue_available(state: object, fact_id: str) -> bool:
    return RuntimeEngine._cue_reveal_available(SimpleNamespace(state=state), fact_id)


def _state_after_reveal(package: object, item_id: str) -> object:
    item = next(item for item in package.knowledge.knowledge if item.id == item_id)
    storylet = next(storylet for storylet in _storylets(package) if storylet.id == item.source.storylet_id)
    state = _state(package, "1A")
    _seed_reveal_state(state, storylet, item)
    _apply_reveal(state, item)
    _activate_unfired_storylets(state, package, "1A")
    return state


def test_old_and_new_real_cue_predicates_differ_only_for_three_spent_rows() -> None:
    differences: set[tuple[str, str, str, bool, bool]] = set()

    for scene in PACKAGE.scenes:
        scene_id = scene.metadata.scene_id
        deliveries = tuple(
            sorted(
                (delivery for delivery in PACKAGE.deliveries if delivery.scene_id == scene_id and delivery.cue_text),
                key=lambda delivery: delivery.fact_id,
            )
        )
        for state_label, state in _scene_states(PACKAGE, scene_id):
            for delivery in deliveries:
                # The report's 160-row audit concerns cues whose own fact is
                # still missing. Established cue facts are already excluded
                # from staging and are not part of this old-vs-new contract.
                if delivery.fact_id in _true_fact_ids(state):
                    continue
                old = old_cue_reveal_available(state, delivery.fact_id)
                new = _cue_available(state, delivery.fact_id)
                if old != new:
                    differences.add((scene_id, state_label, delivery.fact_id, old, new))

    assert differences == {
        (
            "1C",
            "SL-1C-C fired through k_sl_1c_c_r2",
            "national_detention_network_known",
            True,
            False,
        ),
        (
            "2B",
            "SL-2B-B fired through k_sl_2b_b_r3",
            "brandon_claimed_reform_motive",
            True,
            False,
        ),
        (
            "2B",
            "SL-2B-B fired through k_sl_2b_b_r3",
            "brandon_janus_role_known",
            True,
            False,
        ),
    }


def test_synthetic_cue_predicate_keeps_the_other_eligibility_cases() -> None:
    package = _synthetic_package()

    eligible_state = _state(package, "1A")
    _activate_unfired_storylets(eligible_state, package, "1A")
    assert _cue_available(eligible_state, "eligible_fact")

    spent_state = _state_after_reveal(package, "k_spent_setup")
    assert not _cue_available(spent_state, "spent_fact")

    missing_state = _state(package, "1A")
    _activate_unfired_storylets(missing_state, package, "1A")
    assert not _cue_available(missing_state, "missing_fact")

    inactive_package_values = vars(package).copy()
    inactive_package_values["deliveries"] = (*package.deliveries, _delivery("setup_fact"))
    inactive_package = SimpleNamespace(**inactive_package_values)
    inactive_state = _state(inactive_package, "1A")
    _activate_unfired_storylets(inactive_state, inactive_package, "1A")
    assert _cue_available(inactive_state, "setup_fact")

    no_match_package_values = vars(package).copy()
    no_match_package_values["deliveries"] = (*package.deliveries, _delivery("unmatched_fact"))
    no_match_package = SimpleNamespace(**no_match_package_values)
    no_match_state = _state(no_match_package, "1A")
    assert _cue_available(no_match_state, "unmatched_fact")


def test_real_engine_does_not_stage_spent_1c_cue_but_stages_it_when_ranked_first(monkeypatch) -> None:
    spent_state = next(
        state for label, state in _scene_states(PACKAGE, "1C") if label == "SL-1C-C fired through k_sl_1c_c_r2"
    )
    spent_engine = RuntimeEngine(spent_state, lambda _command: {"segments": []})
    spent_engine._activate_pacing()
    assert spent_engine.state.staged_cue_fact_id != "national_detention_network_known"

    entry_state = next(state for label, state in _scene_states(PACKAGE, "1C") if label == "S0")
    for fact_id in ("facility_proof", "captives_confirmed_alive"):
        entry_state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    entry_engine = RuntimeEngine(entry_state, lambda _command: {"segments": []})
    monkeypatch.setattr(
        entry_engine,
        "_ranked_cue_fact_ids",
        lambda: ("national_detention_network_known",),
    )
    entry_engine._activate_pacing()
    assert entry_engine.state.staged_cue_fact_id == "national_detention_network_known"

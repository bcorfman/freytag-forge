from __future__ import annotations

from pathlib import Path

import pytest

from bench.core import load_variation
from storygame.runtime.candidate_matcher import (
    ActionEvidenceCandidate,
    uniquely_matched_authored_handoff,
    uniquely_matched_candidate,
)
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))
ENTRY_FACTS = ("broadcast_started", "brandon_confession_available", "detention_locations_secured")
CUE_FACTS = (
    "truth_no_longer_containable",
    "rebecca_captured",
    "evacuation_route_open",
    "los_angeles_facility_lost",
    "national_network_fragmenting",
    "community_rescue_efforts_begun",
    "phase_two_conflict_plan_known",
)
REVEAL_IDS = (
    "k_sl_3c_a_r1",
    "k_sl_3c_a_r2",
    "k_sl_3c_b_r1",
    "k_sl_3c_b_r2",
    "k_sl_3c_c_r1",
    "k_sl_3c_c_r2",
    "k_sl_3c_d_r1",
    "k_sl_3c_d_r2",
    "k_sl_3c_e_r1",
    "k_sl_3c_e_r2",
)
COMMAND_EXPECTATIONS = (
    ("Send the evidence package.", "k_sl_3c_a_r1"),
    ("Answer Charles's terrorist claim.", "k_sl_3c_a_r2"),
    ("Inspect the broadcast controls.", None),
    ("Evacuate the facility.", None),
    ("Call Rebecca.", None),
    ("Take the Portable data case from Rebecca.", "k_sl_3c_b_r1"),
    ("Copy Rebecca's archive.", "k_sl_3c_b_r2"),
    ("Follow Rebecca out of the executive office.", "k_sl_3c_b_r1"),
    ("Inspect the executive office.", None),
    ("Open the drainage pump controls.", None),
    ("Restore the drainage pumps.", "k_sl_3c_c_r1"),
    ("Lead Michelle through the maintenance routes.", "k_sl_3c_c_r1"),
    ("Inspect the drainage pump controls.", None),
    ("Open the surface gates.", "k_sl_3c_c_r2"),
    ("Release the surface gates.", "k_sl_3c_c_r2"),
    ("Use the senior official's authorization.", "k_sl_3c_c_r2"),
    ("Inspect the surface gates.", None),
    ("Check reports from other detention sites.", "k_sl_3c_d_r1"),
    ("Read the detention site reports.", "k_sl_3c_d_r1"),
    ("Call the families of the missing.", "k_sl_3c_d_r2"),
    ("Contact missing families.", "k_sl_3c_d_r2"),
    ("Open the reports.", None),
    ("Watch the families of the missing.", None),
    ("Open the recovered document.", "k_sl_3c_e_r1"),
    ("Trace Charles's signal.", "k_sl_3c_e_r2"),
    ("Read Charles's last signal.", None),
    ("Inspect the broadcast chamber.", None),
    ("Send the evidence package to independent networks.", None),
    ("Follow Rebecca.", "k_sl_3c_b_r1"),
    ("Follow Rebecca with Michelle.", "k_sl_3c_b_r1"),
    ("Follow Rebecca's escape route.", "k_sl_3c_b_r1"),
    ("Take Rebecca's escape route.", "k_sl_3c_b_r1"),
    ("Extend the emergency gate authorization.", "k_sl_3c_c_r2"),
    ("Guide the captives through the emergency gate.", "k_sl_3c_c_r2"),
    ("Lead the captives to safety.", None),
    ("Lead the captives to the safe surface.", None),
    ("Open the surface exit.", "k_sl_3c_c_r2"),
    ("Broadcast updates to the families.", "k_sl_3c_d_r2"),
    ("Broadcast the reports from other detention sites.", "k_sl_3c_d_r1"),
    ("Broadcast reports from other detention sites.", "k_sl_3c_d_r1"),
    ("Answer the families with the broadcast's truth.", "k_sl_3c_d_r2"),
    ("Carry Michelle to safety.", None),
    ("Open the access panel.", None),
    ("Broadcast the detention site list.", None),
    ("Take Rebecca's portable data case.", "k_sl_3c_b_r1"),
    ("Ask Rebecca about Charles.", None),
    ("Talk to Rebecca.", None),
    ("Ask Rebecca about her archive.", "k_sl_3c_b_r2"),
    ("Answer the families about Charles's terrorist claim.", None),
    ("Guide Michelle through the maintenance routes and the captives through the emergency gate.", None),
    ("Answer the families.", "k_sl_3c_d_r2"),
    ("Reassure the families.", "k_sl_3c_d_r2"),
    ("Answer the families' requests for information.", "k_sl_3c_d_r2"),
    ("Answer the families with the detention-site reports.", "k_sl_3c_d_r2"),
    ("Respond to the families of the missing.", "k_sl_3c_d_r2"),
    ("Reassure the families of the missing.", "k_sl_3c_d_r2"),
    ("Answer them.", None),
    ("Answer the people waiting.", None),
    ("Trace Charles's last remote channel.", "k_sl_3c_e_r2"),
    ("Examine Charles's last remote channel.", "k_sl_3c_e_r2"),
    ("Read Charles's last remote channel.", None),
    ("Decode Charles's last remote message.", None),
    ("Follow Charles's last remote channel.", "k_sl_3c_e_r2"),
    ("Enter my one-use authority code into the gate-status panel.", None),
    ("Respond to Charles's terrorist claim.", "k_sl_3c_a_r2"),
    ("Answer Michelle.", None),
    ("Reassure the captives.", None),
    ("Answer the reports from other detention sites.", None),
    ("Read Charles's signal.", None),
    ("Extend the gate authorization.", "k_sl_3c_c_r2"),
    ("Guide the captives to the surface gates.", "k_sl_3c_c_r2"),
    ("Lead the captives to the surface gates.", "k_sl_3c_c_r2"),
    ("Broadcast updates to the detention sites.", None),
    ("Answer the families with the reports.", "k_sl_3c_d_r2"),
    ("Decode the recovered document.", "k_sl_3c_e_r1"),
    ("Examine the recovered document.", "k_sl_3c_e_r1"),
    ("Decode Charles's signal.", None),
    ("Examine Charles's signal.", "k_sl_3c_e_r2"),
    ("Read Charles's last remote channel and the recovered document.", "k_sl_3c_e_r1"),
    ("Broadcast the reports to the families.", "k_sl_3c_d_r1"),
    ("Answer the families with Charles's terrorist claim.", None),
    ("Reassure the families about the revolt.", "k_sl_3c_d_r2"),
    ("Respond to the families about Charles's terrorist claim.", None),
    ("Tell the families that the missing are alive.", "k_sl_3c_d_r2"),
    ("Contact the families.", "k_sl_3c_d_r2"),
    ("Enter the gate code.", "k_sl_3c_c_r2"),
    ("Enter the authority code.", None),
    ("Enter the gate-status panel.", None),
    ("Inspect the gate-status panel.", None),
    ("Read the recovered document.", "k_sl_3c_e_r1"),
    ("Read the recovered document about Charles's signal.", "k_sl_3c_e_r1"),
    ("Read the recovered document and trace Charles's last remote channel.", None),
    ("Follow the last remote channel.", None),
    ("Trace his last remote channel.", "k_sl_3c_e_r2"),
    ("Trace the last remote message.", None),
    ("Trace the recovered document.", None),
    ("Decode the recovered file.", None),
    ("Broadcast evidence to independent networks.", None),
    ("Broadcast updates about the families.", "k_sl_3c_d_r2"),
    ("Broadcast updates about the detention sites.", None),
    ("Answer the families with updates about other detention sites.", "k_sl_3c_d_r2"),
    ("Broadcasting the reports from the other detention sites.", "k_sl_3c_d_r1"),
    ("Keep broadcasting the reports from other detention sites.", "k_sl_3c_d_r1"),
    (
        "Continue broadcasting the reports from all remaining detention sites and coordinate their rescue.",
        "k_sl_3c_d_r1",
    ),
    ("Relay the reports from other detention sites.", "k_sl_3c_d_r1"),
    ("Relaying the reports from other detention sites.", "k_sl_3c_d_r1"),
    (
        "Continue broadcasting the reports from the other detention sites and "
        "coordinate rescue efforts for the remaining missing.",
        None,
    ),
    ("Continue broadcasting the truth about JANUS.", None),
    ("Keep broadcasting the evidence to independent networks.", None),
    ("Relay the evidence to independent networks.", "k_sl_3c_a_r1"),
    ("Relay the broadcast.", None),
    ("Broadcasting updates to the detention sites.", None),
)


def _state_3c(*, turn_index: int = 0) -> RuntimeState:
    state = RuntimeState(package=PACKAGE, current_scene_id="3C", phase="resolution")
    state._assert_scene_entry_fact("3C")
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    state.turn_index = turn_index
    return state


def _provider(knowledge_id: str):
    knowledge = PACKAGE.knowledge_indexes.by_id[knowledge_id]
    text = knowledge.delivery_text or knowledge.statement
    return lambda _command: {
        "segments": [{"kind": "narration", "text": text, "grounding_ids": [knowledge_id]}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _reveal(engine: RuntimeEngine, knowledge_id: str, command: str) -> None:
    engine.provider = _provider(knowledge_id)
    engine.turn(command)
    engine._activate_pacing()  # noqa: SLF001 - inspect the next staged cue.


def _finish_a_and_b() -> RuntimeEngine:
    engine = RuntimeEngine(_state_3c(), _provider("k_sl_3c_a_r1"))
    _reveal(engine, "k_sl_3c_a_r1", "Send the evidence package.")
    _reveal(engine, "k_sl_3c_b_r1", "Take the Portable data case from Rebecca.")
    return engine


def _finish_a_through_c() -> RuntimeEngine:
    engine = _finish_a_and_b()
    _reveal(engine, "k_sl_3c_c_r1", "Restore the drainage pumps.")
    _reveal(engine, "k_sl_3c_c_r2", "Open the surface gates.")
    return engine


def test_3c_cue_chain_stages_each_next_fact() -> None:
    engine = RuntimeEngine(_state_3c(), _provider("k_sl_3c_a_r1"))
    engine._activate_pacing()  # noqa: SLF001 - inspect deterministic cue staging.
    assert engine.state.staged_cue_fact_id == "truth_no_longer_containable"

    _reveal(engine, "k_sl_3c_a_r1", "Send the evidence package.")
    assert engine.state.staged_cue_fact_id == "rebecca_captured"
    _reveal(engine, "k_sl_3c_b_r1", "Take the Portable data case from Rebecca.")
    assert engine.state.staged_cue_fact_id in {"evacuation_route_open", "los_angeles_facility_lost"}

    first_c = engine.state.staged_cue_fact_id
    c_reveal = "k_sl_3c_c_r1" if first_c == "evacuation_route_open" else "k_sl_3c_c_r2"
    c_command = "Restore the drainage pumps." if c_reveal.endswith("c_r1") else "Open the surface gates."
    _reveal(engine, c_reveal, c_command)
    missing_c = "los_angeles_facility_lost" if first_c == "evacuation_route_open" else "evacuation_route_open"
    assert engine.state.staged_cue_fact_id == missing_c
    _reveal(
        engine,
        "k_sl_3c_c_r2" if c_reveal.endswith("c_r1") else "k_sl_3c_c_r1",
        "Open the surface gates." if c_reveal.endswith("c_r1") else "Restore the drainage pumps.",
    )
    assert engine.state.staged_cue_fact_id in {"national_network_fragmenting", "community_rescue_efforts_begun"}

    first_d = engine.state.staged_cue_fact_id
    d_reveal = "k_sl_3c_d_r1" if first_d == "national_network_fragmenting" else "k_sl_3c_d_r2"
    d_command = (
        "Check reports from other detention sites."
        if d_reveal.endswith("d_r1")
        else "Call the families of the missing."
    )
    _reveal(engine, d_reveal, d_command)
    assert engine.state.staged_cue_fact_id == (
        "community_rescue_efforts_begun"
        if first_d == "national_network_fragmenting"
        else "national_network_fragmenting"
    )
    _reveal(
        engine,
        "k_sl_3c_d_r2" if d_reveal.endswith("d_r1") else "k_sl_3c_d_r1",
        (
            "Call the families of the missing."
            if d_reveal.endswith("d_r1")
            else "Check reports from other detention sites."
        ),
    )
    assert engine.state.staged_cue_fact_id == "phase_two_conflict_plan_known"


@pytest.mark.parametrize("order", [("k_sl_3c_c_r1", "k_sl_3c_c_r2"), ("k_sl_3c_c_r2", "k_sl_3c_c_r1")])
def test_both_c_parts_are_earnable_in_either_order(order: tuple[str, str]) -> None:
    engine = _finish_a_and_b()
    commands = {
        "k_sl_3c_c_r1": "Restore the drainage pumps.",
        "k_sl_3c_c_r2": "Open the surface gates.",
    }
    _reveal(engine, order[0], commands[order[0]])
    assert not any(fact.predicate == "captives_reaching_surface" for fact in engine.state.facts.asserted)
    _reveal(engine, order[1], commands[order[1]])
    assert any(fact.predicate == "captives_reaching_surface" for fact in engine.state.facts.asserted)


def test_after_d_r1_only_d_r2_remains_in_the_reveal_universe() -> None:
    engine = _finish_a_through_c()
    _reveal(engine, "k_sl_3c_d_r1", "Check reports from other detention sites.")

    projection = engine.projector.project(engine.state, "player", "Call the families of the missing.")
    assert [candidate.id for candidate in projection.reveal_universe] == ["k_sl_3c_d_r2"]


def test_resolution_scene_stages_cues_without_staging_deadline_handoff() -> None:
    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "3C")
    engine = RuntimeEngine(_state_3c(turn_index=window.handoff_after_turns), _provider("k_sl_3c_a_r1"))
    engine._activate_pacing()  # noqa: SLF001 - inspect the staging split.

    assert engine.state.staged_cue_fact_id == "truth_no_longer_containable"
    assert engine.state.staged_handoff_fact_ids == ()


def test_nonresolution_scene_still_stages_a_cue() -> None:
    scene = next(item for item in PACKAGE.scenes if item.metadata.scene_id == "1B")
    state = RuntimeState(package=PACKAGE, current_scene_id="1B", phase=scene.metadata.freytag_phase)
    state.facts.assert_fact(Fact(predicate="source_ready", subject="story", value="true"))
    engine = RuntimeEngine(state, lambda _command: {"segments": [{"kind": "narration", "text": "Search the park."}]})
    engine._activate_pacing()  # noqa: SLF001 - inspect existing cue behavior.

    assert engine.state.staged_cue_fact_id is not None


def test_player_commands_match_the_answer_table() -> None:
    # Build the matcher candidates from the same projected fields used by the
    # engine's shadow matcher. Keep all ten reveals in this audit so commands
    # for later steps are checked even before their prerequisites are true.
    candidates = tuple(
        ActionEvidenceCandidate(id=knowledge.id, required_groups=knowledge.action_evidence)
        for knowledge_id in REVEAL_IDS
        if (knowledge := PACKAGE.knowledge_indexes.by_id[knowledge_id]).action_evidence
    )
    assert {candidate.id for candidate in candidates} == set(REVEAL_IDS)

    for command, expected_id in COMMAND_EXPECTATIONS:
        matched = uniquely_matched_candidate(command, candidates)
        if expected_id is None:
            assert matched is None
        else:
            assert matched is not None
            assert matched.id == expected_id


def test_3c_cues_do_not_use_protected_words() -> None:
    forbidden = ("janus", "phase one", "phase two", "coded message")
    deliveries = tuple(delivery for delivery in PACKAGE.deliveries if delivery.scene_id == "3C")

    assert {delivery.fact_id for delivery in deliveries} == set(CUE_FACTS)
    for delivery in deliveries:
        assert delivery.cue_text is not None
        lowered = delivery.cue_text.casefold()
        assert not any(word in lowered for word in forbidden), delivery.fact_id


def _families_package_and_state(variation_path: str = "stage7-3c-families.json"):
    from bench.core import load_variation, package_and_state

    variation = load_variation(Path("bench/variations") / variation_path)
    package, state = package_and_state(variation, "3C")
    state._assert_scene_entry_fact("3C")  # noqa: SLF001 - establish the committed scene entry.
    for fact_id in ENTRY_FACTS:
        state.facts.assert_fact(Fact(predicate=fact_id, subject="story", value="true"))
    return package, state


def _families_provider(package, knowledge_id: str):
    knowledge = package.knowledge_indexes.by_id[knowledge_id]
    return lambda _command: {
        "segments": [{"kind": "narration", "text": knowledge.delivery_text or knowledge.statement}],
        "selected_knowledge_ids": [knowledge_id],
    }


def _families_finish_a_through_c(
    order: tuple[str, ...] = ("k_sl_3c_c_r1", "k_sl_3c_c_r2"),
    variation_path: str = "stage7-3c-families.json",
):
    package, state = _families_package_and_state(variation_path)
    commands = {
        "k_sl_3c_a_r1": "Send the evidence package.",
        "k_sl_3c_b_r1": "Take the Portable data case from Rebecca.",
        "k_sl_3c_c_r1": "Restore the drainage pumps.",
        "k_sl_3c_c_r2": "Open the surface gates.",
    }
    engine = RuntimeEngine(state, _families_provider(package, "k_sl_3c_a_r1"))
    for knowledge_id in ("k_sl_3c_a_r1", "k_sl_3c_b_r1", *order):
        engine.provider = _families_provider(package, knowledge_id)
        engine.turn(commands[knowledge_id])
        engine._activate_pacing()  # noqa: SLF001 - commit the next staged cue.
    return package, engine


def _families_match(package, engine, command: str):
    projection = engine.projector.project(engine.state, "player", command)
    return uniquely_matched_authored_handoff(command, projection.reveal_universe)


def test_families_replacement_is_unique_and_current_package_lacks_aliases() -> None:
    source = Path("data/stories/continuity-initiative/knowledge.yaml").read_text(encoding="utf-8")
    old = "reassure the families, respond to the families]"
    assert source.count(old) == 1

    package, _ = _families_package_and_state()
    d_r2 = package.knowledge_indexes.by_id["k_sl_3c_d_r2"]
    aliases = (
        "broadcast a message to the families",
        "broadcast a response to the families",
        "broadcast an update to the families",
    )
    assert all(alias in d_r2.action_evidence[0] for alias in aliases)
    current = PACKAGE.knowledge_indexes.by_id["k_sl_3c_d_r2"]
    assert all(
        not uniquely_matched_candidate(
            alias, (ActionEvidenceCandidate(id=current.id, required_groups=current.action_evidence),)
        )
        for alias in aliases
    )


def test_families_c2_only_does_not_make_d_eligible() -> None:
    package, engine = _families_finish_a_through_c(("k_sl_3c_c_r2",))
    assert not {"k_sl_3c_d_r1", "k_sl_3c_d_r2"} & {
        candidate.id
        for candidate in engine.projector.project(
            engine.state, "player", "Broadcast the reports to the families."
        ).reveal_universe
    }


def test_families_neither_d_part_is_eligible_before_c_is_complete() -> None:
    package, engine = _families_finish_a_through_c(())
    projection = engine.projector.project(engine.state, "player", "Broadcast the reports to the families.")
    assert not {"k_sl_3c_d_r1", "k_sl_3c_d_r2"} & {candidate.id for candidate in projection.reveal_universe}
    for alias in (
        "Broadcast a message to the families.",
        "Broadcast a response to the families.",
        "Broadcast an update to the families.",
    ):
        assert _families_match(package, engine, alias) is None


def test_families_unrelated_recipients_never_match() -> None:
    commands = (
        "Broadcast a message to the journalists.",
        "Broadcast an update to the guards.",
        "Broadcast a message to Brandon.",
    )

    package, engine = _families_finish_a_through_c()
    for command in commands:
        assert _families_match(package, engine, command) is None

    engine.provider = _families_provider(package, "k_sl_3c_d_r1")
    engine.turn("Read the detention site reports.")
    engine._activate_pacing()  # noqa: SLF001 - spend D1 before repeating the controls.
    for command in commands:
        assert _families_match(package, engine, command) is None


def test_current_package_does_not_match_family_aliases_through_projection() -> None:
    engine = _finish_a_through_c()
    aliases = (
        "Broadcast a message to the families.",
        "Broadcast a response to the families.",
        "Broadcast an update to the families.",
    )
    for alias in aliases:
        projection = engine.projector.project(engine.state, "player", alias)
        assert uniquely_matched_authored_handoff(alias, projection.reveal_universe) is None


FAMILIES_V2_PATH = "stage7-3c-families-v2.json"


def _families_v2_added_aliases() -> tuple[str, ...]:
    from bench.core import package_and_state

    pump, _ = package_and_state(load_variation(Path("bench/variations/stage7-3c-pump-need.json")), "3C")
    v2, _ = package_and_state(load_variation(Path("bench/variations") / FAMILIES_V2_PATH), "3C")
    pump_aliases = set(pump.knowledge_indexes.by_id["k_sl_3c_d_r2"].action_evidence[0])
    v2_aliases = tuple(v2.knowledge_indexes.by_id["k_sl_3c_d_r2"].action_evidence[0])
    added = tuple(alias for alias in v2_aliases if alias not in pump_aliases)
    assert len(added) == 34
    return added


@pytest.mark.parametrize("variation_path", [FAMILIES_V2_PATH])
def test_families_v2_initial_free_evidence_table(variation_path: str) -> None:
    package, engine = _families_finish_a_through_c(variation_path=variation_path)
    expectations = (
        ("Send the families a message confirming the captives are alive.", "k_sl_3c_d_r2"),
        ("Send the families the names and locations of the rescued prisoners.", "k_sl_3c_d_r2"),
        ("Broadcast the captives' names and locations to their families.", "k_sl_3c_d_r2"),
        ("Broadcast the prisoner records and names to the families of the missing.", "k_sl_3c_d_r2"),
        ("Broadcast a message to the families of the missing.", "k_sl_3c_d_r2"),
        ("Tell their families that the captives are safe.", "k_sl_3c_d_r2"),
        ("Broadcast music to the families.", None),
        ("Listen for any response from the families.", None),
        ("Send the families into danger.", None),
        ("Broadcast the reports to the families.", "k_sl_3c_d_r1"),
        ("Read the detention site reports and broadcast a message to the families.", None),
    )
    for command, expected_id in expectations:
        matched = _families_match(package, engine, command)
        assert matched is None if expected_id is None else matched.candidate.id == expected_id

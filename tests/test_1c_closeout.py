from __future__ import annotations

import re

from storygame.runtime.candidate_matcher import uniquely_matched_authored_handoff
from storygame.runtime.knowledge import RevealCandidate
from tests.test_richer_1c import PACKAGE, _engine, _entries, _handoff, _routes


def _candidate(
    candidate_id: str,
    groups: tuple[tuple[str, ...], ...],
    *,
    repeatable: bool = False,
) -> RevealCandidate:
    return RevealCandidate(
        id=candidate_id,
        statement=f"Statement for {candidate_id}.",
        action_evidence=groups,
        must_convey=(),
        delivery_text=f"Delivery for {candidate_id}.",
        repeatable=repeatable,
    )


def test_the_optional_1c_reveals_last_until_the_transfer_window_closes():
    routes = _routes()
    storylets = {storylet.id: storylet for storylet in PACKAGE.storylets}
    transfer_window = next(event for event in PACKAGE.pacing.events if event.id == "transfer_window_1c")

    for storylet_id in ("SL-1C-E", "SL-1C-F", "SL-1C-G"):
        route_pacing = routes[storylet_id]["activation"]["pacing"]
        assert (
            route_pacing["earliest_turn"],
            route_pacing["target_turn"],
            route_pacing["latest_turn"],
        ) == (0, 2, 4)
        storylet = storylets[storylet_id]
        assert (storylet.earliest_turn, storylet.target_turn, storylet.latest_turn) == (0, 2, 4)
        assert storylet.latest_turn < transfer_window.at_turn


def test_a_more_specific_match_wins_and_equal_matches_still_tie():
    command = "Watch the processing line for Michelle."
    less_specific = _candidate(
        "X",
        (("watch",), ("processing line",)),
    )
    more_specific = _candidate(
        "Y",
        (("watch",), ("processing line",), ("Michelle",)),
    )
    assert uniquely_matched_authored_handoff(command, (less_specific, more_specific)).candidate.id == "Y"

    tied_first = _candidate("first", (("watch",), ("processing line",)))
    tied_second = _candidate("second", (("watch",), ("processing line",)))
    assert uniquely_matched_authored_handoff(command, (tied_first, tied_second)) is None

    repeatable = _candidate(
        "repeatable",
        (("watch",), ("processing line",), ("Michelle",)),
        repeatable=True,
    )
    non_repeatable = _candidate("non-repeatable", (("watch",), ("processing line",)))
    assert uniquely_matched_authored_handoff(command, (repeatable, non_repeatable)).candidate.id == "non-repeatable"

    assert uniquely_matched_authored_handoff(command, (more_specific,)).candidate.id == "Y"
    assert uniquely_matched_authored_handoff("Listen to the vents.", (more_specific,)) is None


def test_the_michelle_command_reaches_the_michelle_glimpse():
    entries = _entries()
    required = {
        entry_id: {(requirement.fact_id, requirement.equals) for requirement in entries[entry_id].requires}
        for entry_id in ("k_sl_1c_b_r1", "k_sl_1c_b_r2")
    }
    assert required["k_sl_1c_b_r1"] == {("facility_proof", True), ("transfer_window_missed", False)}
    assert required["k_sl_1c_b_r2"] == required["k_sl_1c_b_r1"]

    state, engine = _engine(true_facts=("facility_proof",))
    assert "transfer_window_missed" not in {fact.predicate for fact in state.facts.asserted}
    handoff = _handoff(engine, state, "Watch the processing line for Michelle.")
    assert handoff is not None and handoff.candidate.id == "k_sl_1c_b_r2"

    state, engine = _engine(true_facts=("facility_proof",))
    handoff = _handoff(engine, state, "Study the prisoners.")
    assert handoff is not None and handoff.candidate.id == "k_sl_1c_b_r1"


def test_no_other_unique_1c_handoff_changes():
    checks = (
        ((), "Inspect the loading docks.", "k_sl_1c_a_r1"),
        (("facility_proof",), "Study the prisoners.", "k_sl_1c_b_r1"),
        (
            ("facility_proof", "captives_confirmed_alive"),
            "Ask Brandon about the transfer route.",
            "k_sl_1c_c_secure_route",
        ),
        (("facility_proof", "captives_confirmed_alive"), "Copy the prisoner numbers.", "k_sl_1c_c_copy_numbers"),
    )
    for facts, command, entry_id in checks:
        state, engine = _engine(true_facts=facts)
        handoff = _handoff(engine, state, command)
        assert handoff is not None and handoff.candidate.id == entry_id, command


def test_3a_reunion_says_the_captives_are_awake():
    entry = _entries()["k_sl_3a_a_r1"]
    planned_text = (
        "Kristin joins Michelle beside the captives. They are awake: the dose "
        "they were given is for the trip, and it wears off in the detention block. For one unhurried moment the two "
        "of them talk to each other and nobody asks anything of either. Then Michelle turns back to her coded "
        "announcements and points toward the medical level, where the experiment records wait."
    )
    assert re.sub(r"\s+", " ", entry.delivery_text).strip() == planned_text
    assert entry.statement == (
        "Kristin reaches Michelle alive, and the two share one unhurried moment before Michelle returns to directing "
        "prisoners through stolen radios and coded announcements."
    )

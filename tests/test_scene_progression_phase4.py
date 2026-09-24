"""Regression tests retained while the provider contract is narrowed in Phase 3."""

from __future__ import annotations

from pathlib import Path

import pytest

from storygame.runtime.contracts import ResolvedTurnProposal, SceneTransitionProposal
from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.runtime.validation import ProgressionValidator, ProposalValidationError
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def _turn(text: str, selected: list[str] | None = None) -> dict[str, object]:
    # The runtime requires a selection to ground the segment that reveals it.
    segment: dict[str, object] = {"kind": "narration", "text": text}
    if selected:
        segment["grounding_ids"] = list(selected)
    return {"segments": [segment], "selected_knowledge_ids": selected or []}


def test_recording_only_reveal_is_rejected_before_custody_is_committed() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state, lambda _: _turn("The damaged recording carries Michelle's warning.", ["k_sl_1a_b_r2"])
    )

    with pytest.raises(ProposalValidationError, match="selected knowledge is not eligible"):
        engine.turn("Play Michelle's damaged recording.")

    assert Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="michelle_warning_known", subject="story", value="true") not in state.facts.asserted


def test_warning_first_path_secures_card_then_reads_remaining_files() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-E")
    responses = iter(
        (
            _turn(
                "A memory card is taped beneath the KMS drawer. Michelle left it there.",
                ["k_sl_1a_b_r0"],
            ),
            _turn(
                'The card holds a damaged recording. Michelle\'s voice warns, "Do not trust the emergency broadcasts."',
                ["k_sl_1a_b_r2"],
            ),
            _turn(
                "Kristin reads the remaining files on Michelle's recovered memory card and learns the place she used "
                "to trade information.",
                ["k_sl_1a_d_r1"],
            ),
        )
    )
    engine = RuntimeEngine(state, lambda _: next(responses))

    engine.turn("Search beneath the marked drawer for Michelle's memory card.")
    assert Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true") in state.facts.asserted

    engine.turn("Play the damaged recording on Michelle's memory card.")
    assert Fact(predicate="michelle_warning_known", subject="story", value="true") in state.facts.asserted
    state.active_event_ids.add("SL-1A-D")
    engine.turn("Read the remaining files on Michelle's recovered memory card.")

    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="michelle_lead_actionable", subject="story", value="true") in state.facts.asserted


def test_complete_path_secures_card_with_files_and_park_lead() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.active_event_ids.add("SL-1A-E")
    engine = RuntimeEngine(
        state,
        lambda player_input: (
            _turn("A memory card is taped beneath the KMS drawer. Michelle left it there.", ["k_sl_1a_b_r0"])
            if "Search" in player_input
            else _turn(
                "The card holds Michelle's saved files and a damaged recording. The recording warns, "
                '"Do not trust the emergency broadcasts." The files name the Continuity Initiative and point to a dead '
                "drop at a bench in the park.",
                ["k_sl_1a_b_r1"],
            )
        ),
    )

    engine.turn("Search beneath the marked drawer for Michelle's memory card.")
    state.active_event_ids.add("SL-1A-B")
    engine.turn("Read the files on Michelle's recovered memory card.")

    assert Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="michelle_lead_actionable", subject="story", value="true") in state.facts.asserted


@pytest.mark.parametrize(
    "selected", [["k_sl_1c_b_r1"], ["k_sl_1a_b_r2", "k_sl_1a_b_r2"], ["k_sl_1a_b_r1", "k_sl_1a_b_r2"]]
)
def test_invalid_or_duplicate_selection_is_atomic(selected: list[str]) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = (set(state.facts.asserted), set(state.fired_event_ids), tuple(state.turn_records))
    engine = RuntimeEngine(state, lambda _: _turn("The room yields no unearned revelation.", selected))

    with pytest.raises((ProposalValidationError, ValueError)):
        engine.turn("Inspect Michelle's phone.")

    assert (state.facts.asserted, set(state.fired_event_ids), tuple(state.turn_records)) == before


def test_grounding_cannot_name_an_unselected_or_invented_source() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state,
        lambda _: {
            "segments": [{"kind": "narration", "text": "A recording clicks on.", "grounding_ids": ["SL-1A-B"]}],
            "selected_knowledge_ids": ["k_sl_1a_b_r2"],
        },
    )

    with pytest.raises(ProposalValidationError, match="grounding"):
        engine.turn("Recover the damaged recording.")
    assert Fact(predicate="michelle_warning_known", subject="story", value="true") not in state.facts.asserted


def test_a_reveal_the_narration_never_delivers_cannot_commit_or_move_the_scene() -> None:
    """A silent commit strands the player in the next scene with no reason to be there.

    Selecting Scene 1A's memory-card reveal while narrating only a scratch and a
    few loose screws used to commit `continuity_initiative_known`, fire the
    canonical bridge, and carry Kristin to the park bench the player had never
    been told about. Nothing the player read explained the move.
    """

    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state,
        lambda _: {
            "segments": [
                {
                    "kind": "narration",
                    "text": "Michelle fears the emergency broadcasts.",
                    "grounding_ids": ["k_sl_1a_b_r1"],
                }
            ],
            "selected_knowledge_ids": ["k_sl_1a_b_r1"],
        },
    )

    with pytest.raises(ProposalValidationError, match="memory card"):
        engine.turn("Look under the workstation.", clock_seconds=120)

    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") not in state.facts.asserted
    assert Fact(predicate="michelle_lead_actionable", subject="story", value="true") not in state.facts.asserted
    assert "SL-1A-B" not in state.fired_event_ids
    assert state.current_scene_id == "1A", "the story may not leave the house on a reveal the player never read"


def test_a_fully_conveyed_reveal_commits_and_opens_the_scene_exit() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state,
        lambda _: (
            {
                "segments": [
                    {
                        "kind": "narration",
                        "text": (
                            "The card holds Michelle's saved files and a damaged recording. The recording warns, "
                            '"Do not trust the emergency broadcasts." The files name the Continuity Initiative and '
                            "point to a dead drop at a bench in the park."
                        ),
                        "grounding_ids": ["k_sl_1a_b_r1"],
                    }
                ],
                "selected_knowledge_ids": ["k_sl_1a_b_r1"],
            }
            if not state.fired_event_ids
            else _turn("The house holds its breath while Kristin decides what to do next.")
        ),
    )

    engine.turn("Look under the workstation.", clock_seconds=120)

    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="michelle_lead_actionable", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true") in state.facts.asserted
    assert "SL-1A-B" in state.fired_event_ids
    assert state.current_scene_id == "1A"

    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "1A")
    for _ in range(window.min_turns - 1):
        engine.turn("Search the room for the next concrete lead.")

    assert state.current_scene_id == "1B"


def test_an_ungrounded_fully_conveyed_reveal_derives_its_grounding_and_commits() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state,
        lambda _: {
            "segments": [
                {
                    "kind": "narration",
                    "text": (
                        "The card holds Michelle's saved files and a damaged recording. The recording warns, "
                        '"Do not trust the emergency broadcasts." The files name the Continuity Initiative and '
                        "point to a dead drop at a bench in the park."
                    ),
                }
            ],
            "selected_knowledge_ids": ["k_sl_1a_b_r1"],
        },
    )

    proposal = engine.turn("Look under the workstation.", clock_seconds=120)

    assert proposal.selected_knowledge_ids == ("k_sl_1a_b_r1",)
    assert proposal.segments[0].grounding_ids == ("k_sl_1a_b_r1",)
    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") in state.facts.asserted


def test_an_ungrounded_partially_told_reveal_is_still_rejected() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="memory_card_in_kristins_custody", subject="story", value="true"))
    state.active_event_ids.add("SL-1A-B")
    engine = RuntimeEngine(
        state,
        lambda _: {
            "segments": [{"kind": "narration", "text": "Kristin finds Michelle's memory card."}],
            "selected_knowledge_ids": ["k_sl_1a_b_r1"],
        },
    )

    with pytest.raises(ProposalValidationError, match="grounded"):
        engine.turn("Look under the workstation.", clock_seconds=120)

    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") not in state.facts.asserted


def test_declared_pressure_event_advances_without_provider_timing_or_prose_parsing() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _: _turn("Dust shifts beneath the door."))

    for player_input in (
        "Inspect the marked front gate.",
        "Examine the patrol marker on the gate.",
        "Search the front room.",
        "Trace the patrol route.",
    ):
        engine.turn(player_input)

    assert Fact(predicate="patrol_return_pressure", subject="story", value="true") in state.facts.asserted
    assert "pressure_1a" in state.fired_event_ids
    assert Fact(predicate="story_elapsed_seconds", subject="story", value="240") in state.facts.asserted


def test_transition_rejects_lead_and_patrol_without_card_custody() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="michelle_lead_actionable", subject="story", value="true"))
    state.facts.assert_fact(Fact(predicate="patrol_return_pressure", subject="story", value="true"))
    proposal = ResolvedTurnProposal(
        segments=({"kind": "narration", "text": "Kristin leaves the house."},),
        transition=SceneTransitionProposal(transition_id="t_1a_1b"),
    )

    with pytest.raises(ProposalValidationError, match="transition triggers"):
        ProgressionValidator(PACKAGE).validate(state, proposal)


def test_untrusted_provider_operations_and_transitions_fail_closed() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    before = (set(state.facts.asserted), set(state.fired_event_ids), tuple(state.turn_records))
    engine = RuntimeEngine(
        state,
        lambda _: {
            "segments": [{"kind": "narration", "text": "An invented shortcut appears."}],
            "operations": [{"operation": "assert", "fact": {"predicate": "facility_proof", "subject": "story"}}],
        },
    )

    with pytest.raises(ValueError):
        engine.turn("Inspect the facility.")
    assert (state.facts.asserted, set(state.fired_event_ids), tuple(state.turn_records)) == before


def test_internal_game_break_path_keeps_the_resolved_candidate_pending_until_proceed(monkeypatch) -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    engine = RuntimeEngine(state, lambda _: _turn("The choice would strand a future dependency."))
    monkeypatch.setattr(engine.validator, "validate", lambda *_: ("brandon",))

    proposal = engine.turn("Make the risky attempt.")

    assert proposal.game_break is not None
    assert state.has_pending_break
    engine.resolve_break("proceed")
    assert not state.has_pending_break

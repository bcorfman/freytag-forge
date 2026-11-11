"""Deterministic full-game canon journey: every authored transition is reachable.

These tests drive the runtime with a scripted provider so CI proves the story
package and engine support a complete 1A -> 3C playthrough without any model
call. The clocked variant mirrors the hosted Playwright package-clock recipe;
the unclocked variant mirrors default 60-second turns and stays within the
authored package budget.
"""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.facts import Fact
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package
from tests._legacy_package import legacy_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

# (selected knowledge id or None, elapsed target, expected scene at turn end)
# Alternate-realization coverage at the default 60-second turn cadence.
UNCLOCKED_JOURNEY = [
    ("k_sl_1a_a_r1", "1A"),
    ("k_sl_1a_b_r0", "1A"),
    (None, "1A"),
    (None, "1A"),
    ("k_sl_1a_b_r1", "1A"),
    (None, "1A"),
    (None, "1A"),
    (None, "1A"),
    (None, "1A"),
    (None, "1A"),
    (None, "1A"),
    (None, "1A"),
    (None, "1B"),
    ("k_sl_1b_d_r1", "1B"),
    ("k_sl_1b_b_r2", "1B"),
    ("k_sl_1b_c_r1", "1B"),
    (None, "1B"),
    (None, "1B"),
    (None, "1B"),
    (None, "1B"),
    (None, "1C"),
    (None, "1C"),
    ("k_sl_1c_a_r1", "1C"),
    ("k_sl_1c_b_r1", "1C"),
    ("k_sl_1c_c_copy_numbers", "2A"),
    ("k_sl_2a_b_r1", "2A"),
    (None, "2A"),
    (None, "2A"),
    (None, "2A"),
    (None, "2A"),
    (None, "2A"),
    ("k_sl_2a_c_r5", "2B"),
    ("k_sl_2b_a_r1", "2B"),
    (None, "2B"),
    (None, "2B"),
    (None, "2B"),
    (None, "2B"),
    (None, "2B"),
    ("k_sl_2b_b_r5", "2B"),
    ("k_sl_2b_c_r3", "2C"),
    ("k_sl_2c_c_r1", "2C"),
    (None, "2C"),
    (None, "2C"),
    (None, "2C"),
    ("k_sl_2c_d_r3", "3A"),
    (None, "3A"),
    (None, "3A"),
    (None, "3A"),
    (None, "3A"),
    ("k_sl_3a_a_r1", "3A"),
    ("k_sl_3a_b_r2", "3A"),
    ("k_sl_3a_d_r1", "3A"),
    ("k_sl_3a_c_r1", "3A"),
    (None, "3B"),
    (None, "3B"),
    (None, "3B"),
    (None, "3B"),
    (None, "3B"),
    (None, "3B"),
    ("k_sl_3b_a_r1", "3B"),
    ("k_sl_3b_e_r1", "3B"),
    ("k_sl_3b_b_r1", "3B"),
    ("k_sl_3b_d_r1", "3B"),
    ("k_sl_3b_c_r1", "3C"),
    (None, "3C"),
    (None, "3C"),
    (None, "3C"),
    (None, "3C"),
    ("k_sl_3c_a_r1", "3C"),
    ("k_sl_3c_b_r1", "3C"),
    ("k_sl_3c_c_r1", "3C"),
    ("k_sl_3c_c_r2", "3C"),
    ("k_sl_3c_d_r1", "3C"),
    ("k_sl_3c_d_r2", "3C"),
    ("k_sl_3c_e_r1", "3C"),
]

# The package-clock path advances the same scripted turns by one minute each.
CLOCKED_JOURNEY = [
    (selection, turn_number * 60, expected_scene)
    for turn_number, (selection, expected_scene) in enumerate(UNCLOCKED_JOURNEY, start=1)
]


class _ScriptedProvider:
    """Return one pre-planned selection per turn without parsing prose."""

    def __init__(self, package=PACKAGE) -> None:
        self.package = package
        self.selected: list[str] = []

    def __call__(self, _player_input: str) -> dict[str, object]:
        # A selection must be grounded in the segment that tells it, exactly as the
        # runtime requires of a live provider; an ungrounded selection is rejected.
        text = "A concrete authored consequence lands."
        if self.selected:
            knowledge = self.package.knowledge_indexes.by_id[self.selected[0]]
            text = knowledge.delivery_text or knowledge.statement
            if self.selected[0] == "k_sl_1a_b_r0":
                text = "A memory card is taped beneath the KMS drawer. Michelle left it there."
        return {
            "segments": [
                {
                    "kind": "narration",
                    "text": text,
                    "grounding_ids": list(self.selected),
                }
            ],
            "selected_knowledge_ids": list(self.selected),
        }


def _drive(engine: RuntimeEngine, provider: _ScriptedProvider, selection: str | None, **kwargs) -> None:
    provider.selected = [selection] if selection else []
    command = {
        "k_sl_1b_d_r1": "Look under the park bench.",
        "k_sl_1b_b_r2": "Ask the man about Michelle.",
        "k_sl_1b_c_r1": "Open the service gate.",
    }.get(selection, "Act on the strongest available lead.")
    engine.turn(command, **kwargs)


def test_clocked_canon_journey_reaches_the_resolution_scene() -> None:
    package = legacy_package(PACKAGE, {"k_sl_1a_a_r1"})
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)

    elapsed = 0
    for turn_index, (selection, target, expected_scene) in enumerate(CLOCKED_JOURNEY, start=1):
        _drive(engine, provider, selection, clock_seconds=target - elapsed)
        elapsed = target
        assert state.current_scene_id == expected_scene, (
            f"turn {turn_index} selecting {selection} at {target}s ended in "
            f"{state.current_scene_id}, expected {expected_scene}"
        )
        assert not state.has_pending_break

    assert {
        "patrol_arrives_1a",
        "patrol_enters_1a",
        "patrol_leaves_1a",
        "patrol_returns_1a",
    } <= state.fired_event_ids
    assert {"purge_window_2c", "SL-2C-D"} & state.fired_event_ids
    assert "override_deadline_3a" in state.fired_event_ids
    assert "destruction_3b" in state.fired_event_ids
    assert state.story_complete is True
    assert Fact(predicate="evacuation_complete", subject="story", value="true") in state.facts.asserted


def test_unclocked_canon_journey_fits_the_authored_budget() -> None:
    package = legacy_package(PACKAGE, {"k_sl_1a_a_r1"})
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)

    for turn_index, (selection, expected_scene) in enumerate(UNCLOCKED_JOURNEY, start=1):
        _drive(engine, provider, selection)
        assert state.current_scene_id == expected_scene, (
            f"turn {turn_index} selecting {selection} ended in {state.current_scene_id}, expected {expected_scene}"
        )

    assert 60 * len(UNCLOCKED_JOURNEY) <= package.pacing.budget_seconds
    assert state.story_complete is True
    assert Fact(predicate="evacuation_complete", subject="story", value="true") in state.facts.asserted


def test_committed_triggers_never_outrun_the_authored_pacing_floor() -> None:
    """A committed transition trigger must wait for the source scene's minimum turns."""

    package = legacy_package(PACKAGE, {"k_sl_1a_a_r1"})
    state = RuntimeState.bootstrap(package)
    provider = _ScriptedProvider(package)
    engine = RuntimeEngine(state, provider)

    _drive(engine, provider, "k_sl_1a_a_r1", clock_seconds=120)
    _drive(engine, provider, "k_sl_1a_b_r0", clock_seconds=0)
    _drive(engine, provider, "k_sl_1a_b_r1", clock_seconds=75)
    window = next(item for item in package.pacing.scenes if item.scene_id == "1A")
    for _ in range(window.min_turns - 4):
        _drive(engine, provider, None, clock_seconds=0)
    assert state.current_scene_id == "1A"
    _drive(engine, provider, None, clock_seconds=0)
    assert state.current_scene_id == "1B"

    # Commit the next trigger before the first turn in 1B; its authored floor
    # keeps the committed trigger in the source scene until the floor is met.
    state.facts.assert_fact(Fact(predicate="transport_route_departure_ready", subject="story", value="true"))
    _drive(engine, provider, None, clock_seconds=40)
    assert state.current_scene_id == "1B", "the source scene must receive its minimum turns"

    window = next(item for item in package.pacing.scenes if item.scene_id == "1B")
    for _ in range(window.min_turns - 2):
        _drive(engine, provider, None, clock_seconds=0)
    _drive(engine, provider, None, clock_seconds=15)
    assert state.current_scene_id == "1C"


def test_scene_1a_handoff_recovers_card_atomically_with_continuity_files() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    state.facts.assert_fact(Fact(predicate="patrol_return_pressure", subject="story", value="true"))
    provider = _ScriptedProvider()
    engine = RuntimeEngine(state, provider)

    window = next(item for item in PACKAGE.pacing.scenes if item.scene_id == "1A")
    for _ in range(window.handoff_after_turns):
        _drive(engine, provider, None)

    assert state.current_scene_id == "1B"
    assert Fact(predicate="continuity_initiative_known", subject="story", value="true") in state.facts.asserted
    assert Fact(predicate="memory_card_recovered", subject="story", value="true") in state.facts.asserted

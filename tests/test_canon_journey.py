"""Deterministic full-game canon journey: every authored transition is reachable.

These tests drive the runtime with a scripted provider so CI proves the story
package and engine support a complete 1A -> 3C playthrough without any model
call. The clocked variant mirrors the hosted Playwright package-clock recipe;
the unclocked variant mirrors default 60-second turns and lands exactly on the
authored 1200-second (20-minute) budget.
"""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.engine import RuntimeEngine
from storygame.runtime.state import RuntimeState
from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

# (selected knowledge id or None, armed elapsed target, expected scene at turn end)
CLOCKED_JOURNEY = [
    ("k_sl_1a_a_r1", 120, "1A"),
    ("k_sl_1a_b_r1", 195, "1B"),
    ("k_sl_1b_b_r1", 270, "1B"),
    ("k_sl_1b_c_r1", 330, "1C"),
    ("k_sl_1c_a_r2", 390, "1C"),
    ("k_sl_1c_b_r1", 450, "2A"),
    ("k_sl_2a_b_r1", 510, "2A"),
    ("k_sl_2a_c_r2", 570, "2B"),
    ("k_sl_2b_a_r2", 630, "2B"),
    ("k_sl_2b_b_r1", 630, "2B"),
    ("k_sl_2b_c_r1", 705, "2C"),
    ("k_sl_2c_a_r2", 780, "2C"),
    ("k_sl_2c_c_r1", 840, "3A"),
    ("k_sl_3a_a_r1", 870, "3A"),
    ("k_sl_3a_b_r2", 900, "3A"),
    ("k_sl_3a_c_r1", 975, "3B"),
    ("k_sl_3b_a_r1", 1020, "3B"),
    ("k_sl_3b_b_r1", 1050, "3B"),
    ("k_sl_3b_c_r1", 1140, "3C"),
    ("k_sl_3c_a_r1", 1200, "3C"),
]

# Alternate-realization coverage at the default 60-second turn cadence.
UNCLOCKED_JOURNEY = [
    ("k_sl_1a_a_r1", "1A"),
    (None, "1A"),
    ("k_sl_1a_b_r1", "1B"),
    ("k_sl_1b_b_r1", "1B"),
    ("k_sl_1b_c_r1", "1C"),
    ("k_sl_1c_a_r2", "1C"),
    ("k_sl_1c_b_r2", "2A"),
    ("k_sl_2a_b_r1", "2A"),
    ("k_sl_2a_c_r2", "2B"),
    ("k_sl_2b_a_r1", "2B"),
    ("k_sl_2b_b_r2", "2B"),
    ("k_sl_2b_c_r2", "2C"),
    ("k_sl_2c_a_r2", "2C"),
    ("k_sl_2c_c_r2", "3A"),
    ("k_sl_3a_a_r2", "3A"),
    ("k_sl_3a_b_r1", "3A"),
    ("k_sl_3a_c_r2", "3B"),
    ("k_sl_3b_a_r2", "3B"),
    ("k_sl_3b_b_r2", "3B"),
    ("k_sl_3b_c_r2", "3C"),
    ("k_sl_3c_a_r2", "3C"),
]


class _ScriptedProvider:
    """Return one pre-planned selection per turn without parsing prose."""

    def __init__(self) -> None:
        self.selected: list[str] = []

    def __call__(self, _player_input: str) -> dict[str, object]:
        return {
            "segments": [{"kind": "narration", "text": "A concrete authored consequence lands."}],
            "selected_knowledge_ids": list(self.selected),
        }


def _drive(engine: RuntimeEngine, provider: _ScriptedProvider, selection: str | None, **kwargs) -> None:
    provider.selected = [selection] if selection else []
    engine.turn("I act on the strongest available lead.", **kwargs)


def test_clocked_canon_journey_reaches_the_resolution_scene() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _ScriptedProvider()
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

    assert "pressure_1a" in state.fired_event_ids
    assert "purge_2c" in state.fired_event_ids
    assert "override_deadline_3a" in state.fired_event_ids
    assert "destruction_3b" in state.fired_event_ids
    assert state.facts.has("resolution_complete", "story", value="true")


def test_unclocked_canon_journey_fits_the_twenty_minute_budget() -> None:
    state = RuntimeState.bootstrap(PACKAGE)
    provider = _ScriptedProvider()
    engine = RuntimeEngine(state, provider)

    for turn_index, (selection, expected_scene) in enumerate(UNCLOCKED_JOURNEY, start=1):
        _drive(engine, provider, selection)
        assert state.current_scene_id == expected_scene, (
            f"turn {turn_index} selecting {selection} ended in {state.current_scene_id}, expected {expected_scene}"
        )

    assert state.facts.has("story_elapsed_seconds", "story", value=str(60 * len(UNCLOCKED_JOURNEY)))
    assert state.facts.has("resolution_complete", "story", value="true")


def test_committed_triggers_never_outrun_the_authored_pacing_floor() -> None:
    """A committed transition trigger must wait for the target scene's earliest window."""

    state = RuntimeState.bootstrap(PACKAGE)
    provider = _ScriptedProvider()
    engine = RuntimeEngine(state, provider)

    _drive(engine, provider, "k_sl_1a_a_r1", clock_seconds=120)
    _drive(engine, provider, "k_sl_1a_b_r1", clock_seconds=75)
    assert state.current_scene_id == "1B"

    # Commit every bridge_1b fact well before scene 1C's earliest window (270s).
    _drive(engine, provider, "k_sl_1b_b_r1", clock_seconds=40)
    _drive(engine, provider, "k_sl_1b_c_r1", clock_seconds=20)
    assert state.facts.has("park_pursuit_resolved", "story", value="true")
    assert state.current_scene_id == "1B", "the transition must wait for 1C's authored earliest window"

    _drive(engine, provider, None, clock_seconds=15)
    # At 270 seconds the authored window opens and the committed triggers carry Kristin out.
    assert state.current_scene_id == "1C"


def _reachable_facts(package, seed_facts: set[str], fired_storylets: set[str]) -> set[str]:
    """Every fact still committable from this state, ignoring turn order."""

    pacing_facts = {effect.fact_id for event in package.pacing.events for effect in event.effects}
    facts = set(seed_facts) | pacing_facts
    changed = True
    while changed:
        changed = False
        for route in package.storylet_routes.storylets:
            if route.id in fired_storylets:
                continue
            eligible = all(
                (predicate.fact_id in facts) if predicate.equals is not False else (predicate.fact_id not in seed_facts)
                for predicate in route.activation_conditions
            )
            if not eligible:
                continue
            for realization in route.realizations:
                for operation in realization.operations:
                    if operation.op == "assert" and operation.fact_id not in facts:
                        facts.add(operation.fact_id)
                        changed = True
        for event in package.storylet_routes.bridge_events:
            if all(predicate.fact_id in facts for predicate in event.activation_conditions):
                for operation in event.operations:
                    if operation.op == "assert" and operation.fact_id not in facts:
                        facts.add(operation.fact_id)
                        changed = True
    return facts


def test_no_single_reveal_can_strand_a_scene_exit() -> None:
    """No realization may consume the only route to its own scene's exit.

    A storylet fires once. When two authored beats share a storylet and only one
    of them establishes the outgoing trigger, choosing the other permanently
    strands the player: recovering Michelle's damaged recording used to consume
    Scene 1A's only source of `michelle_lead_actionable`, leaving the game
    unwinnable in the opening scene.
    """

    stranded = []
    for transition in PACKAGE.pacing.transitions:
        required = {trigger.fact_id for trigger in transition.triggers}
        for route in PACKAGE.storylet_routes.storylets:
            if route.scene_id != transition.source_scene_id:
                continue
            for realization in route.realizations:
                committed = {op.fact_id for op in realization.operations if op.op == "assert"}
                missing = required - _reachable_facts(PACKAGE, committed, {route.id})
                if missing:
                    stranded.append(f"{route.id}/{realization.id} strands {sorted(missing)} needed by {transition.id}")

    assert not stranded, "a single reveal made a scene exit unreachable:\n" + "\n".join(stranded)

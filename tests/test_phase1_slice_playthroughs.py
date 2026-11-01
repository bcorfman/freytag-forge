"""Hermetic Act 2 incident slices for outcomes and missed-window recovery."""

from pathlib import Path

import pytest

from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_slice_a_inspection_convincing_outcome_uses_the_new_route() -> None:
    incident = next(item for item in PACKAGE.incidents if item.id == "i_2a_real_leak")
    convincing = next(item for item in incident.outcomes if item.id == "inspection_convincing")

    assert convincing.storylet_id == "SL-2A-C"
    assert convincing.realization_id == "SL-2A-C-R5"
    assert convincing.advantages == ("supervisor_convinced",)
    assert convincing.costs == ()


def test_slice_b_inspection_doubted_outcome_marks_the_cover_suspected_path() -> None:
    incident = next(item for item in PACKAGE.incidents if item.id == "i_2a_real_leak")
    doubted = next(item for item in incident.outcomes if item.id == "inspection_doubted")

    assert doubted.storylet_id == "SL-2A-C"
    assert doubted.realization_id == "SL-2A-C-R6"
    assert doubted.advantages == ("restricted_corridor_access",)
    assert doubted.costs == ("cover_suspected",)


def test_slice_c_missed_window_recovery_requires_the_inspection_window_fact() -> None:
    recovery = next(route for route in PACKAGE.storylet_routes.storylets if route.id == "SL-2A-D")
    assert tuple(condition.fact_id for condition in recovery.activation_conditions) == ("inspection_window_missed",)
    event = next(event for event in PACKAGE.pacing.events if event.id == "inspection_window_2a")
    assert event.scene_id == "2A"
    assert event.at_turn == 5
    assert tuple(effect.fact_id for effect in event.effects) == ("inspection_window_missed",)


@pytest.mark.parametrize(
    ("scene_id", "incident_id", "window_id", "nudge_id", "missed_fact", "pressure_fact"),
    (
        (
            "2A",
            "i_2a_real_leak",
            "inspection_window_2a",
            "inspection_nudge_2a",
            "inspection_window_missed",
            "supervisor_escorting",
        ),
        ("2B", "i_2b_audit", "audit_window_2b", "audit_nudge_2b", "audit_window_missed", "audit_reaches_stacks"),
        (
            "2C",
            "i_2c_rebecca_corridor",
            "purge_window_2c",
            "purge_nudge_2c",
            "purge_window_missed",
            "purge_alarm_active",
        ),
    ),
)
def test_act2_windows_and_recovery_routes_are_one_per_scene(
    scene_id: str,
    incident_id: str,
    window_id: str,
    nudge_id: str,
    missed_fact: str,
    pressure_fact: str,
) -> None:
    incident = next(item for item in PACKAGE.incidents if item.id == incident_id)
    assert incident.scene_id == scene_id
    assert incident.missed_window_event_id == window_id
    recovery_id = {"2A": "SL-2A-D", "2B": "SL-2B-D", "2C": "SL-2C-E"}[scene_id]
    assert incident.recovery_storylet_id == recovery_id

    window = next(event for event in PACKAGE.pacing.events if event.id == window_id)
    nudge = next(event for event in PACKAGE.pacing.events if event.id == nudge_id)
    assert window.scene_id == nudge.scene_id == scene_id
    assert window.at_turn == 5
    assert nudge.at_turn == 6
    assert tuple(effect.fact_id for effect in window.effects) == (missed_fact,)
    assert tuple(effect.fact_id for effect in nudge.effects) == (pressure_fact,)

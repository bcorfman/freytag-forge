from __future__ import annotations

from pathlib import Path

import pytest

from storygame.personas import _ScriptedProvider
from storygame.runtime.engine import RuntimeEngine
from storygame.story_package.loader import load_story_package
from tests.test_continuity_1c_incident import _facts, _state

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))


def test_1c_offer_contract_is_gated_and_the_miss_is_visible() -> None:
    event = next(item for item in PACKAGE.pacing.events if item.id == "transfer_window_1c")
    assert len(event.effects) == 1
    assert event.effects[0].fact_id == "transfer_window_missed"
    assert event.realizations[0].verbatim is True
    assert event.realizations[0].text == (
        'The view down the observation shaft goes dark. Brandon says, "That chance is gone. '
        "We can still try the service entrance. Follow me through it if you want to try. "
        'We will have to risk the sweep."'
    )

    routes = {item.id: item for item in PACKAGE.storylet_routes.storylets}
    for route_id in ("SL-1C-A", "SL-1C-B"):
        assert any(
            condition.fact_id == "transfer_window_missed" and condition.equals is False
            for condition in routes[route_id].activation_conditions
        )

    state = _state()
    provider = _ScriptedProvider(PACKAGE, state)
    engine = RuntimeEngine(state, provider)
    missed_result = None
    for _ in range(5):
        missed_result = engine.turn("Inspect the loading docks for signs of activity.")

    assert missed_result is not None
    assert event.realizations[0].text in {segment.text for segment in missed_result.segments}
    assert "transfer_window_missed" in _facts(state)
    assert not {
        "processing_numbers_copied",
        "service_level_access_known",
        "facility_infiltration_needed",
    } & _facts(state)

    provider.selected = ("k_sl_1c_b_r1",)
    with pytest.raises(Exception, match="not eligible"):
        engine.turn("Study the people through the observation shaft.")

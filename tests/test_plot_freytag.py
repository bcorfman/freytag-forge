from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.plot.freytag import get_phase
from storygame.plot.tension import TARGET_TENSION, apply_tension_events


def test_phase_boundaries():
    assert get_phase(0.0) == "exposition"
    assert get_phase(0.19) == "exposition"
    assert get_phase(0.2) == "rising_action"
    assert get_phase(0.59) == "rising_action"
    assert get_phase(0.6) == "climax"
    assert get_phase(0.79) == "climax"
    assert get_phase(0.8) == "falling_action"
    assert get_phase(0.94) == "falling_action"
    assert get_phase(0.95) == "resolution"


def test_tension_smoothing_to_target():
    state = build_default_state(seed=9)
    state.progress = 0.7
    state.tension = 0.1
    after = apply_tension_events(
        state,
        [Event(type="x", delta_tension=0.3)],
    )
    assert after.tension >= 0.1
    assert after.tension <= TARGET_TENSION["climax"]

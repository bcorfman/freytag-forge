from __future__ import annotations

import textwrap

import pytest

from storygame.engine.state import Event
from storygame.engine.world import build_default_state
from storygame.plot.curves import (
    _normalize_genre,
    _stable_index,
    load_plot_curves,
    normalize_session_length,
    select_curve_id,
    select_curve_template,
)
from storygame.plot.tension import apply_tension_events


def test_curves_validation_error_paths(tmp_path) -> None:
    with pytest.raises(ValueError, match="non-empty"):
        _normalize_genre("   ")
    with pytest.raises(ValueError, match="one of"):
        normalize_session_length("invalid")
    with pytest.raises(ValueError, match=">= 1"):
        normalize_session_length(0)

    bad_root = tmp_path / "bad_root.yaml"
    bad_root.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must parse to a mapping"):
        load_plot_curves(bad_root)

    missing_library = tmp_path / "missing_library.yaml"
    missing_library.write_text("schema_version: 1", encoding="utf-8")
    with pytest.raises(ValueError, match="curve_library"):
        load_plot_curves(missing_library)


def test_curve_selection_error_paths_for_invalid_templates(tmp_path) -> None:
    invalid_payload = tmp_path / "invalid_templates.yaml"
    invalid_payload.write_text(
        textwrap.dedent(
            """
            curve_library:
              mystery:
                - not_a_mapping
            """
        ).strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Invalid curve template entry"):
        select_curve_template("mystery", "short", seed=1, path=invalid_payload)

    missing_curve_id = tmp_path / "missing_curve_id.yaml"
    missing_curve_id.write_text(
        textwrap.dedent(
            """
            curve_library:
              mystery:
                - phase_targets: [0.1, 0.3]
            """
        ).strip(),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="curve_id"):
        select_curve_id("mystery", "short", seed=1, path=missing_curve_id)

    unknown_genre = tmp_path / "unknown_genre.yaml"
    unknown_genre.write_text("curve_library: { mystery: [ {curve_id: x} ] }", encoding="utf-8")
    with pytest.raises(ValueError, match="Unknown genre"):
        select_curve_template("romance", "short", seed=1, path=unknown_genre)


def test_stable_index_and_tension_clamp_bounds() -> None:
    assert _stable_index("mystery", "short", 5, 3) in {0, 1, 2}

    state = build_default_state(seed=631)
    state.tension = 0.95
    apply_tension_events(state, [Event(type="x", delta_tension=10.0)])
    assert state.tension == 1.0

    state.tension = 0.01
    apply_tension_events(state, [Event(type="x", delta_tension=-10.0)])
    assert state.tension == 0.0

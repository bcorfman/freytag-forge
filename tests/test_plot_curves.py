from __future__ import annotations

import pytest

from storygame.plot.curves import (
    load_plot_curves,
    normalize_session_length,
    select_curve_id,
    select_curve_template,
)


def test_load_plot_curves_contains_expected_genres() -> None:
    payload = load_plot_curves()

    assert payload["version"] == 1
    assert "curve_library" in payload
    assert "sci-fi" in payload["curve_library"]
    assert "mystery" in payload["curve_library"]
    assert "thriller" in payload["curve_library"]


def test_normalize_session_length_for_string_and_int() -> None:
    assert normalize_session_length("short") == "short"
    assert normalize_session_length("medium") == "medium"
    assert normalize_session_length("long") == "long"

    assert normalize_session_length(8) == "short"
    assert normalize_session_length(20) == "medium"
    assert normalize_session_length(40) == "long"


def test_normalize_session_length_rejects_invalid_values() -> None:
    with pytest.raises(ValueError, match="session_length"):
        normalize_session_length("xl")

    with pytest.raises(ValueError, match="session_length"):
        normalize_session_length(0)


def test_select_curve_id_is_deterministic() -> None:
    first = select_curve_id(genre="mystery", session_length="medium", seed=42)
    second = select_curve_id(genre="mystery", session_length="medium", seed=42)

    assert first == second
    assert first in {
        "mystery_fair_play_whodunit",
        "mystery_conspiracy_spiral",
    }


def test_select_curve_id_rejects_unknown_genre() -> None:
    with pytest.raises(ValueError, match="Unknown genre"):
        select_curve_id(genre="western", session_length="short", seed=7)


def test_select_curve_template_returns_matching_curve_id() -> None:
    curve = select_curve_template(genre="sci-fi", session_length=18, seed=11)

    assert curve["curve_id"] in {
        "sci_fi_discovery_escalation",
        "sci_fi_dystopian_pressure",
    }
    assert isinstance(curve["points"], list)
    assert len(curve["points"]) == 12

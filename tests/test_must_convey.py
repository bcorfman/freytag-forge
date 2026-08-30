"""Unit coverage for deterministic authored reveal requirements."""

from __future__ import annotations

from storygame.runtime.validation import unconveyed_terms


def test_unconveyed_terms_normalizes_case_curly_punctuation_dashes_and_spacing() -> None:
    groups = (("Memory—card", "unused card"), ("Michelle's note", "other note"))

    assert unconveyed_terms(groups, "  the MEMORY-card\nwas from Michelle’s   note. ") == ()


def test_unconveyed_terms_returns_the_first_phrase_for_each_missed_group() -> None:
    groups = (("first missing", "alternate"), ("second missing",), ("found", "other"))

    assert unconveyed_terms(groups, "The found details are here.") == (
        "first missing",
        "second missing",
    )


def test_unconveyed_terms_empty_groups_are_empty() -> None:
    assert unconveyed_terms((), "anything") == ()

"""Unit coverage for deterministic authored reveal requirements."""

from __future__ import annotations

from pathlib import Path

from storygame.runtime.contracts import NarrationSegment
from storygame.runtime.validation import derive_grounding, derive_statement_grounding, unconveyed_terms
from storygame.story_package import load_story_package

PACKAGE = Path("data/stories/continuity-initiative")

REVEAL_GROUPS = (
    ("memory card", "card"),
    ("damaged recording", "recording"),
    ("Michelle's",),
    ("dead drop",),
    ("park bench", "bench in the park"),
)


def test_derive_grounding_returns_the_smallest_segment_set_that_tells_the_reveal() -> None:
    segments = (
        NarrationSegment(kind="narration", text="A drawer sticks."),
        NarrationSegment(
            kind="narration",
            text="Kristin finds Michelle's memory card and damaged recording at a dead drop by the park bench.",
        ),
        NarrationSegment(kind="narration", text="The room goes quiet."),
    )

    assert derive_grounding(REVEAL_GROUPS, segments) == (segments[1],)


def test_derive_grounding_returns_nothing_when_prose_tells_none_of_the_reveal() -> None:
    segments = (NarrationSegment(kind="narration", text="The drawer sticks."),)

    assert derive_grounding(REVEAL_GROUPS, segments) == ()


def test_derive_grounding_returns_nothing_when_prose_tells_only_part_of_the_reveal() -> None:
    segments = (NarrationSegment(kind="narration", text="Kristin finds Michelle's memory card."),)

    assert derive_grounding(REVEAL_GROUPS, segments) == ()


def test_derive_grounding_can_span_segments_in_narration_order() -> None:
    segments = (
        NarrationSegment(kind="narration", text="Kristin finds Michelle's memory card and damaged recording."),
        NarrationSegment(kind="narration", text="It points to a dead drop at the park bench."),
    )

    assert derive_grounding(REVEAL_GROUPS, segments) == segments


def test_derive_grounding_never_derives_an_empty_requirement() -> None:
    segments = (NarrationSegment(kind="narration", text="Anything at all."),)

    assert derive_grounding((), segments) == ()


def test_derive_statement_grounding_picks_the_segment_that_delivers_the_statement() -> None:
    segments = (
        NarrationSegment(kind="narration", text="The corridor waits in silence."),
        NarrationSegment(kind="narration", text="Michelle broadcasts the captives and records to the networks."),
    )

    assert derive_statement_grounding("Michelle broadcasts captives and records to networks.", segments) == (
        segments[1],
    )


def test_derive_statement_grounding_rejects_unrelated_narration() -> None:
    segments = (NarrationSegment(kind="narration", text="She waits in the corridor and listens to the vents."),)

    assert derive_statement_grounding("Michelle broadcasts captives to networks.", segments) == ()


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


def test_unconveyed_terms_matches_a_whole_word() -> None:
    assert unconveyed_terms((("card",),), "The card is on the table.") == ()


def test_unconveyed_terms_matches_an_ordinary_english_ending() -> None:
    assert unconveyed_terms((("relay",), ("open",)), "The relays opened.") == ()


def test_unconveyed_terms_matches_each_supported_ordinary_ending() -> None:
    groups = (("relay",), ("watch",), ("wash",), ("use",), ("open",))

    assert unconveyed_terms(groups, "Relays watches washed used opening.") == ()


def test_unconveyed_terms_rejects_a_phrase_inside_a_longer_word() -> None:
    assert unconveyed_terms((("card",),), "The discarded item is here.") == ("card",)


def test_unconveyed_terms_requires_multi_word_phrasings_to_be_contiguous() -> None:
    groups = (("memory card",),)

    assert unconveyed_terms(groups, "The memory was hidden beside the card.") == ("memory card",)
    assert unconveyed_terms(groups, "The hidden memory cards were recovered.") == ()


def test_no_delivery_is_conveyed_by_another_delivery_fallback() -> None:
    package = load_story_package(PACKAGE)

    for delivery in package.deliveries:
        for other_delivery in package.deliveries:
            if delivery.fact_id == other_delivery.fact_id:
                continue
            assert unconveyed_terms(delivery.must_convey, other_delivery.fallback_text), (
                delivery.fact_id,
                other_delivery.fact_id,
            )


def test_generic_prose_conveys_no_delivery() -> None:
    package = load_story_package(PACKAGE)

    for delivery in package.deliveries:
        assert unconveyed_terms(delivery.must_convey, "The situation changed."), delivery.fact_id


def test_gated_reveal_statements_convey_their_own_groups() -> None:
    package = load_story_package(PACKAGE)

    for knowledge in package.knowledge.knowledge:
        if knowledge.must_convey:
            assert not unconveyed_terms(knowledge.must_convey, knowledge.statement), knowledge.id

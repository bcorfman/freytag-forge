from pathlib import Path

import pytest

from storygame.story_package.loader import load_story_package

PACKAGE = load_story_package(Path("data/stories/continuity-initiative"))

pytestmark = pytest.mark.authoring_quality

EXPECTED_CUES = {
    "national_network_fragmenting": "Reports from other detention sites reach the broadcast chamber.",
    "community_rescue_efforts_begun": "Families of the missing call the broadcast chamber for word.",
}


def _delivery(fact_id: str):
    return next(item for item in PACKAGE.deliveries if item.fact_id == fact_id)


def _matches_must_convey(delivery, text: str) -> bool:
    lowered = text.casefold()
    return all(any(phrase.casefold() in lowered for phrase in group) for group in delivery.must_convey)


def test_3c_option_3_cues_are_loaded() -> None:
    assert {delivery.cue_text for delivery in PACKAGE.deliveries} >= set(EXPECTED_CUES.values())


def test_3c_option_3_cues_and_fallbacks_match_must_convey() -> None:
    for fact_id, expected_cue in EXPECTED_CUES.items():
        delivery = _delivery(fact_id)
        assert delivery.cue_text == expected_cue
        assert _matches_must_convey(delivery, delivery.cue_text)
        assert _matches_must_convey(delivery, delivery.fallback_text)
